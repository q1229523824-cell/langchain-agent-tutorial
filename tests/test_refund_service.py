import json
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chapter05_refund.refund_service import (  # noqa: E402
    RefundService,
    RefundStatus,
    SimulatedRefundProvider,
)
from chapter05_refund.refund_tools import build_refund_tools  # noqa: E402


class RefundServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.provider = SimulatedRefundProvider()
        self.service = RefundService(
            Path(self.temporary_directory.name) / "refund.db",
            provider=self.provider,
        )
        self.service.seed_demo_orders()

    def test_lists_only_authenticated_users_orders(self):
        result = self.service.list_orders("demo-user")

        order_ids = {order["order_id"] for order in result["orders"]}
        self.assertEqual(order_ids, {"order-1001", "order-1002"})
        self.assertNotIn("order-2001", order_ids)

    def test_other_users_order_is_not_disclosed(self):
        result = self.service.get_order("demo-user", "order-2001")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "not_found")
        self.assertNotIn("other-user", json.dumps(result))

    def test_unshipped_order_is_eligible(self):
        result = self.service.check_eligibility("demo-user", "order-1001")

        self.assertTrue(result["eligible"])
        self.assertEqual(result["amount_cents"], 19900)

    def test_shipped_order_requires_manual_flow(self):
        result = self.service.check_eligibility("demo-user", "order-1002")

        self.assertFalse(result["eligible"])
        self.assertIn("人工退货", result["reason"])

    def test_prepare_refund_creates_bound_confirmation(self):
        result = self.service.prepare_refund("demo-user", "order-1001")

        self.assertEqual(result["status"], "pending_confirmation")
        self.assertEqual(result["order_id"], "order-1001")
        self.assertEqual(result["amount_cents"], 19900)
        self.assertTrue(result["next_action"].startswith("/confirm confirm_"))

    def test_repeated_prepare_reuses_pending_confirmation(self):
        first = self.service.prepare_refund("demo-user", "order-1001")
        second = self.service.prepare_refund("demo-user", "order-1001")

        self.assertEqual(first["confirmation_id"], second["confirmation_id"])

    def test_expired_confirmation_cannot_execute(self):
        start = datetime(2026, 7, 28, tzinfo=timezone.utc)
        prepared = self.service.prepare_refund(
            "demo-user",
            "order-1001",
            now=start,
        )

        result = self.service.confirm_and_execute(
            "demo-user",
            str(prepared["confirmation_id"]),
            now=start + timedelta(minutes=11),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "expired")
        self.assertEqual(self.provider.call_count, 0)

    def test_cancelled_confirmation_cannot_execute(self):
        prepared = self.service.prepare_refund("demo-user", "order-1001")
        confirmation_id = str(prepared["confirmation_id"])
        cancelled = self.service.cancel_confirmation("demo-user", confirmation_id)

        result = self.service.confirm_and_execute("demo-user", confirmation_id)

        self.assertEqual(cancelled["status"], "cancelled")
        self.assertFalse(result["ok"])
        self.assertEqual(self.provider.call_count, 0)

    def test_confirm_executes_once_and_updates_order(self):
        prepared = self.service.prepare_refund("demo-user", "order-1001")

        result = self.service.confirm_and_execute(
            "demo-user",
            str(prepared["confirmation_id"]),
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(self.provider.call_count, 1)
        order = self.service.get_order("demo-user", "order-1001")
        self.assertEqual(order["order"]["status"], "refunded")

    def test_repeated_confirmation_is_idempotent(self):
        prepared = self.service.prepare_refund("demo-user", "order-1001")
        confirmation_id = str(prepared["confirmation_id"])

        first = self.service.confirm_and_execute("demo-user", confirmation_id)
        second = self.service.confirm_and_execute("demo-user", confirmation_id)

        self.assertEqual(first["refund_id"], second["refund_id"])
        self.assertTrue(second["reused"])
        self.assertEqual(self.provider.call_count, 1)

    def test_concurrent_confirmation_calls_provider_once(self):
        prepared = self.service.prepare_refund("demo-user", "order-1001")
        confirmation_id = str(prepared["confirmation_id"])
        results: list[dict[str, object]] = []

        def execute() -> None:
            results.append(
                self.service.confirm_and_execute("demo-user", confirmation_id)
            )

        threads = [threading.Thread(target=execute) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(len(results), 2)
        self.assertEqual({result["refund_id"] for result in results}, {results[0]["refund_id"]})
        self.assertEqual(self.provider.call_count, 1)

    def test_processing_provider_does_not_claim_success(self):
        provider = SimulatedRefundProvider(mode=RefundStatus.PROCESSING)
        service = RefundService(
            Path(self.temporary_directory.name) / "processing.db",
            provider=provider,
        )
        service.seed_demo_orders()
        prepared = service.prepare_refund("demo-user", "order-1001")

        result = service.confirm_and_execute(
            "demo-user",
            str(prepared["confirmation_id"]),
        )

        self.assertEqual(result["status"], "processing")
        self.assertEqual(
            service.get_order("demo-user", "order-1001")["order"]["status"],
            "unshipped",
        )

    def test_failed_provider_preserves_failure_details(self):
        provider = SimulatedRefundProvider(mode=RefundStatus.FAILED)
        service = RefundService(
            Path(self.temporary_directory.name) / "failed.db",
            provider=provider,
        )
        service.seed_demo_orders()
        prepared = service.prepare_refund("demo-user", "order-1001")

        result = service.confirm_and_execute(
            "demo-user",
            str(prepared["confirmation_id"]),
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "SIMULATED_PROVIDER_REJECTED")
        self.assertFalse(result["retryable"])

    def test_refund_events_record_state_transitions(self):
        prepared = self.service.prepare_refund("demo-user", "order-1001")
        result = self.service.confirm_and_execute(
            "demo-user",
            str(prepared["confirmation_id"]),
        )

        events = self.service.list_refund_events(
            "demo-user",
            str(result["refund_id"]),
        )

        self.assertEqual(
            [event["to_status"] for event in events],
            ["processing", "succeeded"],
        )

    def test_refund_tools_hide_user_id_from_model_schema(self):
        tools = build_refund_tools(self.service, current_user_id="demo-user")

        for refund_tool in tools:
            properties = refund_tool.args_schema.model_json_schema().get("properties", {})
            self.assertNotIn("user_id", properties)

        list_tool = next(tool for tool in tools if tool.name == "list_my_orders")
        result = json.loads(list_tool.invoke({}))
        self.assertEqual(
            {order["order_id"] for order in result["orders"]},
            {"order-1001", "order-1002"},
        )


if __name__ == "__main__":
    unittest.main()
