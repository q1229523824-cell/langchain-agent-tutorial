from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.api.dependencies import authenticated_user, get_runtime
from app.core.middleware import get_request_id
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
    ConversationListResponse,
)
from app.schemas.common import ERROR_RESPONSES
from app.services.runtime import EcommerceAgentRuntime


router = APIRouter(tags=["agent"])


def _sse(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def stream_sse_events(result: dict[str, object], chunk_size: int = 24) -> Iterator[str]:
    """将完整业务结果转换为SSE事件。

    当前工作流先完成确定性业务执行，再分块传输答案；这是SSE传输流，不冒充模型
    token流。未来替换成异步LangGraph/LLM stream时，前端事件协议无需改变。
    """

    answer = str(result["answer"])
    yield _sse(
        "metadata",
        {
            "request_id": result["request_id"],
            "thread_id": result["thread_id"],
            "intent": result["intent"],
            "route": result["route"],
            "citations": result["citations"],
        },
    )
    for start in range(0, len(answer), chunk_size):
        yield _sse("delta", {"content": answer[start : start + chunk_size]})
    yield _sse(
        "done",
        {
            "request_id": result["request_id"],
            "duration_ms": result["duration_ms"],
            "business_result": result["business_result"],
        },
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses=ERROR_RESPONSES,
    summary="执行一轮电商Agent对话",
)
def chat(
    payload: ChatRequest,
    request: Request,
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
) -> ChatResponse:
    result = runtime.chat(
        user_id=user_id,
        thread_id=payload.thread_id,
        message=payload.message,
        request_id=get_request_id(request),
    )
    return ChatResponse.model_validate(result)


@router.post(
    "/chat/stream",
    responses={
        200: {
            "description": "SSE事件：metadata、delta、done",
            "content": {"text/event-stream": {}},
        },
        **ERROR_RESPONSES,
    },
    summary="通过SSE分块返回Agent回答",
)
def stream_chat(
    payload: ChatRequest,
    request: Request,
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
) -> StreamingResponse:
    result = runtime.chat(
        user_id=user_id,
        thread_id=payload.thread_id,
        message=payload.message,
        request_id=get_request_id(request),
    )
    return StreamingResponse(
        stream_sse_events(result),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    responses=ERROR_RESPONSES,
    summary="列出当前用户的会话",
)
def list_conversations(
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
) -> ConversationListResponse:
    return ConversationListResponse.model_validate(
        runtime.list_conversations(user_id=user_id)
    )


@router.get(
    "/conversations/{thread_id}/messages",
    response_model=ConversationHistoryResponse,
    responses=ERROR_RESPONSES,
    summary="读取当前用户指定会话的消息",
)
def conversation_history(
    thread_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
) -> ConversationHistoryResponse:
    return ConversationHistoryResponse.model_validate(
        runtime.conversation_history(
            user_id=user_id,
            thread_id=thread_id,
            limit=limit,
        )
    )
