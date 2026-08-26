"""Python Agent 调用 Java Business Service 的最小 REST 适配器。"""

from __future__ import annotations

from typing import Any

import httpx


class BusinessServiceError(RuntimeError):
    """Java 服务返回业务错误或网络不可用。"""


class JavaBusinessClient:
    def __init__(
        self,
        base_url: str,
        *,
        user_id: str,
        request_id: str | None = None,
        timeout: float = 5.0,
        client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id
        self.request_id = request_id
        self.timeout = timeout
        self._client = client

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = dict(kwargs.pop("headers", {}))
        headers["X-User-Id"] = self.user_id
        if self.request_id:
            headers["X-Request-ID"] = self.request_id
        client = self._client or httpx.Client(timeout=self.timeout)
        close_after = self._client is None
        try:
            response = client.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
            try:
                body = response.json()
            except ValueError:
                body = {"message": response.text}
            if response.is_error:
                raise BusinessServiceError(f"Java业务服务返回HTTP {response.status_code}: {body}")
            if not isinstance(body, dict):
                raise BusinessServiceError("Java业务服务返回了非对象JSON。")
            return body
        except httpx.HTTPError as exc:
            raise BusinessServiceError(f"Java业务服务暂不可用: {exc}") from exc
        finally:
            if close_after:
                client.close()

    def query_product(self, sku: str) -> dict[str, Any]:
        return self._request("GET", f"/api/products/{sku}")

    def search_products(self, keyword: str = "") -> dict[str, Any]:
        return self._request("GET", "/api/products/search", params={"q": keyword})

    def query_order(self, order_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/orders/{order_id}")

    def preview_refund(self, order_id: str, idempotency_key: str) -> dict[str, Any]:
        return self._request(
            "POST", "/api/refunds/preview",
            json={"orderId": order_id, "idempotencyKey": idempotency_key},
        )

    def confirm_refund(self, refund_id: str, idempotency_key: str) -> dict[str, Any]:
        return self._request(
            "POST", f"/api/refunds/{refund_id}/confirm",
            json={"idempotencyKey": idempotency_key},
        )
