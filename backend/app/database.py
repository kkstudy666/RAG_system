"""
RAG 知识库系统 —— 数据库连接
==============================
使用 SQLAlchemy 2.x + SQLite，数据文件位于 backend/data/app.db。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import DATA_DIR

SQLALCHEMY_DATABASE_URL = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"

# check_same_thread=False 允许 FastAPI 多线程访问 SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


def get_db():
    """FastAPI 依赖：提供数据库会话，请求结束后自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
