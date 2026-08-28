"""星河商城现场演示：本地 TestClient，不调用 DeepSeek、不连接真实支付。"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import AppSettings
from app.main import create_app
from chapter06_ecommerce.workflow import EcommerceAgentRuntime


def pretty(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="xinghe-live-demo-") as directory:
        data_directory = Path(directory)
        runtime = EcommerceAgentRuntime.create(
            data_directory=data_directory, use_llm=False, rate_limit=100
        )
        app = create_app(
            runtime,
            settings=AppSettings(data_directory=data_directory, rate_limit=100),
        )
        with TestClient(app) as client:
            print("=== 1. JWT 登录 ===")
            login = client.post(
                "/api/v1/auth/login",
                json={"user_id": "demo-user", "password": "demo-password"},
            )
            login.raise_for_status()
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}", "X-Request-ID": "live-demo-001"}
            pretty({"user": client.get("/api/v1/auth/me", headers=headers).json()})

            print("\n=== 2. Agent 聊天 ===")
            chat = client.post(
                "/api/v1/chat",
                headers=headers,
                json={"thread_id": "live-demo", "message": "满多少金额可以包邮？"},
            )
            chat.raise_for_status()
            pretty({"request_id": chat.json()["request_id"], "answer": chat.json()["answer"]})

            print("\n=== 3. 退款预览（不执行资金动作） ===")
            prepared = client.post(
                "/api/v1/refunds/prepare",
                headers=headers,
                json={"order_id": "order-1001"},
            )
            prepared.raise_for_status()
            pretty(prepared.json())

            print("\n=== 4. 用户确认后执行一次 ===")
            confirmation_id = prepared.json()["confirmation_id"]
            confirmed = client.post(
                f"/api/v1/refunds/{confirmation_id}/confirm",
                headers=headers,
            )
            confirmed.raise_for_status()
            pretty(confirmed.json())

            print("\n=== 5. 重复确认复用幂等结果 ===")
            repeated = client.post(
                f"/api/v1/refunds/{confirmation_id}/confirm",
                headers=headers,
            )
            repeated.raise_for_status()
            pretty({"same_refund_id": repeated.json()["refund_id"] == confirmed.json()["refund_id"]})


if __name__ == "__main__":
    main()
