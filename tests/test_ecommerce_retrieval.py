import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chapter06_ecommerce.catalog_service import CatalogService, extract_budget_cents  # noqa: E402
from chapter06_ecommerce.hybrid_retriever import (  # noqa: E402
    HybridCommerceRetriever,
    LocalHashVectorEncoder,
)
from chapter06_ecommerce.workflow import KNOWLEDGE_ROOT  # noqa: E402


class EcommerceRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = HybridCommerceRetriever.from_directory(KNOWLEDGE_ROOT)

    def test_refund_question_ranks_refund_policy_first(self):
        hits = self.retriever.search("未发货订单怎么退钱", top_k=3)
        self.assertIn("refund_policy.md", hits[0].citation)

    def test_shipping_synonym_ranks_shipping_policy_first(self):
        hits = self.retriever.search("快递什么时候到", top_k=3)
        self.assertIn("shipping_policy.md", hits[0].citation)

    def test_product_warranty_ranks_product_document_first(self):
        hits = self.retriever.search("数码商品坏了保修多久", top_k=3)
        self.assertIn("product_and_invoice.md", hits[0].citation)

    def test_result_exposes_retrieval_scores_and_citation(self):
        payload = self.retriever.search("满多少包邮", top_k=1)[0].as_payload()
        for field in (
            "citation",
            "bm25_score",
            "vector_score",
            "fusion_score",
            "rerank_score",
        ):
            self.assertIn(field, payload)

    def test_top_k_is_bounded(self):
        with self.assertRaises(ValueError):
            self.retriever.search("退款", top_k=6)

    def test_local_encoder_is_deterministic_and_normalized(self):
        encoder = LocalHashVectorEncoder(dimensions=128)
        first = encoder.encode("快递什么时候到")
        second = encoder.encode("快递什么时候到")

        self.assertEqual(first, second)
        self.assertAlmostEqual(sum(value * value for value in first), 1.0)

    def test_budget_parser_supports_common_chinese_expressions(self):
        self.assertEqual(extract_budget_cents("预算500元买耳机"), 50000)
        self.assertEqual(extract_budget_cents("300以内的键盘"), 30000)

    def test_catalog_respects_budget_and_stock(self):
        result = CatalogService().recommend("推荐通勤降噪耳机", max_price_cents=40000)

        self.assertTrue(result["products"])
        self.assertTrue(all(product["price_cents"] <= 40000 for product in result["products"]))
        self.assertTrue(all(product["stock"] > 0 for product in result["products"]))


if __name__ == "__main__":
    unittest.main()
