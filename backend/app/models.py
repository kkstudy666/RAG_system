"""
RAG 知识库系统 —— ORM 数据模型
================================
User（用户）、KnowledgeBase（知识库）、Document（文档）、QALog（问答埋点）。
"""
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    """统一的时间戳函数，避免 datetime.utcnow 的弃用告警"""
    return datetime.now(timezone.utc)


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    knowledge_bases = relationship(
        "KnowledgeBase", back_populates="owner", cascade="all, delete-orphan"
    )


class KnowledgeBase(Base):
    """知识库表：公开/私有由 is_public 控制，仅 owner 可管理私有库"""
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    # 构建向量索引时使用的参数，重启后据此恢复
    embedding_model: Mapped[str] = mapped_column(String(256), default="BAAI/bge-small-zh-v1.5")
    chunk_size: Mapped[int] = mapped_column(Integer, default=800)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=120)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    owner = relationship("User", back_populates="knowledge_bases")
    documents = relationship(
        "Document", back_populates="kb", cascade="all, delete-orphan"
    )


class Document(Base):
    """文档表：记录入库状态，删除文档时同步清理向量"""
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kb_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    name: Mapped[str] = mapped_column(String(256))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    file_type: Mapped[str] = mapped_column(String(16))
    size_kb: Mapped[float] = mapped_column(Float, default=0.0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    # 解析状态：pending 待处理 / processing 处理中 / done 已完成 / low_quality 低质量 / error 失败
    status: Mapped[str] = mapped_column(String(32), default="pending")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    kb = relationship("KnowledgeBase", back_populates="documents")


class QALog(Base):
    """问答埋点表：用于耗时统计、准确率分析与测试报告生成"""
    __tablename__ = "qa_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kb_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id"))
    question: Mapped[str] = mapped_column(Text)
    rewritten_question: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
