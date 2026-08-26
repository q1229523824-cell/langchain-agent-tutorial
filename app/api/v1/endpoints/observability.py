from fastapi import APIRouter, Depends, Query

from app.api.dependencies import authenticated_user, get_runtime
from app.schemas.common import ERROR_RESPONSES
from app.services.runtime import EcommerceAgentRuntime


router = APIRouter(tags=["observability"])


@router.get("/metrics", responses=ERROR_RESPONSES, summary="读取聚合运行指标")
def metrics(
    _: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return runtime.trace_store.metrics()


@router.get("/traces", responses=ERROR_RESPONSES, summary="读取最近Agent Trace元数据")
def traces(
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return {"traces": runtime.trace_store.recent_for_user(user_id, limit)}
