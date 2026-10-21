"""
RAG 知识库系统 —— FAISS 向量库管理
====================================
按知识库隔离存储，显式 ids 支持精确删除（删文档同步清向量），
并提供增量追加、全量重建、磁盘备份与恢复、重启自动加载。
"""
import os
import shutil
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import STORAGE_DIR, BACKUP_DIR


def kb_storage_dir(kb_id: int) -> Path:
    """知识库向量文件目录：data/storage/{kb_id}/"""
    d = STORAGE_DIR / str(kb_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


# FAISS 的 C++ 写文件（faiss.write_index）在 Windows 上无法打开含非 ASCII（中文）的
# 绝对路径，因此保存/加载时加锁 chdir 到目标目录，改用相对路径 "." 规避该问题。
_faiss_io_lock = threading.Lock()


def _save_local(store: FAISS, folder: Path) -> None:
    """线程安全地保存 FAISS 索引（规避中文路径问题）"""
    folder.mkdir(parents=True, exist_ok=True)
    with _faiss_io_lock:
        cwd = os.getcwd()
        os.chdir(folder)
        try:
            store.save_local(".")
        finally:
            os.chdir(cwd)


def _load_local(folder: Path, embeddings: HuggingFaceEmbeddings) -> FAISS:
    """线程安全地加载 FAISS 索引（规避中文路径问题）"""
    with _faiss_io_lock:
        cwd = os.getcwd()
        os.chdir(folder)
        try:
            return FAISS.load_local(
                ".", embeddings, allow_dangerous_deserialization=True
            )
        finally:
            os.chdir(cwd)


def create_vector_store(
    docs: List[Document],
    embeddings: HuggingFaceEmbeddings,
    ids: List[str],
    kb_id: int,
) -> FAISS:
    """全量新建向量索引（显式 ids，支持后续精确删除）"""
    store = FAISS.from_documents(docs, embeddings, ids=ids)
    _save_local(store, kb_storage_dir(kb_id))
    return store


def load_vector_store(
    kb_id: int,
    embeddings: HuggingFaceEmbeddings,
) -> Optional[FAISS]:
    """重启时从磁盘自动加载已有向量库，不存在则返回 None"""
    d = kb_storage_dir(kb_id)
    if not (d / "index.faiss").exists():
        return None
    try:
        return _load_local(d, embeddings)
    except Exception as e:  # noqa: BLE001
        print(f"[vector_store] 加载知识库 {kb_id} 失败: {e}")
        return None


def add_documents(
    store: FAISS,
    docs: List[Document],
    ids: List[str],
    kb_id: int,
) -> FAISS:
    """增量追加文档到现有向量库并持久化"""
    store.add_documents(docs, ids=ids)
    _save_local(store, kb_storage_dir(kb_id))
    return store


def delete_documents(
    store: FAISS,
    ids: List[str],
    kb_id: int,
) -> FAISS:
    """精确删除指定 ids 对应的向量（需索引由 ids 构建），并持久化"""
    store.delete(ids)
    _save_local(store, kb_storage_dir(kb_id))
    return store


def rebuild_vector_store(
    docs: List[Document],
    embeddings: HuggingFaceEmbeddings,
    ids: List[str],
    kb_id: int,
) -> FAISS:
    """全量重建：清空目录后重新构建索引（用于回退或手动重建）"""
    d = kb_storage_dir(kb_id)
    for f in d.iterdir():
        if f.is_file():
            f.unlink()
    return create_vector_store(docs, embeddings, ids, kb_id)


# ============================================================================
# 备份与恢复
# ============================================================================
def backup_kb(kb_id: int) -> Path:
    """将知识库向量文件打包为 zip 备份，返回备份文件路径"""
    src = kb_storage_dir(kb_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"{kb_id}_{timestamp}.zip"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src.iterdir()):
            if f.is_file():
                zf.write(f, arcname=f.name)
    return dest


def restore_kb(kb_id: int, backup_filename: str) -> bool:
    """从备份文件恢复知识库向量库"""
    backup_path = BACKUP_DIR / backup_filename
    if not backup_path.exists():
        return False

    src = kb_storage_dir(kb_id)
    # 清空现有向量文件
    for f in src.iterdir():
        if f.is_file():
            f.unlink()
    with zipfile.ZipFile(backup_path, "r") as zf:
        zf.extractall(src)
    return True


def list_backups(kb_id: int) -> List[dict]:
    """列出某知识库的备份文件"""
    backups = sorted(BACKUP_DIR.glob(f"{kb_id}_*.zip"), reverse=True)
    return [
        {"filename": b.name, "size_kb": round(b.stat().st_size / 1024, 1)}
        for b in backups
    ]
