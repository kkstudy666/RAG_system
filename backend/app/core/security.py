"""
RAG 知识库系统 —— 安全与鉴权
==============================
JWT 签发/校验 + bcrypt 密码哈希。
直接使用 bcrypt 库（而非 passlib），规避 passlib 与 bcrypt 4.x 的兼容问题。
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES


# ============================================================================
# 密码哈希
# ============================================================================
def hash_password(password: str) -> str:
    """对明文密码做 bcrypt 哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码与哈希是否匹配"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# ============================================================================
# JWT
# ============================================================================
def create_access_token(user_id: int, username: str) -> str:
    """签发 JWT access token，payload 携带 user_id 与 username"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """解析 JWT，失败返回 None"""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
