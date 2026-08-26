from fastapi import APIRouter, Depends, Query

from app.api.dependencies import authenticated_user, get_runtime
from app.core.errors import require_business_success
from app.schemas.commerce import ProductDetailResponse, ProductListResponse
from app.schemas.common import ERROR_RESPONSES
from app.services.runtime import EcommerceAgentRuntime


router = APIRouter(tags=["catalog"])


@router.get(
    "/products",
    response_model=ProductListResponse,
    responses=ERROR_RESPONSES,
    summary="查询商品目录",
)
def list_products(
    category: str | None = Query(default=None, max_length=40),
    in_stock_only: bool = False,
    _: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
) -> ProductListResponse:
    return ProductListResponse.model_validate(
        runtime.list_products(category=category, in_stock_only=in_stock_only)
    )


@router.get(
    "/products/{sku}",
    response_model=ProductDetailResponse,
    responses=ERROR_RESPONSES,
    summary="查询单个商品实时事实",
)
def get_product(
    sku: str,
    _: str = Depends(authenticated_user),
    runtime: EcommerceAgentRuntime = Depends(get_runtime),
) -> ProductDetailResponse:
    result = require_business_success(
        runtime.get_product(sku=sku),
        not_found_message="商品不存在。",
    )
    return ProductDetailResponse.model_validate(result)
