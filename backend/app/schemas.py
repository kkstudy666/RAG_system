"""
RAG 知识库系统 —— Pydantic 请求/响应模型
==========================================
"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field


# ============================================================================
# 鉴权
# ============================================================================
class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


# ============================================================================
# 知识库
# ============================================================================
class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    is_public: bool = False
    embedding_model: Optional[str] = None
    chunk_size: Optional[int] = Field(default=None, ge=100, le=4000)
    chunk_overlap: Optional[int] = Field(default=None, ge=0, le=2000)


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class KnowledgeBaseOut(BaseModel):
    id: int
    name: str
    description: str
    owner_id: int
    is_public: bool
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    created_at: datetime
    document_count: int = 0

    class Config:
        from_attributes = True


# ============================================================================
# 文档
# ============================================================================
class DocumentOut(BaseModel):
    id: int
    kb_id: int
    name: str
    file_hash: str
    file_type: str
    size_kb: float
    chunk_count: int
    status: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# 分片上传
# ============================================================================
class ChunkMergeRequest(BaseModel):
    filename: str
    kb_id: int
    total_chunks: int
    file_hash: str
    file_type: str


# ============================================================================
# 对话
# ============================================================================
class ChatMessage(BaseModel):
    role: str  # user / assistant
    content: str


class ChatRequest(BaseModel):
    kb_id: int
    question: str
    history: List[ChatMessage] = []
    config: Dict[str, Any] = {}  # LLM/检索参数（provider、模型、温度、Top-K 等）


class ChatHistoryResponse(BaseModel):
    kb_id: int
    messages: List[ChatMessage]


# ============================================================================
# 配置
# ============================================================================
class SystemConfig(BaseModel):
    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieval_top_k: int = 4
    temperature: float = 0.1
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    llm_provider: str = "ollama"          # ollama / openai_compatible
    ollama_model: str = "llama3"
    ollama_url: str = "http://localhost:11434"
    api_model: str = "deepseek-chat"
    api_url: str = "https://api.deepseek.com/v1"
    api_key: str = ""


class MetricsOut(BaseModel):
    total_qa: int = 0
    avg_latency_ms: float = 0.0
