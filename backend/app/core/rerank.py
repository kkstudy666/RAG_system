"""
RAG 知识库系统 —— BGE-Rerank 重排序
=====================================
使用 BGE-Reranker cross-encoder 对粗召回的 Top-K 候选做二次精排，
提升检索准确率。模型懒加载，加载失败时自动降级为原始排序。
"""
from typing import List, Optional

from langchain_core.documents import Document

from app.config import RERANK_MODEL


_reranker = None          # 已加载的 CrossEncoder 实例
_reranker_failed = False  # 加载失败标记，避免重复尝试


def _get_reranker():
    """懒加载 BGE-Reranker，加载失败返回 None"""
    global _reranker, _reranker_failed
    if _reranker is not None:
        return _reranker
    if _reranker_failed:
        return None
    try:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(RERANK_MODEL)
        return _reranker
    except Exception as e:  # noqa: BLE001 模型下载失败/依赖缺失时降级
        _reranker_failed = True
        print(f"[rerank] BGE-Reranker 加载失败，本次将降级为无重排: {e}")
        return None


def rerank_documents(
    query: str,
    docs: List[Document],
    top_n: int,
) -> List[Document]:
    """
    对候选文档做相关性重排，返回分数最高的 top_n 个文档。

    Args:
        query: 用户提问（或改写后的查询）
        docs: 粗召回的候选文档列表
        top_n: 精排后返回的文档数

    Returns:
        按相关性降序的文档列表（长度 <= top_n）
    """
    if not docs:
        return docs

    reranker = _get_reranker()
    # 未加载重排模型，或候选数不超过目标数时直接返回
    if reranker is None or len(docs) <= top_n:
        return docs[:top_n]

    try:
        pairs = [(query, doc.page_content) for doc in docs]
        scores = reranker.predict(pairs)
        scored = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in scored[:top_n]]
    except Exception as e:  # noqa: BLE001 重排失败时降级
        print(f"[rerank] 重排失败，返回原始排序: {e}")
        return docs[:top_n]
