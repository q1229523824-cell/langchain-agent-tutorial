from fastapi import APIRouter, Depends

from app.api.dependencies import authenticated_user, get_runtime
from app.core.errors import require_business_success
from app.schemas.common import ERROR_RESPONSES
from app.services.runtime import EcommerceAgentRuntime


router = APIRouter(tags=["orders"])


@router.get("/orders", responses=ERROR_RESPONSES, summary="列出当前用户订单")
def list_orders(
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return runtime.list_orders(user_id=user_id)


@router.get(
    "/orders/{order_id}",
    responses=ERROR_RESPONSES,
    summary="查询当前用户单个订单",
)
def get_order(
    order_id: str,
    user_id: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
):
    return require_business_success(
        runtime.get_order(user_id=user_id, order_id=order_id),
        not_found_message="订单不存在或无权访问。",
    )
