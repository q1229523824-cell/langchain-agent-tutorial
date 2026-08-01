"""确定性的本地商品目录服务。

大模型可以理解用户需求，但价格、库存和 SKU 必须来自业务服务，不能由模型编造。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    category: str
    price_cents: int
    stock: int
    features: tuple[str, ...]

    def as_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["price"] = f"{self.price_cents / 100:.2f}"
        payload["in_stock"] = self.stock > 0
        payload["features"] = list(self.features)
        return payload


DEMO_PRODUCTS = (
    Product(
        sku="sku-headphone-pro",
        name="降噪蓝牙耳机 Pro",
        category="数码音频",
        price_cents=39900,
        stock=23,
        features=("主动降噪", "蓝牙5.3", "续航40小时", "通勤"),
    ),
    Product(
        sku="sku-headphone-lite",
        name="轻量蓝牙耳机 Lite",
        category="数码音频",
        price_cents=19900,
        stock=51,
        features=("轻量", "蓝牙5.3", "续航24小时", "运动"),
    ),
    Product(
        sku="sku-keyboard-k87",
        name="机械键盘 K87",
        category="电脑外设",
        price_cents=29900,
        stock=16,
        features=("87键", "热插拔", "RGB", "办公"),
    ),
    Product(
        sku="sku-coffee-cup",
        name="智能恒温咖啡杯",
        category="生活电器",
        price_cents=25900,
        stock=0,
        features=("恒温", "无线充电", "陶瓷内胆"),
    ),
)


def extract_budget_cents(text: str) -> int | None:
    """从“预算500元”“500以内”等常见中文表达中提取预算。"""

    patterns = (
        r"预算\s*(\d+(?:\.\d+)?)\s*元?",
        r"(\d+(?:\.\d+)?)\s*元?\s*(?:以内|以下|之内)",
        r"不超过\s*(\d+(?:\.\d+)?)\s*元?",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(float(match.group(1)) * 100)
    return None


class CatalogService:
    """从服务端商品事实中查询和推荐，不让模型生成价格或库存。"""

    def __init__(self, products: tuple[Product, ...] = DEMO_PRODUCTS):
        self.products = products

    def get_product(self, sku: str) -> dict[str, object]:
        product = next((item for item in self.products if item.sku == sku), None)
        if product is None:
            return {"ok": False, "status": "not_found", "message": "商品不存在。"}
        return {"ok": True, "status": "succeeded", "product": product.as_payload()}

    def recommend(
        self,
        query: str,
        *,
        max_price_cents: int | None = None,
        limit: int = 3,
    ) -> dict[str, object]:
        if not 1 <= limit <= 5:
            raise ValueError("limit 必须位于 1 到 5 之间。")

        query_lower = query.lower()
        keyword_groups = {
            "耳机": ("耳机", "音频", "降噪", "蓝牙", "通勤", "运动"),
            "键盘": ("键盘", "外设", "办公", "游戏", "机械"),
            "咖啡": ("咖啡", "杯", "恒温", "生活"),
        }
        expanded: set[str] = set()
        for anchor, related in keyword_groups.items():
            if anchor in query_lower or any(word in query_lower for word in related):
                expanded.update(related)

        ranked: list[tuple[int, Product]] = []
        for product in self.products:
            if product.stock <= 0:
                continue
            if max_price_cents is not None and product.price_cents > max_price_cents:
                continue
            searchable = " ".join((product.name, product.category, *product.features)).lower()
            score = sum(2 if word in product.name else 1 for word in expanded if word in searchable)
            if score > 0:
                ranked.append((score, product))

        ranked.sort(key=lambda item: (-item[0], item[1].price_cents, item[1].sku))
        products = [product.as_payload() for _, product in ranked[:limit]]
        return {
            "ok": True,
            "status": "succeeded",
            "budget_cents": max_price_cents,
            "products": products,
            "message": "推荐结果来自本地商品目录的实时价格与库存。",
        }
