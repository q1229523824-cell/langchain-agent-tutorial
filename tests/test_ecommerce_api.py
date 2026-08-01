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

from chapter06_ecommerce.api import create_app  # noqa: E402
from chapter06_ecommerce.workflow import EcommerceAgentRuntime  # noqa: E402


class EcommerceApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        runtime = EcommerceAgentRuntime.create(
            data_directory=Path(self.temporary_directory.name),
            use_llm=False,
            rate_limit=100,
        )
        self.client = TestClient(create_app(runtime))
        self.headers = {"X-Demo-Token": "demo-user-token"}

    def test_health_does_not_require_authentication(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_business_endpoints_require_demo_authentication(self):
        response = self.client.get("/v1/orders")
        self.assertEqual(response.status_code, 401)

    def test_chat_returns_route_answer_and_citations(self):
        response = self.client.post(
            "/v1/chat",
            headers=self.headers,
            json={"thread_id": "api-test", "message": "满多少金额可以包邮？"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["intent"], "policy")
        self.assertIn("九十九元", payload["answer"])
        self.assertTrue(payload["citations"])

    def test_request_schema_rejects_user_id_from_body(self):
        response = self.client.post(
            "/v1/chat",
            headers=self.headers,
            json={
                "thread_id": "api-test",
                "message": "查询订单 order-2001",
                "user_id": "other-user",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_refund_requires_separate_confirmation_endpoint(self):
        prepared_response = self.client.post(
            "/v1/chat",
            headers=self.headers,
            json={"thread_id": "refund", "message": "我要退款 order-1001"},
        )
        prepared = prepared_response.json()["business_result"]
        self.assertEqual(prepared["status"], "pending_confirmation")

        confirmed_response = self.client.post(
            f"/v1/refunds/{prepared['confirmation_id']}/confirm",
            headers=self.headers,
        )
        self.assertEqual(confirmed_response.status_code, 200)
        self.assertEqual(confirmed_response.json()["status"], "succeeded")

    def test_other_user_cannot_confirm_confirmation(self):
        prepared = self.client.post(
            "/v1/chat",
            headers=self.headers,
            json={"thread_id": "refund", "message": "我要退款 order-1001"},
        ).json()["business_result"]

        response = self.client.post(
            f"/v1/refunds/{prepared['confirmation_id']}/confirm",
            headers={"X-Demo-Token": "other-user-token"},
        )
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.json()["status"], "not_found")

    def test_metrics_expose_aggregates_without_raw_messages(self):
        self.client.post(
            "/v1/chat",
            headers=self.headers,
            json={"thread_id": "metric", "message": "推荐耳机"},
        )

        response = self.client.get("/v1/metrics", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["request_count"], 1)
        self.assertNotIn("message", response.text)


if __name__ == "__main__":
    unittest.main()
