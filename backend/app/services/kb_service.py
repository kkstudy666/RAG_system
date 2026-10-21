"""
RAG 知识库服务 —— 全量重建、备份恢复等管理操作
================================================
"""
from typing import List

from sqlalchemy.orm import Session

from app.models import KnowledgeBase, Document as DocModel
from app.core import chunking
from app.core.embeddings import load_embedding_model
from app.core import vector_store as vs
from app.services.doc_service import UPLOAD_DIR, load_single_document


def rebuild_kb(db: Session, kb: KnowledgeBase) -> int:
    """
    全量重建知识库向量索引：从已入库文档的落盘文件重新解析、分块、构建索引。
    返回重建后的文本块总数。
    """
    docs = db.query(DocModel).filter(DocModel.kb_id == kb.id).all()

    all_chunks = []
    for doc in docs:
        # 定位落盘文件（文件名形如 {file_hash}_{原名}）
        file_path = next(UPLOAD_DIR.glob(f"{doc.file_hash}_*"), None)
        if file_path is None:
            continue
        try:
            documents, _ = load_single_document(str(file_path), doc.file_type)
            chunks = chunking.split_documents(
                documents, doc.file_hash, kb.chunk_size, kb.chunk_overlap
            )
            all_chunks.extend(chunks)
        except Exception as e:  # noqa: BLE001
            print(f"[kb_service] 重建时跳过文档 {doc.name}: {e}")
            continue

    embeddings = load_embedding_model(kb.embedding_model)

    if all_chunks:
        ids = [c.metadata["chunk_id"] for c in all_chunks]
        vs.rebuild_vector_store(all_chunks, embeddings, ids, kb.id)
    else:
        # 无有效文档，清空向量目录
        for f in vs.kb_storage_dir(kb.id).iterdir():
            if f.is_file():
                f.unlink()

    return len(all_chunks)


def backup_kb(kb_id: int) -> dict:
    """备份知识库向量库，返回备份文件信息"""
    path = vs.backup_kb(kb_id)
    return {"filename": path.name, "size_kb": round(path.stat().st_size / 1024, 1)}


def restore_kb(kb_id: int, filename: str) -> bool:
    """从备份恢复知识库向量库"""
    return vs.restore_kb(kb_id, filename)


def list_backups(kb_id: int) -> List[dict]:
    """列出知识库的备份文件"""
    return vs.list_backups(kb_id)
