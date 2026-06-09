"""
RAG 知识库智能问答系统
========================
基于 LangChain + FAISS + Streamlit 的检索增强生成(RAG)系统
支持 PDF / TXT / MD / DOCX 文件上传，向量化存储，智能问答

Author: RAG System
Version: 1.0.0
"""

# ============================================================================
# 国内用户使用 HuggingFace 镜像站，解决网络无法访问问题
# ============================================================================
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import streamlit as st
import tempfile
import hashlib
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

# ============================================================================
# LangChain 导入
# ============================================================================
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_classic.chains import RetrievalQA
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models.openai import ChatOpenAI
from langchain_core.documents import Document

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
st.markdown(
    """
<style>
    /* 整体字体优化 */
    .stApp {
        font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }

    /* 主标题 */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }

    /* 副标题 */
    .sub-header {
        font-size: 1rem;
        color: #888;
        margin-bottom: 1.5rem;
    }

    /* 侧边栏样式 */
    .sidebar-section {
        padding: 0.5rem 0;
        border-bottom: 1px solid #eee;
        margin-bottom: 0.8rem;
    }

    /* 文档卡片 */
    .doc-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        margin: 0.3rem 0;
        font-size: 0.85rem;
        border-left: 3px solid #667eea;
    }

    /* 引用来源框 */
    .source-box {
        background: #f0f4ff;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
        font-size: 0.85rem;
    }

    .source-box .title {
        font-weight: 600;
        color: #4a4a8a;
        margin-bottom: 0.3rem;
    }

    .source-box .content {
        color: #555;
        max-height: 100px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-size: 0.8rem;
    }

    .source-box .meta {
        color: #999;
        font-size: 0.75rem;
        margin-top: 0.3rem;
    }

    /* 状态指示器 */
    .status-ready {
        color: #28a745;
        font-weight: 600;
    }

    .status-empty {
        color: #dc3545;
        font-weight: 600;
    }

    /* 按钮样式 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }

    /* 聊天气泡优化 */
    .stChatMessage {
        border-radius: 12px;
    }

    /* 文件上传区域 */
    .stFileUploader {
        border-radius: 12px;
    }

    /* 进度条 */
    .stProgress > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================================
# 常量与配置
# ============================================================================
VECTOR_STORE_PATH = Path("./vector_store")
UPLOAD_DIR = Path("./uploaded_files")
VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 支持的嵌入模型
EMBEDDING_MODELS = {
    "all-MiniLM-L6-v2 (英文优化, 384维, 轻量)": "sentence-transformers/all-MiniLM-L6-v2",
    "bge-small-zh-v1.5 (中文优化, 512维, 推荐中文)": "BAAI/bge-small-zh-v1.5",
    "paraphrase-multilingual-MiniLM-L12-v2 (多语言, 384维)": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "all-mpnet-base-v2 (英文最佳, 768维, 较慢)": "sentence-transformers/all-mpnet-base-v2",
}

# ============================================================================
# RAG 提示词模板
# ============================================================================
RAG_PROMPT_TEMPLATE = """你是一个专业的知识库问答助手。请严格基于以下提供的上下文信息来回答问题。

## 规则
1. 只使用下面【上下文】中提供的具体信息来回答
2. 如果上下文中没有相关信息，请明确说"根据已有文档，无法找到相关信息"
3. 不要编造或猜测任何不在上下文中的信息
4. 回答时请引用具体的文档来源
5. 如果信息充足，请给出详细、结构化的回答
6. 使用与用户问题相同的语言回答

## 上下文信息
{context}

## 用户问题
{question}

## 详细回答
"""

RAG_PROMPT = PromptTemplate(
    template=RAG_PROMPT_TEMPLATE,
    input_variables=["context", "question"],
)

# ============================================================================
# 会话状态初始化
# ============================================================================


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
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


# ============================================================================
# 工具函数
# ============================================================================


def get_file_hash(file_bytes: bytes) -> str:
    """计算文件 SHA256 哈希值，用于去重"""
    return hashlib.sha256(file_bytes).hexdigest()[:16]


def detect_file_type(filename: str) -> str:
    """根据文件名后缀检测文件类型"""
    ext = Path(filename).suffix.lower()
    type_map = {
        ".pdf": "pdf",
        ".txt": "txt",
        ".md": "md",
        ".docx": "docx",
        ".doc": "docx",  # .doc 尝试用 docx loader
    }
    return type_map.get(ext, "unknown")


@st.cache_resource(show_spinner=False)
def _get_ocr_reader() -> Any:
    """
    获取 RapidOCR 实例（使用缓存避免重复加载 ONNX 模型）

    Returns:
        RapidOCR 实例，如果 rapidocr 未安装则返回 None
    """
    try:
        from rapidocr_onnxruntime import RapidOCR
        return RapidOCR()
    except ImportError:
        return None


def _ocr_pdf_document(file_path: str, source_name: str) -> List[Document]:
    """
    使用 OCR 处理扫描版 PDF（当常规文本提取失败时的回退方案）

    使用 pymupdf 将每页渲染为图片，再用 RapidOCR 识别文字。

    Args:
        file_path: PDF 文件路径
        source_name: 源文件名（用于元数据）

    Returns:
        Document 对象列表，每个对象包含一页的 OCR 识别文本

    Raises:
        ImportError: 缺少必要的 OCR 依赖
        ValueError: OCR 也未识别到任何文本
    """
    import fitz
    import numpy as np

    reader = _get_ocr_reader()
    if reader is None:
        raise ImportError(
            "OCR 功能需要安装 rapidocr-onnxruntime 和 pymupdf。\n"
            "请运行: pip install rapidocr-onnxruntime pymupdf"
        )

    documents = []
    pdf_doc = fitz.open(file_path)
    total_pages = len(pdf_doc)

    try:
        for page_idx in range(total_pages):
            page = pdf_doc[page_idx]
            # 渲染页面为图片（150 DPI，平衡速度与精度）
            pix = page.get_pixmap(dpi=150)
            img = np.frombuffer(
                pix.samples, dtype=np.uint8
            ).reshape(pix.height, pix.width, pix.n)

            # OCR 识别
            results, _ = reader(img)

            if results:
                # 按阅读顺序拼接文本（从上到下）
                # results 已按 y 坐标排序
                texts = [r[1] for r in results if r[2] >= 0.3]
                page_text = "\n".join(texts).strip()

                if page_text:
                    documents.append(
                        Document(
                            page_content=page_text,
                            metadata={
                                "source": source_name,
                                "file_type": "pdf",
                                "page": page_idx + 1,
                                "ocr_method": "rapidocr",
                            }
                        )
                    )
    finally:
        pdf_doc.close()

    if not documents:
        raise ValueError(
            f"文档 '{source_name}' OCR 识别后仍未提取到文本。"
            f"可能原因：1) 图片质量过低；2) 文档为空白页；3) 文件损坏"
        )

    return documents


def load_single_document(file_path: str, file_type: str) -> List[Document]:
    """加载单个文档并返回 LangChain Document 对象列表"""
    loaders = {
        "pdf": PyPDFLoader,
        "txt": TextLoader,
        "md": TextLoader,
        "docx": Docx2txtLoader,
    }

    loader_class = loaders.get(file_type)
    if loader_class is None:
        raise ValueError(f"不支持的文件类型: {file_type}")

    if file_type in ("txt", "md"):
        loader = loader_class(file_path, encoding="utf-8", autodetect_encoding=True)
    else:
        loader = loader_class(file_path)
    documents = loader.load()

    # 过滤掉空页面（扫描版 PDF 等无法提取文本的页面）
    source_name = Path(file_path).name
    valid_docs = []
    for doc in documents:
        text = doc.page_content.strip()
        if text:
            doc.metadata["source"] = source_name
            doc.metadata["file_type"] = file_type
            valid_docs.append(doc)

    if not valid_docs:
        # PDF 文件：常规提取失败时尝试 OCR 回退
        if file_type == "pdf":
            st.warning(f"📄 '{source_name}' 常规文本提取为空，正在尝试 OCR 识别...")
            try:
                ocr_docs = _ocr_pdf_document(file_path, source_name)
                if ocr_docs:
                    st.success(f"✅ OCR 识别成功：从 '{source_name}' 提取了 {len(ocr_docs)} 页文本")
                    return ocr_docs
            except ImportError as e:
                raise ValueError(
                    f"文档 '{source_name}' 为扫描版 PDF（无可选文本），"
                    f"且 OCR 依赖未安装。请运行:\n"
                    f"pip install rapidocr-onnxruntime pymupdf"
                ) from e
        # PDF OCR 也失败，或非 PDF 文件
        raise ValueError(
            f"文档 '{source_name}' 无法提取文本内容。\n"
            f"可能原因：1) PDF 为扫描版/图片型，需 OCR 识别（已尝试但失败）；"
            f"2) DOCX 内容为嵌入图片；3) 文件损坏或加密"
        )

    return valid_docs


def process_uploaded_files(
    uploaded_files,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> tuple[List[Document], List[Dict[str, Any]]]:
    """
    处理上传的文件：保存、加载、分块

    Args:
        uploaded_files: Streamlit 上传的文件对象列表
        chunk_size: 文本分块大小
        chunk_overlap: 分块重叠大小

    Returns:
        (all_chunks, doc_info_list): 所有文档块列表 + 文档信息列表
    """
    all_chunks = []
    doc_info_list = []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", ".", "！", "!", "？", "?", "；", ";", " ", ""],
        length_function=len,
    )

    progress_bar = st.progress(0)
    status_text = st.empty()

    total_files = len(uploaded_files)

    for idx, uploaded_file in enumerate(uploaded_files):
        file_name = uploaded_file.name
        file_type = detect_file_type(file_name)

        if file_type == "unknown":
            st.warning(f"⚠️ 跳过不支持的文件类型: {file_name}")
            continue

        status_text.text(f"正在处理: {file_name} ({idx + 1}/{total_files})")

        try:
            # 保存文件到临时目录
            file_bytes = uploaded_file.read()
            file_hash = get_file_hash(file_bytes)

            # 保存到上传目录
            save_path = UPLOAD_DIR / f"{file_hash}_{file_name}"
            save_path.write_bytes(file_bytes)

            # 加载文档
            documents = load_single_document(str(save_path), file_type)

            # 分块
            chunks = text_splitter.split_documents(documents)

            # 为每个块添加唯一标识
            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_id"] = f"{file_hash}_{i}"
                chunk.metadata["file_hash"] = file_hash

            all_chunks.extend(chunks)

            # 记录文档信息
            doc_info_list.append(
                {
                    "name": file_name,
                    "hash": file_hash,
                    "type": file_type,
                    "chunks": len(chunks),
                    "size_kb": len(file_bytes) / 1024,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            )

        except Exception as e:
            st.error(f"❌ 处理文件 '{file_name}' 失败: {str(e)}")
            continue

        # 更新进度条
        progress_bar.progress((idx + 1) / total_files)

    progress_bar.empty()
    status_text.empty()

    return all_chunks, doc_info_list


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


# ============================================================================
# UI 组件
# ============================================================================


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
                use_container_width=True,
                type="primary",
                disabled=not uploaded_files,
            )
        with col2:
            clear_btn = st.button(
                "🗑️ 清空知识库",
                use_container_width=True,
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

        return {
            "llm_provider": llm_provider,
            "embedding_choice": embedding_choice,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "retrieval_k": retrieval_k,
            "temperature": temperature,
        }


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
                            st.markdown(
                                f"""<div class="source-box">
                                <div class="title">📎 来源 {i}: {source.get('source', '未知')}</div>
                                <div class="content">{source.get('content', '')[:500]}</div>
                                <div class="meta">相关度: {source.get('score', 0):.4f}</div>
                                </div>""",
                                unsafe_allow_html=True,
                            )

    # 聊天输入框
    if prompt := st.chat_input(
        "💬 基于知识库内容提问...",
        disabled=not st.session_state.documents_processed,
    ):
        handle_user_question(prompt)


# ============================================================================
# 核心业务逻辑
# ============================================================================


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
            llm_provider = st.session_state.get("llm_provider_select", "ollama")

            if embedding_choice is None:
                embedding_choice = list(EMBEDDING_MODELS.keys())[1]

            # 加载嵌入模型
            model_name = EMBEDDING_MODELS[embedding_choice]
            with st.status(f"加载嵌入模型: {embedding_choice}...", expanded=False) as status:
                embeddings = load_embedding_model(model_name)
                status.update(label="嵌入模型加载完成 ✅", state="complete")

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

            # 构建 QA 链
            rebuild_qa_chain(llm_provider, vector_store)

            # 记录处理数量
            new_doc_count = len(doc_info_list)
            new_chunk_count = len(all_chunks)

            st.success(f"✅ 成功处理 {new_doc_count} 个文档，共 {new_chunk_count} 个文本块")
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
    import shutil

    if VECTOR_STORE_PATH.exists():
        shutil.rmtree(VECTOR_STORE_PATH)
        VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

    # 删除上传文件
    if UPLOAD_DIR.exists():
        shutil.rmtree(UPLOAD_DIR)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    st.success("✅ 知识库已清空")
    st.rerun()


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
            verbose=False,
        )

        st.session_state.qa_chain = qa_chain
        st.session_state.llm_provider = llm_provider

    except Exception as e:
        st.error(f"构建 QA 链失败: {str(e)}")
        st.session_state.qa_chain = None


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
                        "score": doc.metadata.get("score", None),
                        "chunk_id": doc.metadata.get("chunk_id", ""),
                    }
                )

            # 显示回答
            message_placeholder.markdown(answer)

            # 显示来源
            if sources:
                with st.expander("📖 查看引用来源"):
                    for i, source in enumerate(sources, 1):
                        st.markdown(
                            f"""<div class="source-box">
                            <div class="title">📎 来源 {i}: {source['source']}</div>
                            <div class="content">{source['content'][:500]}</div>
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


# ============================================================================
# 初始化逻辑（应用启动时执行）
# ============================================================================


def initialize_app():
    """应用初始化：加载已有向量库"""
    embedding_choice = st.session_state.get("embedding_model_select")
    if embedding_choice is None:
        embedding_choice = list(EMBEDDING_MODELS.keys())[1]
        st.session_state.embedding_model_select = embedding_choice

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

                        # 重建 QA 链
                        llm_provider = st.session_state.get("llm_provider_select", "ollama")
                        rebuild_qa_chain(llm_provider, vector_store)

                        st.sidebar.success(f"✅ 已加载知识库 ({index.ntotal} 个文本块)")
            except Exception as e:
                st.sidebar.warning(f"加载已有知识库失败: {str(e)}")


# ============================================================================
# 主入口
# ============================================================================


def main():
    """主函数"""
    init_session_state()

    # 渲染侧边栏并获取配置
    config = render_sidebar()

    # 初始化应用（首次加载时）
    initialize_app()

    # 渲染主内容区域
    render_main_area()


if __name__ == "__main__":
    main()
