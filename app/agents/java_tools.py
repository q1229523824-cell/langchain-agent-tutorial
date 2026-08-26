"""将 Java 业务 REST API 暴露成 Agent 可使用的安全工具。"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool

from app.services.java_business_client import JavaBusinessClient


def build_java_business_tools(client: JavaBusinessClient) -> list[StructuredTool]:
    """返回四个最小权限工具；确认退款仍建议由独立按钮/接口触发。"""

    def query_product(sku: str) -> str:
        return json.dumps(client.query_product(sku), ensure_ascii=False)

    def query_order(order_id: str) -> str:
        return json.dumps(client.query_order(order_id), ensure_ascii=False)

    def preview_refund(order_id: str, idempotency_key: str) -> str:
        return json.dumps(client.preview_refund(order_id, idempotency_key), ensure_ascii=False)

    def confirm_refund(refund_id: str, idempotency_key: str) -> str:
        return json.dumps(client.confirm_refund(refund_id, idempotency_key), ensure_ascii=False)

    return [
        StructuredTool.from_function(query_product, name="query_product", description="查询商品事实"),
        StructuredTool.from_function(query_order, name="query_order", description="查询当前用户订单"),
        StructuredTool.from_function(preview_refund, name="preview_refund", description="创建退款待确认记录，不执行退款"),
        StructuredTool.from_function(confirm_refund, name="confirm_refund", description="确认已获用户授权的退款"),
    ]
