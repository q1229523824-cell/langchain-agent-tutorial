import json
import sys
import tempfile
import unittest
import warnings
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import AppSettings  # noqa: E402
from app.main import create_app  # noqa: E402
from chapter06_ecommerce.workflow import EcommerceAgentRuntime  # noqa: E402


class FormalApplicationApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        data_directory = Path(self.temporary_directory.name)
        runtime = EcommerceAgentRuntime.create(
            data_directory=data_directory,
            use_llm=False,
            rate_limit=200,
        )
        settings = AppSettings(
            data_directory=data_directory,
            rate_limit=200,
            cors_origins=("http://localhost:5173",),
        )
        self.client = TestClient(create_app(runtime, settings=settings))
        self.headers = {"X-Demo-Token": "demo-user-token"}

    def test_versioned_health_and_openapi_only_show_formal_routes(self):
        health = self.client.get("/api/v1/health")
        schema = self.client.get("/openapi.json").json()

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["version"], "2.0.0")
        self.assertIn("/api/v1/chat", schema["paths"])
        self.assertNotIn("/v1/chat", schema["paths"])

    def test_request_id_correlates_header_chat_and_trace(self):
        headers = {**self.headers, "X-Request-ID": "portfolio-request-1"}
        response = self.client.post(
            "/api/v1/chat",
            headers=headers,
            json={"thread_id": "request-id", "message": "推荐耳机"},
        )
        traces = self.client.get("/api/v1/traces", headers=self.headers).json()["traces"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "portfolio-request-1")
        self.assertEqual(response.json()["request_id"], "portfolio-request-1")
        self.assertEqual(traces[-1]["request_id"], "portfolio-request-1")

    def test_invalid_request_id_is_replaced(self):
        response = self.client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "invalid id with spaces"},
        )

        self.assertRegex(response.headers["X-Request-ID"], r"^req_[a-f0-9]{32}$")

    def test_auth_and_validation_use_unified_error_shape(self):
        unauthorized = self.client.get("/api/v1/orders")
        invalid = self.client.post(
            "/api/v1/chat",
            headers=self.headers,
            json={"thread_id": "contains spaces", "message": "你好"},
        )

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(unauthorized.json()["error"]["code"], "authentication_failed")
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json()["error"]["code"], "validation_error")
        self.assertEqual(invalid.json()["request_id"], invalid.headers["X-Request-ID"])

    def test_jwt_login_and_bearer_auth(self):
        login = self.client.post(
            "/api/v1/auth/login",
            json={"user_id": "demo-user", "password": "demo-password"},
        )
        self.assertEqual(login.status_code, 200)
        token = login.json()["access_token"]
        me = self.client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        chat = self.client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"thread_id": "jwt", "message": "推荐耳机"},
        )
        self.assertEqual(me.json()["user_id"], "demo-user")
        self.assertEqual(chat.status_code, 200)

    def test_jwt_rejects_wrong_password_and_tampering(self):
        wrong = self.client.post(
            "/api/v1/auth/login",
            json={"user_id": "demo-user", "password": "wrong"},
        )
        invalid = self.client.get(
            "/api/v1/orders", headers={"Authorization": "Bearer not-a-jwt"}
        )
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(invalid.status_code, 401)

    def test_cors_allows_configured_frontend_origin(self):
        response = self.client.options(
            "/api/v1/chat",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-demo-token,content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:5173",
        )
        self.assertIn("X-Request-ID", response.headers)

    def test_sse_stream_contains_metadata_delta_and_done(self):
        response = self.client.post(
            "/api/v1/chat/stream",
            headers=self.headers,
            json={"thread_id": "sse", "message": "满多少金额可以包邮？"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        self.assertIn("event: metadata", response.text)
        self.assertIn("event: delta", response.text)
        self.assertIn("九十九元", response.text)
        self.assertIn("event: done", response.text)

    def test_conversation_list_history_and_user_isolation(self):
        self.client.post(
            "/api/v1/chat",
            headers=self.headers,
            json={"thread_id": "history", "message": "你好"},
        )
        conversations = self.client.get(
            "/api/v1/conversations", headers=self.headers
        ).json()
        history = self.client.get(
            "/api/v1/conversations/history/messages", headers=self.headers
        ).json()
        other_history = self.client.get(
            "/api/v1/conversations/history/messages",
            headers={"X-Demo-Token": "other-user-token"},
        ).json()

        self.assertEqual(conversations["conversations"][0]["thread_id"], "history")
        self.assertEqual([item["role"] for item in history["messages"]], ["user", "assistant"])
        self.assertEqual(other_history["count"], 0)

    def test_trace_endpoint_only_returns_current_users_records(self):
        self.client.post(
            "/api/v1/chat",
            headers=self.headers,
            json={"thread_id": "first-user", "message": "推荐耳机"},
        )
        self.client.post(
            "/api/v1/chat",
            headers={"X-Demo-Token": "other-user-token"},
            json={"thread_id": "second-user", "message": "你好"},
        )

        first_traces = self.client.get(
            "/api/v1/traces", headers=self.headers
        ).json()["traces"]
        self.assertTrue(first_traces)
        self.assertEqual({item["user_id"] for item in first_traces}, {"demo-user"})

    def test_catalog_list_detail_and_not_found(self):
        products = self.client.get(
            "/api/v1/products?in_stock_only=true", headers=self.headers
        ).json()
        product = self.client.get(
            "/api/v1/products/sku-headphone-pro", headers=self.headers
        )
        missing = self.client.get(
            "/api/v1/products/sku-missing", headers=self.headers
        )

        self.assertTrue(all(item["in_stock"] for item in products["products"]))
        self.assertEqual(product.json()["product"]["price"], "399.00")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["error"]["code"], "resource_not_found")

    def test_order_detail_hides_other_users_order(self):
        own = self.client.get("/api/v1/orders/order-1001", headers=self.headers)
        other = self.client.get("/api/v1/orders/order-2001", headers=self.headers)

        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.json()["order"]["order_id"], "order-1001")
        self.assertEqual(other.status_code, 404)

    def test_complete_refund_api_and_audit_flow(self):
        prepared = self.client.post(
            "/api/v1/refunds/prepare",
            headers=self.headers,
            json={"order_id": "order-1001"},
        ).json()
        confirmed = self.client.post(
            f"/api/v1/refunds/{prepared['confirmation_id']}/confirm",
            headers=self.headers,
        ).json()
        refunds = self.client.get("/api/v1/refunds", headers=self.headers).json()
        status = self.client.get(
            f"/api/v1/refunds/{confirmed['refund_id']}", headers=self.headers
        ).json()
        events = self.client.get(
            f"/api/v1/refunds/{confirmed['refund_id']}/events", headers=self.headers
        ).json()

        self.assertEqual(prepared["status"], "pending_confirmation")
        self.assertEqual(confirmed["status"], "succeeded")
        self.assertEqual(refunds["refunds"][0]["refund_id"], confirmed["refund_id"])
        self.assertEqual(status["status"], "succeeded")
        self.assertEqual(
            [item["to_status"] for item in events["events"]],
            ["processing", "succeeded"],
        )

    def test_sse_payload_is_valid_json_per_data_line(self):
        response = self.client.post(
            "/api/v1/chat/stream",
            headers=self.headers,
            json={"thread_id": "json-sse", "message": "你好"},
        )

        data_lines = [line.removeprefix("data: ") for line in response.text.splitlines() if line.startswith("data: ")]
        self.assertTrue(data_lines)
        for data in data_lines:
            self.assertIsInstance(json.loads(data), dict)


if __name__ == "__main__":
    unittest.main()
