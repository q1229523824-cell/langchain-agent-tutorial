"""Day14旧 `/v1` 接口兼容层，不在OpenAPI中展示。"""

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import authenticated_user, get_runtime
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.runtime import EcommerceAgentRuntime


router = APIRouter(include_in_schema=False)


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return runtime.chat(
        user_id=user_id,
        thread_id=payload.thread_id,
        message=payload.message,
    )


@router.get("/orders")
def orders(
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return runtime.list_orders(user_id=user_id)


@router.post("/refunds/{confirmation_id}/confirm")
def confirm_refund(
    confirmation_id: str,
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return runtime.confirm_refund(user_id=user_id, confirmation_id=confirmation_id)


@router.get("/refunds/{refund_id}")
def refund_status(
    refund_id: str,
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return runtime.refund_status(user_id=user_id, refund_id=refund_id)


@router.get("/metrics")
def metrics(
    _: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return runtime.trace_store.metrics()


@router.get("/traces")
def traces(
    limit: int = Query(default=20, ge=1, le=100),
    _: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return {"traces": runtime.trace_store.recent(limit)}
