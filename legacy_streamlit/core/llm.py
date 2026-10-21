"""
RAG 知识库智能问答系统 —— LLM 与 QA 链
=======================================
负责获取 LLM 实例（Ollama / OpenAI 兼容 API），
以及基于向量库检索器构建 RAG 问答链。
"""
from typing import Any

import streamlit as st
from langchain_classic.chains import RetrievalQA
from langchain_community.llms import Ollama
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI

from config import RAG_PROMPT


def get_llm(provider: str, **kwargs) -> Any:
    """
    获取 LLM 实例

    Args:
        provider: "ollama" 或 "openai_compatible"
        **kwargs: 其他配置参数

    Returns:
        LLM 实例
    """
    if provider == "ollama":
        return Ollama(
            model=kwargs.get("model", "llama3"),
            base_url=kwargs.get("base_url", "http://localhost:11434"),
            temperature=kwargs.get("temperature", 0.1),
            num_predict=kwargs.get("max_tokens", 2048),
        )
    elif provider == "openai_compatible":
        return ChatOpenAI(
            model=kwargs.get("model", "gpt-3.5-turbo"),
            openai_api_key=kwargs.get("api_key", "not-needed"),
            openai_api_base=kwargs.get("base_url", "http://localhost:1234/v1"),
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 2048),
        )
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")


def rebuild_qa_chain(llm_provider: str, vector_store: FAISS):
    """重新构建 RAG QA 链"""
    try:
        # 获取 LLM 配置
        if llm_provider == "ollama":
            llm = get_llm(
                "ollama",
                model=st.session_state.get("ollama_model", "llama3"),
                base_url=st.session_state.get("ollama_url", "http://localhost:11434"),
                temperature=st.session_state.get("temperature", 0.1),
            )
        else:
            api_key = st.session_state.get("api_key", "")
            if not api_key:
                st.warning("⚠️ 请先输入 API Key")
                st.session_state.qa_chain = None
                return

            llm = get_llm(
                "openai_compatible",
                model=st.session_state.get("api_model", "deepseek-chat"),
                base_url=st.session_state.get("api_url", "https://api.deepseek.com/v1"),
                api_key=api_key,
                temperature=st.session_state.get("temperature", 0.1),
            )

        # 设置检索器
        retrieval_k = st.session_state.get("retrieval_k", 4)
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": retrieval_k},
        )

        # 构建 QA 链
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": RAG_PROMPT},
        )

        st.session_state.qa_chain = qa_chain
        st.session_state.llm_provider = llm_provider

    except Exception as e:
        st.error(f"构建 QA 链失败: {str(e)}")
        st.session_state.qa_chain = None
