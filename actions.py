"""
RAG 知识库智能问答系统 —— 业务动作
=====================================
编排核心业务：文档处理入库、清空知识库、处理用户提问。
被 UI 层（ui.sidebar / ui.main_area）调用。
"""
import shutil

import streamlit as st

from config import EMBEDDING_MODELS, VECTOR_STORE_PATH, UPLOAD_DIR
from state import get_llm_config_signature
from core.documents import process_uploaded_files
from core.storage import (
    save_doc_info,
    load_saved_embedding_model,
    save_embedding_model,
)
from core.embeddings import load_embedding_model
from core.vector_store import create_or_update_vector_store
from core.llm import rebuild_qa_chain


def process_documents_action(uploaded_files):
    """处理文档上传的核心逻辑"""
    if not uploaded_files:
        st.warning("请先上传文件")
        return

    st.session_state.processing = True

    with st.spinner("🔄 正在处理文档..."):
        try:
            # 获取参数
            chunk_size = st.session_state.get("chunk_size", 500)
            chunk_overlap = st.session_state.get("chunk_overlap", 50)
            embedding_choice = st.session_state.get("embedding_model_select")

            # 处理文档（分块）
            all_chunks, doc_info_list = process_uploaded_files(
                uploaded_files, chunk_size, chunk_overlap
            )

            if not all_chunks:
                st.error(
                    "没有成功处理的文档。可能原因：\n\n"
                    "1) PDF 为扫描版/图片型（需 OCR 识别）\n"
                    "2) DOCX 内容为嵌入图片而非文本\n"
                    "3) 文件损坏或加密\n\n"
                    "请检查上方具体文件的错误信息，或上传包含可选文本的文档。"
                )
                st.session_state.processing = False
                return

            # 判断是新建还是追加
            mode = "create" if not st.session_state.documents_processed else "add"
            if mode == "add":
                existing_docs = {d["hash"] for d in st.session_state.doc_info_list}
                new_chunks = [
                    c for c in all_chunks if c.metadata.get("file_hash") not in existing_docs
                ]
                new_docs = [d for d in doc_info_list if d["hash"] not in existing_docs]

                if not new_chunks:
                    st.info("所有文档已存在，无需重复添加")
                    st.session_state.processing = False
                    return
                all_chunks = new_chunks
                doc_info_list = new_docs

            # 确定嵌入模型：新建用 UI 选择，追加沿用索引原模型（保证维度一致）
            if mode == "create":
                model_name = EMBEDDING_MODELS[embedding_choice]
            else:
                model_name = load_saved_embedding_model() or EMBEDDING_MODELS[embedding_choice]

            with st.status(f"加载嵌入模型: {model_name}...", expanded=False) as status:
                embeddings = load_embedding_model(model_name)
                status.update(label="嵌入模型加载完成 ✅", state="complete")

            # 创建或更新向量库
            with st.status("构建向量索引...", expanded=False) as status:
                vector_store = create_or_update_vector_store(
                    all_chunks, embeddings, mode=mode
                )
                status.update(label="向量索引构建完成 ✅", state="complete")

            if vector_store is None:
                st.error("向量库构建失败")
                st.session_state.processing = False
                return

            # 持久化索引使用的嵌入模型（新建/追加都记录，供重启加载时校验维度）
            save_embedding_model(model_name)

            # 更新会话状态
            if mode == "create":
                st.session_state.vector_store = vector_store
                st.session_state.doc_info_list = doc_info_list
                st.session_state.chunk_count = len(all_chunks)
            else:
                st.session_state.vector_store = vector_store
                st.session_state.doc_info_list.extend(doc_info_list)
                st.session_state.chunk_count += len(all_chunks)

            st.session_state.embeddings_model = model_name
            st.session_state.documents_processed = True
            st.session_state.processing = False

            # 持久化文档信息，重启后可恢复已加载文档列表
            save_doc_info(st.session_state.doc_info_list)

            # 重建 QA 链并记录配置签名
            llm_provider = st.session_state.get("llm_provider_select", "ollama")
            rebuild_qa_chain(llm_provider, vector_store)
            st.session_state.llm_config_signature = get_llm_config_signature()

            # 记录处理数量
            new_doc_count = len(doc_info_list)
            new_chunk_count = len(all_chunks)

            # 跨 rerun 显示成功提示
            st.session_state.flash = (
                "success",
                f"✅ 成功处理 {new_doc_count} 个文档，共 {new_chunk_count} 个文本块",
            )
            st.rerun()

        except Exception as e:
            st.error(f"文档处理失败: {str(e)}")
            st.session_state.processing = False


def clear_knowledge_base():
    """清空知识库"""
    st.session_state.vector_store = None
    st.session_state.documents_processed = False
    st.session_state.doc_info_list = []
    st.session_state.chunk_count = 0
    st.session_state.qa_chain = None
    st.session_state.messages = []
    st.session_state.embeddings_model = None

    # 删除向量库文件
    if VECTOR_STORE_PATH.exists():
        shutil.rmtree(VECTOR_STORE_PATH)
        VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

    # 删除上传文件
    if UPLOAD_DIR.exists():
        shutil.rmtree(UPLOAD_DIR)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    st.session_state.flash = ("success", "✅ 知识库已清空")
    st.rerun()


def handle_user_question(prompt: str):
    """处理用户提问"""
    if not st.session_state.qa_chain:
        st.error("QA 链未初始化，请先处理文档并配置 LLM")
        return

    # 添加用户消息
    st.session_state.messages.append(
        {"role": "user", "content": prompt, "avatar": "👤"}
    )

    # 显示用户消息
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # 生成回答
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        message_placeholder.markdown("💭 正在检索知识库并生成回答...")

        try:
            # 调用 RAG QA 链
            result = st.session_state.qa_chain.invoke({"query": prompt})

            answer = result.get("result", "无法生成回答")
            source_docs = result.get("source_documents", [])

            # 提取来源信息
            sources = []
            for doc in source_docs:
                sources.append(
                    {
                        "source": doc.metadata.get("source", "未知文档"),
                        "content": doc.page_content,
                        "chunk_id": doc.metadata.get("chunk_id", ""),
                        "page": doc.metadata.get("page", None),
                    }
                )

            # 显示回答
            message_placeholder.markdown(answer)

            # 显示来源
            if sources:
                with st.expander("📖 查看引用来源"):
                    for i, source in enumerate(sources, 1):
                        chunk_id = source.get("chunk_id") or "-"
                        st.markdown(
                            f"""<div class="source-box">
                            <div class="title">📎 来源 {i}: {source['source']}</div>
                            <div class="content">{source['content'][:500]}</div>
                            <div class="meta">分块 ID: {chunk_id}</div>
                            </div>""",
                            unsafe_allow_html=True,
                        )

            # 保存消息
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "avatar": "🤖",
                    "sources": sources,
                }
            )

        except Exception as e:
            error_msg = f"❌ 生成回答失败: {str(e)}"
            message_placeholder.error(error_msg)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_msg,
                    "avatar": "🤖",
                    "sources": [],
                }
            )
