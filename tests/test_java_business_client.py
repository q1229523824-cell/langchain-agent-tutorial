import json
import sys
import unittest
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.java_tools import build_java_business_tools  # noqa: E402
from app.services.java_business_client import JavaBusinessClient  # noqa: E402


class JavaBusinessClientTests(unittest.TestCase):
    def setUp(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/orders/order-1001":
                return httpx.Response(200, json={"orderId": "order-1001", "status": "PENDING_SHIPMENT"})
            if request.url.path == "/api/refunds/preview":
                return httpx.Response(200, json={"refundId": "refund-1", "status": "PREPARED"})
            return httpx.Response(404, json={"error": "not found"})

        self.transport = httpx.MockTransport(handler)
        self.http_client = httpx.Client(transport=self.transport)
        self.client = JavaBusinessClient(
            "http://business-service", user_id="demo-user", request_id="req-test", client=self.http_client
        )
        self.addCleanup(self.http_client.close)

    def test_client_transmits_server_identity_and_request_id(self):
        result = self.client.query_order("order-1001")
        self.assertEqual(result["status"], "PENDING_SHIPMENT")

    def test_refund_payload_is_structured(self):
        result = self.client.preview_refund("order-1001", "idem-1")
        self.assertEqual(result["status"], "PREPARED")

    def test_tools_are_named_and_return_json(self):
        tools = build_java_business_tools(self.client)
        names = {tool.name for tool in tools}
        self.assertEqual(names, {"query_product", "query_order", "preview_refund", "confirm_refund"})
        self.assertEqual(json.loads(next(tool for tool in tools if tool.name == "query_order").invoke({"order_id": "order-1001"}))["status"], "PENDING_SHIPMENT")


if __name__ == "__main__":
    unittest.main()
