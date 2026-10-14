"""
RAG 知识库智能问答系统 —— 文档处理
=====================================
文件哈希与类型检测、扫描版 PDF 的 OCR 识别、文档加载，
以及上传文件的保存、加载与文本分块。
"""
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import streamlit as st
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config import UPLOAD_DIR


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
    try:
        import pymupdf as fitz
        import numpy as np
    except ImportError as e:
        raise ImportError(
            "OCR 功能需要安装 rapidocr-onnxruntime、pymupdf 和 numpy。\n"
            "请运行: pip install rapidocr-onnxruntime pymupdf numpy"
        ) from e

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
