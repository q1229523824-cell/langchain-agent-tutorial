from fastapi import APIRouter, Depends, Request

from app.api.dependencies import authenticated_user, get_runtime
from app.core.errors import require_business_success
from app.core.middleware import get_request_id
from app.schemas.commerce import RefundPrepareRequest
from app.schemas.common import ERROR_RESPONSES
from app.services.runtime import EcommerceAgentRuntime


router = APIRouter(tags=["refunds"])


@router.get("/refunds", responses=ERROR_RESPONSES, summary="列出当前用户退款记录")
def list_refunds(
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return runtime.list_refunds(user_id=user_id)


@router.post(
    "/refunds/prepare",
    responses=ERROR_RESPONSES,
    summary="创建退款待确认记录，不执行退款",
)
def prepare_refund(
    payload: RefundPrepareRequest,
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return require_business_success(
        runtime.prepare_refund(user_id=user_id, order_id=payload.order_id),
        not_found_message="订单不存在或无权访问。",
    )


@router.post(
    "/refunds/{confirmation_id}/confirm",
    responses=ERROR_RESPONSES,
    summary="通过独立确定性接口确认本地模拟退款",
)
def confirm_refund(
    confirmation_id: str,
    request: Request,
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return require_business_success(
        runtime.confirm_refund(
            user_id=user_id,
            confirmation_id=confirmation_id,
            request_id=get_request_id(request),
        ),
        not_found_message="确认记录不存在或无权访问。",
    )


@router.get(
    "/refunds/{refund_id}",
    responses=ERROR_RESPONSES,
    summary="查询当前用户退款状态",
)
def refund_status(
    refund_id: str,
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return require_business_success(
        runtime.refund_status(user_id=user_id, refund_id=refund_id),
        not_found_message="退款记录不存在或无权访问。",
    )


@router.get(
    "/refunds/{refund_id}/events",
    responses=ERROR_RESPONSES,
    summary="查询退款状态转换审计事件",
)
def refund_events(
    refund_id: str,
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    result = runtime.refund_events(user_id=user_id, refund_id=refund_id)
    if result["count"] == 0:
        # 不区分不存在和属于其他用户，避免资源枚举。
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="退款记录不存在或无权访问。")
    return result
