"""
RAG 知识库智能问答系统 —— 嵌入模型
=====================================
负责加载 HuggingFace 嵌入模型（带缓存），
以及根据模型名反查 UI 选项 key。
"""
from typing import Optional

import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings

from config import EMBEDDING_MODELS


@st.cache_resource(show_spinner=False)
def load_embedding_model(model_name: str) -> HuggingFaceEmbeddings:
    """
    加载嵌入模型（使用缓存避免重复加载）

    Args:
        model_name: HuggingFace 模型名称

    Returns:
        HuggingFaceEmbeddings 实例
    """
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def model_name_to_key(model_name: str) -> Optional[str]:
    """根据模型名反查 UI 选项 key（用于同步侧边栏选中项）"""
    for key, value in EMBEDDING_MODELS.items():
        if value == model_name:
            return key
    return None
