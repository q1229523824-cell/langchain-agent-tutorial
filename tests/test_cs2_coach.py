import io
import json
import unittest

from fastapi.testclient import TestClient
from pydantic import ValidationError

from chapter07_cs2_coach.api import create_app
from chapter07_cs2_coach.models import MatchRecord
from chapter07_cs2_coach.runtime import CS2CoachRuntime
from chapter07_cs2_coach.sample_data import SAMPLE_MATCH
from chapter07_cs2_coach.tools import get_match_summary


class CS2CoachToolTests(unittest.TestCase):
    def test_summary_is_calculated_from_round_facts(self):
        summary = get_match_summary(SAMPLE_MATCH)

        self.assertEqual(summary["score"], "10:12")
        self.assertEqual(summary["kills"], 24)
        self.assertEqual(summary["deaths"], 12)
        self.assertEqual(summary["adr"], 102.6)

    def test_match_rejects_score_inconsistent_with_rounds(self):
        payload = SAMPLE_MATCH.model_dump()
        payload["team_score"] = 11

        with self.assertRaises(ValidationError):
            MatchRecord.model_validate(payload)


class CS2CoachWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.runtime = CS2CoachRuntime.create()

    def test_question_dynamically_selects_clutch_tool(self):
        result = self.runtime.analyze(
            match_id=SAMPLE_MATCH.match_id,
            question="为什么我杀了很多人还是输了？",
        )

        self.assertEqual(result.tools_used, ["clutches"])
        self.assertEqual(result.evidence[0].round_numbers, [9, 14, 19])
        self.assertIn("R9、R14、R19", result.answer)

    def test_comprehensive_review_runs_bounded_tool_loop(self):
        result = self.runtime.analyze(
            match_id=SAMPLE_MATCH.match_id,
            question="请综合复盘并找出最需要改进的问题",
        )

        self.assertEqual(len(result.tools_used), 5)
        self.assertLessEqual(len(result.tools_used), 5)
        self.assertTrue(any(item.severity == "high" for item in result.evidence))
        self.assertEqual(result.confidence, "high")
        self.assertTrue(result.execution_trace[-1].startswith("reporter:"))

    def test_unknown_match_is_rejected(self):
        with self.assertRaises(KeyError):
            self.runtime.analyze(match_id="missing", question="复盘")


class CS2CoachApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(CS2CoachRuntime.create()))

    def test_homepage_and_health(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/health").json()["status"], "ok")

    def test_analyze_endpoint(self):
        response = self.client.post(
            "/api/analyze",
            json={
                "match_id": SAMPLE_MATCH.match_id,
                "question": "分析我的首杀和补枪问题",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["tools_used"], ["opening_duels", "tradeability"])
        self.assertGreaterEqual(len(body["evidence"]), 1)

    def test_upload_json_rejects_wrong_extension(self):
        response = self.client.post(
            "/api/upload-json",
            files={"file": ("match.txt", io.BytesIO(b"{}"), "text/plain")},
        )

        self.assertEqual(response.status_code, 400)

    def test_upload_json_accepts_valid_match(self):
        payload = SAMPLE_MATCH.model_copy(update={"match_id": "uploaded-demo"}).model_dump()
        response = self.client.post(
            "/api/upload-json",
            files={
                "file": (
                    "match.json",
                    io.BytesIO(json.dumps(payload, ensure_ascii=False).encode("utf-8")),
                    "application/json",
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["match_id"], "uploaded-demo")


if __name__ == "__main__":
    unittest.main()
