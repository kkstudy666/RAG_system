"""
RAG 知识库系统 —— 对话接口
============================
流式问答（SSE）+ 对话历史查询。
"""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, KnowledgeBase
from app.schemas import ChatRequest, ChatHistoryResponse, ChatMessage
from app.core.deps import get_current_user
from app.services.chat_service import run_rag_stream

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: dict) -> str:
    """将事件字典编码为 SSE 的 data 帧"""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/stream")
def chat_stream(
    data: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """流式问答：返回 SSE 流（text/event-stream）"""
    kb = db.get(KnowledgeBase, data.kb_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    if not kb.is_public and kb.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="该知识库为私有，无权访问"
        )

    history = [{"role": m.role, "content": m.content} for m in data.history]
    config = data.config or {}

    generator = run_rag_stream(
        db, user.id, kb, data.question, history, config
    )

    return StreamingResponse(
        (_sse(ev) for ev in generator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", response_model=ChatHistoryResponse)
def get_history(
    kb_id: int,
    user: User = Depends(get_current_user),
):
    """对话历史由前端 localStorage 缓存，此接口返回空壳以保证契约一致"""
    return ChatHistoryResponse(kb_id=kb_id, messages=[])
