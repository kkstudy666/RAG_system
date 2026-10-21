"""
RAG 知识库系统 —— OCR 识别与文本质量校验
=========================================
迁移自旧 Streamlit 的 core/documents.py OCR 逻辑，
新增扫描版 PDF 识别后的文本质量校验，低质量文档给出明确提示。
"""
from typing import List, Tuple, Any, Optional

from langchain_core.documents import Document


_ocr_reader = None          # RapidOCR 实例缓存
_ocr_reader_failed = False  # 依赖缺失标记


def _get_ocr_reader() -> Optional[Any]:
    """获取 RapidOCR 实例（懒加载，避免重复加载 ONNX 模型）"""
    global _ocr_reader, _ocr_reader_failed
    if _ocr_reader is not None:
        return _ocr_reader
    if _ocr_reader_failed:
        return None
    try:
        from rapidocr_onnxruntime import RapidOCR

        _ocr_reader = RapidOCR()
        return _ocr_reader
    except ImportError:
        _ocr_reader_failed = True
        return None


def _quality_check(
    page_texts: List[str],
    scores: List[float],
) -> dict:
    """
    对 OCR 结果做文本质量校验。

    Returns:
        {
            "char_count": 总有效字符数,
            "avg_score": 平均置信度,
            "page_count": 有效页数,
            "is_low_quality": 是否低质量,
        }
    """
    char_count = sum(len(t) for t in page_texts)
    avg_score = (sum(scores) / len(scores)) if scores else 0.0
    page_count = len(page_texts)

    # 低质量判定：平均置信度低，或有效字符过少（视为空白/图片质量差）
    is_low_quality = (avg_score < 0.6) or (char_count < 50)

    return {
        "char_count": char_count,
        "avg_score": round(avg_score, 3),
        "page_count": page_count,
        "is_low_quality": is_low_quality,
    }


def ocr_pdf_document(
    file_path: str,
    source_name: str,
) -> Tuple[List[Document], dict]:
    """
    使用 OCR 处理扫描版 PDF（常规文本提取失败时的回退方案）。

    使用 pymupdf 将每页渲染为图片，再用 RapidOCR 识别文字。

    Returns:
        (documents, quality_report)：文档列表 + 质量校验报告
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
    page_texts = []
    scores = []

    pdf_doc = fitz.open(file_path)
    total_pages = len(pdf_doc)

    try:
        for page_idx in range(total_pages):
            page = pdf_doc[page_idx]
            # 渲染页面为图片（150 DPI，平衡速度与精度）
            pix = page.get_pixmap(dpi=150)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )

            results, _ = reader(img)

            if results:
                # 按阅读顺序拼接文本（results 已按 y 坐标排序）
                page_scores = []
                texts = []
                for r in results:
                    if r[2] >= 0.3:  # 过滤低置信度单字
                        texts.append(r[1])
                        page_scores.append(float(r[2]))
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
                            },
                        )
                    )
                    page_texts.append(page_text)
                    scores.extend(page_scores)
    finally:
        pdf_doc.close()

    if not documents:
        raise ValueError(
            f"文档 '{source_name}' OCR 识别后仍未提取到文本。"
            f"可能原因：1) 图片质量过低；2) 文档为空白页；3) 文件损坏"
        )

    return documents, _quality_check(page_texts, scores)
