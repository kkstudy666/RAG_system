"""
RAG 知识库系统 —— 嵌入模型加载
================================
模块级缓存避免重复加载同一嵌入模型，迁移自旧 Streamlit 的 core/embeddings.py。
"""
from typing import Dict

from langchain_huggingface import HuggingFaceEmbeddings


# 模块级缓存：{模型名: 嵌入模型实例}
_embedding_cache: Dict[str, HuggingFaceEmbeddings] = {}


def load_embedding_model(model_name: str) -> HuggingFaceEmbeddings:
    """加载嵌入模型（带缓存），首次加载会从 HuggingFace 镜像下载权重"""
    if model_name not in _embedding_cache:
        _embedding_cache[model_name] = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedding_cache[model_name]
