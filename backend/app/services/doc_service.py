"""
RAG 知识库系统 —— 文档服务
============================
文件哈希/类型检测、分片合并、文档解析（含 OCR 回退与质量校验）、
向量入库、精确删除（删文档同步清向量）。
"""
import hashlib
from pathlib import Path
from typing import List, Optional, Tuple, Any

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)
from langchain_core.documents import Document
from sqlalchemy.orm import Session

from app.config import DATA_DIR, ALLOWED_EXTENSIONS, TMP_DIR
from app.models import KnowledgeBase, Document as DocModel
from app.core import ocr as ocr_module
from app.core import chunking
from app.core.embeddings import load_embedding_model
from app.core import vector_store as vs

# 完整上传文件的落盘目录
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 文件哈希与类型检测
# ============================================================================
def get_file_hash(file_bytes: bytes) -> str:
    """计算文件 SHA256 哈希前 16 位，用于去重与向量 id"""
    return hashlib.sha256(file_bytes).hexdigest()[:16]


def detect_file_type(filename: str) -> str:
    """根据文件名后缀检测文件类型"""
    ext = Path(filename).suffix.lower()
    return {"pdf": "pdf", "txt": "txt", "md": "md", "docx": "docx"}.get(ext, "unknown")


def is_allowed(filename: str) -> bool:
    """文件上传白名单校验"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


# ============================================================================
# 分片上传
# ============================================================================
def save_chunk(file_hash: str, chunk_index: int, chunk_bytes: bytes) -> None:
    """保存单个分片到临时目录"""
    chunk_dir = TMP_DIR / file_hash
    chunk_dir.mkdir(parents=True, exist_ok=True)
    (chunk_dir / f"chunk_{chunk_index}").write_bytes(chunk_bytes)


def uploaded_chunks(file_hash: str) -> List[int]:
    """返回已上传的分片序号列表（用于断点续传）"""
    chunk_dir = TMP_DIR / file_hash
    if not chunk_dir.exists():
        return []
    return sorted(
        int(f.name.split("_")[1]) for f in chunk_dir.glob("chunk_*")
    )


def merge_chunks(file_hash: str, filename: str, total_chunks: int) -> Path:
    """按序合并分片为完整文件，返回落盘路径"""
    chunk_dir = TMP_DIR / file_hash
    final_path = UPLOAD_DIR / f"{file_hash}_{filename}"
    with final_path.open("wb") as out:
        for i in range(total_chunks):
            part = chunk_dir / f"chunk_{i}"
            if not part.exists():
                raise ValueError(f"缺少分片 {i}，请重新上传")
            out.write(part.read_bytes())
    # 清理临时分片
    import shutil

    shutil.rmtree(chunk_dir, ignore_errors=True)
    return final_path


# ============================================================================
# 文档解析
# ============================================================================
def load_single_document(
    file_path: str,
    file_type: str,
) -> Tuple[List[Document], Optional[dict]]:
    """
    加载单个文档并返回 LangChain Document 列表 + 质量报告。

    扫描版 PDF 常规提取为空时自动回退 OCR 识别。
    """
    loaders = {
        "pdf": PyPDFLoader,
        "txt": TextLoader,
        "md": TextLoader,
        "docx": Docx2txtLoader,
    }
    loader_class = loaders.get(file_type)
    if loader_class is None:
        raise ValueError(f"不支持的文件类型: {file_type}")

    if file_type in ("txt", "md"):
        loader = loader_class(file_path, encoding="utf-8", autodetect_encoding=True)
    else:
        loader = loader_class(file_path)
    documents = loader.load()

    source_name = Path(file_path).name
    valid_docs = []
    for doc in documents:
        text = doc.page_content.strip()
        if text:
            doc.metadata["source"] = source_name
            doc.metadata["file_type"] = file_type
            valid_docs.append(doc)

    if not valid_docs:
        # PDF：常规提取失败时尝试 OCR 回退
        if file_type == "pdf":
            try:
                return ocr_module.ocr_pdf_document(file_path, source_name)
            except ImportError as e:
                raise ValueError(
                    f"文档 '{source_name}' 为扫描版 PDF（无可选文本），"
                    f"且 OCR 依赖未安装。请运行: pip install rapidocr-onnxruntime pymupdf"
                ) from e
        raise ValueError(
            f"文档 '{source_name}' 无法提取文本内容。\n"
            f"可能原因：1) PDF 为扫描版/图片型；2) DOCX 内容为嵌入图片；"
            f"3) 文件损坏或加密"
        )

    return valid_docs, None


# ============================================================================
# 入库与删除
# ============================================================================
def process_and_index(
    db: Session,
    kb: KnowledgeBase,
    file_path: Path,
    file_name: str,
    file_type: str,
) -> Tuple[DocModel, Optional[dict]]:
    """
    解析文档 → 分块 → 向量入库（新建或追加），返回文档记录与质量报告。

    该函数在请求线程内同步执行（文档处理为耗时操作，前端展示进度）。
    """
    # 计算文件哈希（用于去重与向量 id）
    file_hash = get_file_hash(file_path.read_bytes())

    # 解析文档
    documents, quality = load_single_document(str(file_path), file_type)

    # 按知识库配置分块
    chunks = chunking.split_documents(
        documents, file_hash, kb.chunk_size, kb.chunk_overlap
    )
    if not chunks:
        raise ValueError(f"文档 '{file_name}' 分块后无有效内容")

    # 加载嵌入模型（维度必须与知识库一致）
    embeddings = load_embedding_model(kb.embedding_model)
    ids = [c.metadata["chunk_id"] for c in chunks]

    # 判断新建还是增量追加
    store = vs.load_vector_store(kb.id, embeddings)
    if store is None:
        vs.create_vector_store(chunks, embeddings, ids, kb.id)
    else:
        vs.add_documents(store, chunks, ids, kb.id)

    # 记录文档元信息
    doc = DocModel(
        kb_id=kb.id,
        name=file_name,
        file_hash=file_hash,
        file_type=file_type,
        size_kb=round(file_path.stat().st_size / 1024, 1),
        chunk_count=len(chunks),
        status="low_quality" if (quality and quality.get("is_low_quality")) else "done",
        message=_quality_message(quality),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc, quality


def _quality_message(quality: Optional[dict]) -> str:
    """根据质量报告生成文档状态提示"""
    if not quality:
        return ""
    if quality.get("is_low_quality"):
        return (
            f"OCR 识别质量较低（平均置信度 {quality.get('avg_score')}，"
            f"有效字符 {quality.get('char_count')}），可能影响检索效果"
        )
    return f"OCR 识别成功（平均置信度 {quality.get('avg_score')}）"


def _all_docs(store) -> List[Document]:
    """枚举向量库中全部文档（用于删除回退时的重建）"""
    docs = []
    seen = set()
    for doc_id in store.index_to_docstore_id.values():
        if doc_id in seen:
            continue
        seen.add(doc_id)
        doc = store.docstore.search(doc_id)
        if doc:
            docs.append(doc)
    return docs


def delete_document(db: Session, kb: KnowledgeBase, doc: DocModel) -> None:
    """删除文档并同步清理向量数据；精确删除失败时回退全量重建"""
    embeddings = load_embedding_model(kb.embedding_model)
    store = vs.load_vector_store(kb.id, embeddings)

    if store is not None:
        # 找到该文档的所有向量 id（chunk_id 以 file_hash 为前缀）
        target_ids = [
            doc_id
            for doc_id in store.index_to_docstore_id.values()
            if doc_id.startswith(f"{doc.file_hash}_")
        ]
        try:
            if target_ids:
                vs.delete_documents(store, target_ids, kb.id)
            else:
                # 兼容：无 ids 匹配时走重建
                raise ValueError("未找到匹配向量")
        except Exception as e:  # noqa: BLE001 精确删除失败，回退重建
            print(f"[doc_service] 精确删除失败，回退全量重建: {e}")
            remaining = [
                d
                for d in _all_docs(store)
                if d.metadata.get("file_hash") != doc.file_hash
            ]
            if remaining:
                ids = [d.metadata["chunk_id"] for d in remaining]
                vs.rebuild_vector_store(remaining, embeddings, ids, kb.id)
            else:
                # 无剩余文档，清空向量目录
                for f in vs.kb_storage_dir(kb.id).iterdir():
                    if f.is_file():
                        f.unlink()

    # 删除落盘文件
    for p in UPLOAD_DIR.glob(f"{doc.file_hash}_*"):
        p.unlink(missing_ok=True)

    db.delete(doc)
    db.commit()
