"""
RAG 知识库系统 —— 依赖注入与权限校验
=======================================
提供当前用户、知识库访问权限 / 管理权限的 FastAPI 依赖。
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, KnowledgeBase
from app.core.security import decode_access_token

# HTTPBearer(auto_error=False)：未携带 token 时返回 None 而非直接报错，便于自定义提示
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """解析 JWT 获取当前登录用户"""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录，请先登录")
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录"
        )
    user = db.get(User, int(payload.get("sub", 0)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def get_kb_with_access(
    kb_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeBase:
    """获取知识库并校验访问权限：公开库所有登录用户可读，私有库仅 owner 可读"""
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    if not kb.is_public and kb.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="该知识库为私有，无权访问"
        )
    return kb


def get_owned_kb(
    kb_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeBase:
    """获取知识库并校验管理权限：仅创建者可管理（修改/删除/上传/备份）"""
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    if kb.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="仅创建者可管理该知识库"
        )
    return kb
