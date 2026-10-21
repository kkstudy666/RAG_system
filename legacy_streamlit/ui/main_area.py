"""
RAG 知识库智能问答系统 —— 主内容区 UI
=======================================
渲染标题、知识库状态指示、聊天历史与提问输入框。
"""
import streamlit as st

from actions import handle_user_question


def render_main_area():
    """渲染主内容区域"""
    # 标题
    st.markdown('<div class="main-header">📚 RAG 知识库智能问答系统</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">上传文档，构建知识库，智能问答 —— 基于检索增强生成 (RAG) 技术</div>',
        unsafe_allow_html=True,
    )

    # 知识库状态指示
    col_status, col_count, col_blank = st.columns([1, 1, 3])
    with col_status:
        if st.session_state.documents_processed:
            st.markdown(
                f'知识库状态: <span class="status-ready">✅ 就绪</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'知识库状态: <span class="status-empty">⚠️ 未加载文档</span>',
                unsafe_allow_html=True,
            )
    with col_count:
        if st.session_state.documents_processed:
            st.caption(f"📊 {st.session_state.chunk_count} 个文本块已索引")

    st.markdown("---")

    # 渲染聊天历史
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar=msg.get("avatar")):
                st.markdown(msg["content"])
                # 显示来源（仅对助手消息）
                if msg["role"] == "assistant" and msg.get("sources"):
                    with st.expander("📖 查看引用来源"):
                        for i, source in enumerate(msg["sources"], 1):
                            chunk_id = source.get("chunk_id") or "-"
                            st.markdown(
                                f"""<div class="source-box">
                                <div class="title">📎 来源 {i}: {source.get('source', '未知')}</div>
                                <div class="content">{source.get('content', '')[:500]}</div>
                                <div class="meta">分块 ID: {chunk_id}</div>
                                </div>""",
                                unsafe_allow_html=True,
                            )

    # 聊天输入框
    if prompt := st.chat_input(
        "💬 基于知识库内容提问...",
        disabled=not st.session_state.documents_processed,
    ):
        handle_user_question(prompt)
