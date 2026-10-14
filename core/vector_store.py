"""
RAG 知识库智能问答系统 —— 向量库
=================================
负责 FAISS 向量库的创建、追加与从磁盘加载。
"""
from typing import List, Optional

import streamlit as st
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from config import VECTOR_STORE_PATH


def create_or_update_vector_store(
    chunks: List[Document],
    embeddings: HuggingFaceEmbeddings,
    mode: str = "create",
) -> Optional[FAISS]:
    """
    创建或更新 FAISS 向量库

    Args:
        chunks: 文档块列表
        embeddings: 嵌入模型
        mode: "create" 新建, "add" 追加

    Returns:
        FAISS 向量库实例
    """
    if not chunks:
        return None

    try:
        if mode == "add" and st.session_state.vector_store is not None:
            # 追加到现有向量库
            st.session_state.vector_store.add_documents(chunks)
            vector_store = st.session_state.vector_store
        else:
            # 新建向量库
            vector_store = FAISS.from_documents(chunks, embeddings)

        # 持久化保存
        vector_store.save_local(str(VECTOR_STORE_PATH))
        return vector_store

    except Exception as e:
        st.error(f"创建向量库失败: {str(e)}")
        return None


def load_existing_vector_store(embeddings: HuggingFaceEmbeddings) -> Optional[FAISS]:
    """从磁盘加载已存在的向量库"""
    index_file = VECTOR_STORE_PATH / "index.faiss"
    if not index_file.exists():
        return None

    try:
        vector_store = FAISS.load_local(
            str(VECTOR_STORE_PATH),
            embeddings,
            allow_dangerous_deserialization=True,
        )
        return vector_store
    except Exception as e:
        st.warning(f"加载已有向量库失败: {str(e)}，将重新创建")
        return None
