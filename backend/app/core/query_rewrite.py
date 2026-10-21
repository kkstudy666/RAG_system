"""
RAG 知识库系统 —— 查询改写（Query Rewrite）
=============================================
使用 LLM 将用户多轮模糊提问改写为独立、精准的检索语句，
补全指代（"它""这个"等），提升向量检索的召回准确率。
"""
from typing import List, Dict, Any

from app.core.llm import get_llm
from app.core.prompts import QUERY_REWRITE_PROMPT


def rewrite_query(
    question: str,
    history: List[Dict[str, str]],
    llm_config: Dict[str, Any],
) -> str:
    """
    改写查询语句。

    Args:
        question: 当前用户提问
        history: 对话历史 [{role, content}, ...]
        llm_config: LLM 配置字典

    Returns:
        改写后的检索语句；LLM 不可用或改写失败时返回原问题
    """
    try:
        llm = get_llm(llm_config)
        # 仅取最近几轮历史，避免上下文过长
        history_text = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-6:]
        ) or "（无历史对话）"

        prompt = QUERY_REWRITE_PROMPT.format(history=history_text, question=question)
        result = llm.invoke(prompt)
        # Ollama 的 invoke 返回 str，ChatOpenAI 返回 AIMessage
        text = getattr(result, "content", None) or str(result)
        text = text.strip().strip('"').strip("'")

        return text if text else question
    except Exception as e:  # noqa: BLE001 LLM 不可用时降级
        print(f"[query_rewrite] 改写失败，使用原始问题: {e}")
        return question
