"""
RAG 知识库智能问答系统 —— 会话状态管理
=========================================
负责初始化 Streamlit 会话状态、跨 rerun 的一次性提示消息，
以及 LLM 配置签名（用于检测配置变化、自动重建 QA 链）。
"""
import json

import streamlit as st

from config import EMBEDDING_MODELS


def init_session_state():
    """初始化 Streamlit 会话状态"""
    defaults = {
        "messages": [],  # 聊天历史
        "vector_store": None,  # FAISS 向量库实例
        "documents_processed": False,  # 是否有已处理文档
        "doc_info_list": [],  # 已处理文档信息列表
        "chunk_count": 0,  # 文档块总数
        "qa_chain": None,  # RAG 问答链
        "embeddings_model": None,  # 当前使用的嵌入模型
        "llm_provider": None,  # 当前 LLM 提供商
        "processing": False,  # 是否正在处理文档
        "flash": None,  # 跨 rerun 的一次性提示消息 (kind, text)
        "llm_config_signature": "",  # LLM 配置签名，用于检测配置变化
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    # 预设 UI 控件默认值，保证 initialize_app 在渲染侧边栏前也能读取
    if "embedding_model_select" not in st.session_state:
        st.session_state.embedding_model_select = list(EMBEDDING_MODELS.keys())[1]
    if "llm_provider_select" not in st.session_state:
        st.session_state.llm_provider_select = "ollama"


def show_flash():
    """渲染跨 rerun 保留的一次性提示消息"""
    if st.session_state.get("flash"):
        kind, text = st.session_state.flash
        renderer = {"success": st.success, "warning": st.warning, "error": st.error}.get(kind)
        if renderer:
            renderer(text)
        st.session_state.flash = None


def get_llm_config_signature() -> str:
    """计算当前 LLM 相关配置的签名，配置变化时用于触发 QA 链重建"""
    config = {
        "provider": st.session_state.get("llm_provider_select", "ollama"),
        "ollama_model": st.session_state.get("ollama_model", ""),
        "ollama_url": st.session_state.get("ollama_url", ""),
        "api_model": st.session_state.get("api_model", ""),
        "api_url": st.session_state.get("api_url", ""),
        "api_key": st.session_state.get("api_key", ""),
        "temperature": st.session_state.get("temperature", 0.1),
        "retrieval_k": st.session_state.get("retrieval_k", 4),
    }
    return json.dumps(config, sort_keys=True, ensure_ascii=False)
