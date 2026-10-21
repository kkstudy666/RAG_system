"""
RAG 知识库智能问答系统 —— 主入口
==================================
基于 LangChain + FAISS + Streamlit 的检索增强生成(RAG)系统
支持 PDF / TXT / MD / DOCX 文件上传，向量化存储，智能问答

Author: RAG System
Version: 1.0.0
"""
# 必须最先导入：config 内部会设置 HuggingFace 镜像环境变量
import config

import streamlit as st

from config import CUSTOM_CSS, EMBEDDING_MODELS, VECTOR_STORE_PATH
from state import init_session_state, show_flash, get_llm_config_signature
from core.embeddings import load_embedding_model, model_name_to_key
from core.vector_store import load_existing_vector_store
from core.storage import load_doc_info, load_saved_embedding_model
from core.llm import rebuild_qa_chain
from ui.sidebar import render_sidebar
from ui.main_area import render_main_area

# ============================================================================
# 页面配置
# ============================================================================
st.set_page_config(
    page_title="RAG 知识库智能问答系统",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# 自定义 CSS 样式
# ============================================================================
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================================
# 初始化逻辑（应用启动时执行）
# ============================================================================


def initialize_app():
    """应用初始化：加载已有向量库（在渲染侧边栏前调用，保证 UI 状态一致）"""
    # 优先使用上次构建索引时保存的嵌入模型，避免切换 UI 模型导致维度不匹配
    saved_model = load_saved_embedding_model()
    if saved_model:
        model_name = saved_model
        # 同步侧边栏选中项为索引实际使用的模型
        key = model_name_to_key(saved_model)
        if key:
            st.session_state.embedding_model_select = key
    else:
        embedding_choice = st.session_state.get("embedding_model_select")
        model_name = EMBEDDING_MODELS[embedding_choice]

    # 检查是否有已存在的向量库
    if VECTOR_STORE_PATH.exists() and (VECTOR_STORE_PATH / "index.faiss").exists():
        if not st.session_state.documents_processed:
            try:
                with st.spinner("正在加载已有知识库..."):
                    embeddings = load_embedding_model(model_name)
                    vector_store = load_existing_vector_store(embeddings)

                    if vector_store:
                        st.session_state.vector_store = vector_store
                        st.session_state.documents_processed = True
                        st.session_state.embeddings_model = model_name

                        # 统计信息
                        index = vector_store.index
                        st.session_state.chunk_count = index.ntotal

                        # 恢复上次加载的文档信息列表
                        restored_info = load_doc_info()
                        if restored_info:
                            st.session_state.doc_info_list = restored_info
                        else:
                            # 旧版本没有 doc_info.json，生成占位条目
                            # 下次重新上传文档后会自动更新为完整信息
                            st.session_state.doc_info_list = [
                                {
                                    "name": "（历史文档 — 重新上传后显示详细信息）",
                                    "hash": "legacy",
                                    "type": "unknown",
                                    "chunks": index.ntotal,
                                    "size_kb": 0,
                                    "time": "未知",
                                }
                            ]

                        # 跨 rerun 显示加载成功提示
                        st.session_state.flash = ("success", f"✅ 已加载知识库 ({index.ntotal} 个文本块)")
            except Exception as e:
                st.sidebar.warning(f"加载已有知识库失败: {str(e)}")


# ============================================================================
# 主入口
# ============================================================================


def main():
    """主函数"""
    init_session_state()

    # 先加载已有知识库，再渲染侧边栏，保证首次启动时 UI 状态正确
    initialize_app()

    # 渲染一次性提示（处理成功 / 加载成功等）
    show_flash()

    # 渲染侧边栏（含文档上传、模型配置等控件）
    render_sidebar()

    # LLM 配置变化时自动重建 QA 链
    if st.session_state.documents_processed and st.session_state.vector_store is not None:
        signature = get_llm_config_signature()
        if signature != st.session_state.get("llm_config_signature"):
            rebuild_qa_chain(
                st.session_state.get("llm_provider_select", "ollama"),
                st.session_state.vector_store,
            )
            st.session_state.llm_config_signature = signature

    # 渲染主内容区域
    render_main_area()


if __name__ == "__main__":
    main()
