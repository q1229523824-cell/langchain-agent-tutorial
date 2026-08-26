from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProductResponse(BaseModel):
    sku: str
    name: str
    category: str
    price_cents: int
    stock: int
    features: list[str]
    price: str
    in_stock: bool


class ProductListResponse(BaseModel):
    ok: bool
    status: str
    count: int
    products: list[ProductResponse]


class ProductDetailResponse(BaseModel):
    ok: bool
    status: str
    product: ProductResponse


class RefundPrepareRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"order_id": "order-1001"}]},
    )

    order_id: str = Field(pattern=r"^order-\d+$", max_length=80)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    api_prefix: str
    llm_enabled: bool
