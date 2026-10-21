"""
RAG 知识库系统 —— 知识库接口
==============================
知识库 CRUD、公开/私有切换、全量重建、备份恢复。
"""
import shutil

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, KnowledgeBase, Document
from app.schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseOut
from app.core.deps import get_current_user, get_owned_kb, get_kb_with_access
from app.core import vector_store as vs
from app.services import kb_service
from app.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_CHUNK_SIZE, CHUNK_OVERLAP_RATIO

router = APIRouter(prefix="/kb", tags=["knowledge_bases"])


def _to_out(db: Session, kb: KnowledgeBase) -> KnowledgeBaseOut:
    """ORM 转响应模型并附带文档数"""
    out = KnowledgeBaseOut.model_validate(kb)
    out.document_count = db.query(Document).filter(Document.kb_id == kb.id).count()
    return out


@router.get("", response_model=list[KnowledgeBaseOut])
def list_kbs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """列出当前用户可见的知识库：自己创建的 + 所有公开库"""
    kbs = (
        db.query(KnowledgeBase)
        .filter(
            (KnowledgeBase.owner_id == user.id) | (KnowledgeBase.is_public.is_(True))
        )
        .order_by(KnowledgeBase.created_at.desc())
        .all()
    )
    return [_to_out(db, kb) for kb in kbs]


@router.post("", response_model=KnowledgeBaseOut)
def create_kb(
    data: KnowledgeBaseCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建知识库"""
    chunk_size = data.chunk_size or DEFAULT_CHUNK_SIZE
    chunk_overlap = (
        data.chunk_overlap
        if data.chunk_overlap is not None
        else int(chunk_size * CHUNK_OVERLAP_RATIO)
    )
    kb = KnowledgeBase(
        name=data.name,
        description=data.description,
        owner_id=user.id,
        is_public=data.is_public,
        embedding_model=data.embedding_model or DEFAULT_EMBEDDING_MODEL,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return _to_out(db, kb)


@router.get("/{kb_id}", response_model=KnowledgeBaseOut)
def get_kb(
    kb_id: int,
    kb: KnowledgeBase = Depends(get_kb_with_access),
    db: Session = Depends(get_db),
):
    """获取知识库详情（公开库任意登录用户可读，私有库仅 owner）"""
    return _to_out(db, kb)


@router.patch("/{kb_id}", response_model=KnowledgeBaseOut)
def update_kb(
    kb_id: int,
    data: KnowledgeBaseUpdate,
    kb: KnowledgeBase = Depends(get_owned_kb),
    db: Session = Depends(get_db),
):
    """更新知识库（改名/描述/公开私有切换），仅创建者"""
    if data.name is not None:
        kb.name = data.name
    if data.description is not None:
        kb.description = data.description
    if data.is_public is not None:
        kb.is_public = data.is_public
    db.commit()
    db.refresh(kb)
    return _to_out(db, kb)


@router.delete("/{kb_id}")
def delete_kb(
    kb_id: int,
    kb: KnowledgeBase = Depends(get_owned_kb),
    db: Session = Depends(get_db),
):
    """删除知识库（含向量文件与文档记录），仅创建者"""
    shutil.rmtree(vs.kb_storage_dir(kb_id), ignore_errors=True)
    db.delete(kb)
    db.commit()
    return {"ok": True}


@router.post("/{kb_id}/rebuild")
def rebuild_kb(
    kb_id: int,
    kb: KnowledgeBase = Depends(get_owned_kb),
    db: Session = Depends(get_db),
):
    """全量重建向量索引"""
    count = kb_service.rebuild_kb(db, kb)
    return {"ok": True, "chunk_count": count}


@router.post("/{kb_id}/backup")
def backup_kb(kb_id: int, kb: KnowledgeBase = Depends(get_owned_kb)):
    """备份向量库到磁盘"""
    return kb_service.backup_kb(kb_id)


@router.get("/{kb_id}/backups")
def list_backups(kb_id: int, kb: KnowledgeBase = Depends(get_owned_kb)):
    """列出备份文件"""
    return kb_service.list_backups(kb_id)


@router.post("/{kb_id}/restore")
def restore_kb(
    kb_id: int,
    filename: str,
    kb: KnowledgeBase = Depends(get_owned_kb),
):
    """从备份恢复向量库"""
    if not kb_service.restore_kb(kb_id, filename):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="备份文件不存在")
    return {"ok": True}
