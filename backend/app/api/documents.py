"""
RAG 知识库系统 —— 文档接口
============================
分片上传 / 断点续传 / 合并 / 解析入库 / 列表 / 删除（同步清向量）。
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, KnowledgeBase, Document
from app.schemas import DocumentOut, ChunkMergeRequest
from app.core.deps import get_current_user
from app.services import doc_service

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_owned_kb(db: Session, kb_id: int, user: User) -> KnowledgeBase:
    """校验知识库归属并返回（供上传/处理/删除使用）"""
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    if kb.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅创建者可管理该知识库")
    return kb


def _get_readable_kb(db: Session, kb_id: int, user: User) -> KnowledgeBase:
    """校验知识库可读（公开库或 owner）"""
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    if not kb.is_public and kb.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该知识库为私有，无权访问")
    return kb


# ============================================================================
# 分片上传
# ============================================================================
@router.post("/chunk")
def upload_chunk(
    file: UploadFile = File(...),
    file_hash: str = Form(...),
    chunk_index: int = Form(...),
    user: User = Depends(get_current_user),
):
    """上传单个分片到临时目录"""
    data = file.file.read()
    doc_service.save_chunk(file_hash, chunk_index, data)
    return {"ok": True, "chunk_index": chunk_index}


@router.get("/chunks")
def get_chunks(file_hash: str, user: User = Depends(get_current_user)):
    """查询已上传的分片序号（用于断点续传）"""
    return {"uploaded": doc_service.uploaded_chunks(file_hash)}


@router.post("/merge")
def merge_chunks(data: ChunkMergeRequest, user: User = Depends(get_current_user)):
    """合并分片为完整文件并落盘"""
    if not doc_service.is_allowed(data.filename):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的文件类型")
    path = doc_service.merge_chunks(data.file_hash, data.filename, data.total_chunks)
    return {
        "ok": True,
        "file_hash": data.file_hash,
        "file_type": data.file_type,
        "filename": data.filename,
    }


# ============================================================================
# 解析入库
# ============================================================================
@router.post("/process", response_model=DocumentOut)
def process_document(
    kb_id: int,
    file_hash: str,
    filename: str,
    file_type: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """解析文档并向量入库（同步执行，耗时操作）"""
    kb = _get_owned_kb(db, kb_id, user)

    file_path = doc_service.UPLOAD_DIR / f"{file_hash}_{filename}"
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在，请重新上传")

    # 去重
    existing = (
        db.query(Document)
        .filter(Document.kb_id == kb_id, Document.file_hash == file_hash)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该文档已存在于知识库中")

    try:
        doc, _ = doc_service.process_and_index(db, kb, file_path, filename, file_type)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return doc


# ============================================================================
# 文档列表与删除
# ============================================================================
@router.get("", response_model=list[DocumentOut])
def list_documents(
    kb_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出知识库内文档（含解析状态）"""
    _get_readable_kb(db, kb_id, user)
    return (
        db.query(Document)
        .filter(Document.kb_id == kb_id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除文档并同步清理向量数据"""
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    kb = _get_owned_kb(db, doc.kb_id, user)
    doc_service.delete_document(db, kb, doc)
    return {"ok": True}
