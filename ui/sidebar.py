"""
RAG 知识库智能问答系统 —— 侧边栏 UI
=====================================
渲染文档上传、已加载文档列表、模型配置、高级设置等控件。
"""
import streamlit as st

from config import EMBEDDING_MODELS
from actions import process_documents_action, clear_knowledge_base


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        # Logo 和标题
        st.markdown(
            '<div style="text-align:center;font-size:2.5rem;margin-bottom:0.3rem;">📚</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="text-align:center;font-weight:700;font-size:1.2rem;margin-bottom:1.5rem;">RAG 知识库系统</div>',
            unsafe_allow_html=True,
        )

        # ===== 第一部分：文档上传 =====
        st.markdown("### 📄 文档管理")

        uploaded_files = st.file_uploader(
            "上传文档（支持多文件）",
            type=["pdf", "txt", "md", "docx"],
            accept_multiple_files=True,
            help="支持格式：PDF, TXT, MD, DOCX\n每个文件最大 200MB",
            key="file_uploader",
        )

        col1, col2 = st.columns(2)
        with col1:
            process_btn = st.button(
                "🔄 处理文档",
                width="stretch",
                type="primary",
                disabled=not uploaded_files,
            )
        with col2:
            clear_btn = st.button(
                "🗑️ 清空知识库",
                width="stretch",
                disabled=not st.session_state.documents_processed,
            )

        # 处理文档按钮逻辑
        if process_btn and uploaded_files:
            process_documents_action(uploaded_files)

        # 清空按钮逻辑
        if clear_btn:
            clear_knowledge_base()

        st.markdown("---")

        # ===== 第二部分：已处理文档列表 =====
        st.markdown("### 📋 已加载文档")

        if st.session_state.doc_info_list:
            for doc in st.session_state.doc_info_list:
                file_icon = {"pdf": "📕", "txt": "📄", "md": "📝", "docx": "📘"}.get(
                    doc["type"], "📎"
                )
                st.markdown(
                    f"""<div class="doc-card">
                    {file_icon} <b>{doc['name']}</b><br>
                    <small>分块: {doc['chunks']} | 大小: {doc['size_kb']:.1f} KB | {doc['time']}</small>
                    </div>""",
                    unsafe_allow_html=True,
                )
            st.caption(f"共 {len(st.session_state.doc_info_list)} 个文档, {st.session_state.chunk_count} 个文本块")
        else:
            st.info("尚未上传任何文档")

        st.markdown("---")

        # ===== 第三部分：模型配置 =====
        st.markdown("### ⚙️ 模型配置")

        # LLM 提供商选择
        llm_provider = st.selectbox(
            "LLM 提供商",
            options=["ollama", "openai_compatible"],
            format_func=lambda x: {
                "ollama": "🦙 Ollama (本地开源模型)",
                "openai_compatible": "☁️ OpenAI 兼容 API",
            }[x],
            key="llm_provider_select",
        )

        # 根据提供商显示不同配置
        if llm_provider == "ollama":
            ollama_model = st.text_input(
                "Ollama 模型名称",
                value="llama3",
                help="如: llama3, qwen2, mistral, deepseek-r1 等",
                key="ollama_model",
            )
            ollama_url = st.text_input(
                "Ollama 服务地址",
                value="http://localhost:11434",
                help="默认本地地址",
                key="ollama_url",
            )
        else:
            api_model = st.text_input(
                "模型名称",
                value="deepseek-chat",
                help="如: deepseek-chat, gpt-4, qwen-turbo 等",
                key="api_model",
            )
            api_url = st.text_input(
                "API 地址",
                value="https://api.deepseek.com/v1",
                help="OpenAI 兼容的 API 端点",
                key="api_url",
            )
            api_key = st.text_input(
                "API Key",
                type="password",
                help="输入您的 API Key",
                key="api_key",
            )

        st.markdown("---")

        # 嵌入模型选择
        embedding_choice = st.selectbox(
            "嵌入模型",
            options=list(EMBEDDING_MODELS.keys()),
            index=1,  # 默认中文优化模型
            key="embedding_model_select",
        )

        st.markdown("---")

        # ===== 第四部分：高级设置 =====
        with st.expander("🔧 高级设置"):
            chunk_size = st.slider(
                "文本块大小 (Chunk Size)",
                min_value=100,
                max_value=2000,
                value=500,
                step=50,
                help="较大的块包含更多上下文，较小的块检索更精确",
                key="chunk_size",
            )
            chunk_overlap = st.slider(
                "块重叠大小 (Chunk Overlap)",
                min_value=0,
                max_value=500,
                value=50,
                step=10,
                help="重叠可以避免信息在块边界处丢失",
                key="chunk_overlap",
            )
            retrieval_k = st.slider(
                "检索块数 (Top-K)",
                min_value=1,
                max_value=20,
                value=4,
                step=1,
                help="每次检索返回的最相关文本块数量",
                key="retrieval_k",
            )
            temperature = st.slider(
                "LLM 温度",
                min_value=0.0,
                max_value=1.0,
                value=0.1,
                step=0.05,
                help="越低越精确，越高越有创造性",
                key="temperature",
            )

        st.markdown("---")

        # ===== 底部信息 =====
        st.markdown(
            '<div style="text-align:center;font-size:0.75rem;color:#999;">'
            "Powered by LangChain + FAISS + Streamlit<br>"
            "v1.0.0 | MIT License"
            "</div>",
            unsafe_allow_html=True,
        )

        # 各配置值均已通过 st.session_state 共享，无需返回值
