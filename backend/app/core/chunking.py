"""
RAG 知识库系统 —— 文本分块策略
================================
语义分块（递归 + 中文标点分隔符） + 重叠分块（默认重叠率 15%），
针对不同文档类型适配不同的分块大小，并为每个块生成稳定唯一 id。
"""
from typing import List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import CHUNK_SIZE_MAP, CHUNK_OVERLAP_RATIO, DEFAULT_CHUNK_SIZE

# 中文优先的分隔符顺序：段落 → 换行 → 中文句号 → 英文句号 → 感叹/问号 → 分号 → 空格
_SEPARATORS = ["\n\n", "\n", "。", ".", "！", "!", "？", "?", "；", ";", " ", ""]


def get_chunk_size_for_type(file_type: str, override: Optional[int] = None) -> int:
    """按文档类型返回分块大小，支持外部覆盖"""
    if override and override > 0:
        return override
    return CHUNK_SIZE_MAP.get(file_type, DEFAULT_CHUNK_SIZE)


def compute_overlap(chunk_size: int, ratio: float = CHUNK_OVERLAP_RATIO) -> int:
    """按比例计算重叠长度（默认 15%），避免上下文在块边界断裂"""
    return max(int(chunk_size * ratio), 1)


def build_splitter(chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
    """构建递归语义分块器"""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=_SEPARATORS,
        length_function=len,
    )


def split_documents(
    documents: List[Document],
    file_hash: str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[Document]:
    """
    对文档做分块，并为每个块写入稳定唯一 id 与文件哈希元数据。

    块 id 形如 `{file_hash}_{idx}`，用于 FAISS 索引的精确删除（删文档同步清向量）。
    """
    splitter = build_splitter(chunk_size, chunk_overlap)
    chunks = splitter.split_documents(documents)

    for idx, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"{file_hash}_{idx}"
        chunk.metadata["file_hash"] = file_hash

    return chunks
