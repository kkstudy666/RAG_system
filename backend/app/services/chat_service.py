"""
RAG 知识库系统 —— 检索增强问答编排
====================================
核心流水线：查询改写 → 向量粗召回 Top-K → BGE-Rerank 精排 → 组装上下文
→ LLM 流式生成。逐 token 产出 SSE 事件，并写入问答埋点用于可观测性。
"""
import json
import time
from typing import Iterator, Dict, Any, List

from sqlalchemy.orm import Session

from app.models import KnowledgeBase, QALog
from app.core.embeddings import load_embedding_model
from app.core import vector_store as vs
from app.core.rerank import rerank_documents
from app.core.query_rewrite import rewrite_query
from app.core.llm import get_llm, stream_llm
from app.core.prompts import RAG_PROMPT
from app.config import RETRIEVAL_TOP_K, MAX_CONTEXT_CHARS


def _build_context(docs: List) -> str:
    """将精排后的文档片段拼接为上下文，控制总长度避免超限"""
    parts = []
    total = 0
    for i, d in enumerate(docs, 1):
        src = d.metadata.get("source", "未知")
        snippet = d.page_content.strip()
        parts.append(f"[片段 {i} | 来源: {src}]\n{snippet}")
        total += len(snippet)
        if total > MAX_CONTEXT_CHARS:
            break
    return "\n\n".join(parts)


def _sources_from_docs(docs: List) -> List[dict]:
    """提取来源信息用于前端引用展示与埋点"""
    return [
        {
            "source": d.metadata.get("source", "未知"),
            "content": d.page_content,
            "chunk_id": d.metadata.get("chunk_id", ""),
            "page": d.metadata.get("page", None),
        }
        for d in docs
    ]


def run_rag_stream(
    db: Session,
    user_id: int,
    kb: KnowledgeBase,
    question: str,
    history: List[Dict[str, str]],
    config: Dict[str, Any],
) -> Iterator[Dict[str, Any]]:
    """
    RAG 流式问答生成器，产出 SSE 事件字典：

    - {"type": "sources", "sources": [...], "rewritten_question": "..."}
    - {"type": "token", "content": "..."}
    - {"type": "done", "latency_ms": ...}
    - {"type": "error", "content": "..."}
    """
    start = time.time()

    # 1. 查询改写（多轮模糊提问 → 精准检索语句）
    rewritten = rewrite_query(question, history, config)

    # 2. 向量粗召回
    embeddings = load_embedding_model(kb.embedding_model)
    store = vs.load_vector_store(kb.id, embeddings)
    if store is None:
        yield {"type": "error", "content": "知识库为空，请先上传文档"}
        return

    candidate_docs = store.similarity_search(rewritten, k=RETRIEVAL_TOP_K)
    if not candidate_docs:
        yield {"type": "error", "content": "未检索到相关内容，请尝试换一种问法"}
        return

    # 3. BGE-Rerank 精排
    top_k = int(config.get("retrieval_top_k", 4))
    docs = rerank_documents(rewritten, candidate_docs, top_k)

    # 4. 组装上下文与来源
    context = _build_context(docs)
    prompt = RAG_PROMPT.format(context=context, question=question)
    sources = _sources_from_docs(docs)

    # 先下发来源与改写结果，前端可先渲染引用
    yield {
        "type": "sources",
        "sources": sources,
        "rewritten_question": rewritten,
    }

    # 5. LLM 流式生成
    answer_parts: List[str] = []
    try:
        llm = get_llm(config)
        for token in stream_llm(llm, prompt):
            answer_parts.append(token)
            yield {"type": "token", "content": token}
    except Exception as e:  # noqa: BLE001
        yield {"type": "error", "content": f"生成回答失败：{e}"}

    answer = "".join(answer_parts)
    latency = round((time.time() - start) * 1000, 1)

    # 6. 问答埋点（耗时 / 改写 / 来源 / 答案）
    try:
        db.add(
            QALog(
                user_id=user_id,
                kb_id=kb.id,
                question=question,
                rewritten_question=rewritten,
                answer=answer,
                sources_json=json.dumps(sources, ensure_ascii=False),
                latency_ms=latency,
            )
        )
        db.commit()
    except Exception as e:  # noqa: BLE001
        print(f"[chat_service] 写入问答埋点失败: {e}")

    yield {"type": "done", "latency_ms": latency}
