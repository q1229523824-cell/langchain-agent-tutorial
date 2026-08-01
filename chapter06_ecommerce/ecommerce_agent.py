"""Day 14 电商客服 Agent 的演示、评测、CLI 和 API 启动入口。"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from chapter06_ecommerce.evaluation import run_offline_evaluation
from chapter06_ecommerce.workflow import EcommerceAgentRuntime


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIRECTORY = PROJECT_ROOT / ".agent_data" / "day14"


def _pretty(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def run_demo() -> None:
    """运行完全离线的端到端电商场景，不调用 DeepSeek。"""

    with tempfile.TemporaryDirectory() as directory:
        runtime = EcommerceAgentRuntime.create(
            data_directory=Path(directory),
            use_llm=False,
            rate_limit=100,
        )
        scenarios = (
            "预算500元，推荐适合通勤的降噪耳机",
            "满多少金额可以包邮？",
            "查询订单 order-1001",
            "order-1001 能不能退款？",
            "我要退款 order-1001",
        )
        prepared: dict[str, object] | None = None
        for index, question in enumerate(scenarios, start=1):
            print(f"\n[{index}] 用户> {question}")
            result = runtime.chat(
                user_id="demo-user",
                thread_id="portfolio-demo",
                message=question,
            )
            print(f"路由> {result['route']}")
            print(f"客服> {result['answer']}")
            if result["business_result"].get("confirmation_id"):
                prepared = result["business_result"]

        if prepared is None:
            raise RuntimeError("演示流程没有生成退款确认记录。")
        confirmation_id = str(prepared["confirmation_id"])
        print("\n[6] 用户通过确定性接口确认本地模拟退款")
        first = runtime.confirm_refund(
            user_id="demo-user",
            confirmation_id=confirmation_id,
        )
        print(_pretty(first))

        print("\n[7] 重复确认复用第一次结果")
        print(
            _pretty(
                runtime.confirm_refund(
                    user_id="demo-user",
                    confirmation_id=confirmation_id,
                )
            )
        )
        print("\n[8] 可观测指标")
        print(_pretty(runtime.trace_store.metrics()))


def run_cli(runtime: EcommerceAgentRuntime, *, user_id: str, thread_id: str) -> None:
    print(
        "Day 14 星河商城客服 Agent 已启动。\n"
        "命令：/orders  /confirm <confirmation_id>  /status <refund_id>  "
        "/metrics  /quit"
    )
    while True:
        try:
            user_input = input(f"\n[{thread_id}] 你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return
        if not user_input:
            continue
        if user_input in {"/quit", "/exit"}:
            print("已退出。")
            return
        if user_input == "/orders":
            print(_pretty(runtime.list_orders(user_id=user_id)))
            continue
        if user_input == "/metrics":
            print(_pretty(runtime.trace_store.metrics()))
            continue
        if user_input.startswith("/confirm "):
            print(
                _pretty(
                    runtime.confirm_refund(
                        user_id=user_id,
                        confirmation_id=user_input.removeprefix("/confirm ").strip(),
                    )
                )
            )
            continue
        if user_input.startswith("/status "):
            print(
                _pretty(
                    runtime.refund_status(
                        user_id=user_id,
                        refund_id=user_input.removeprefix("/status ").strip(),
                    )
                )
            )
            continue
        try:
            result = runtime.chat(user_id=user_id, thread_id=thread_id, message=user_input)
            print(f"[{result['route']}]\n客服> {result['answer']}")
        except Exception as error:
            print(f"[运行失败] {type(error).__name__}: {error}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Day 14 星河商城电商客服 Agent")
    parser.add_argument("--demo", action="store_true", help="运行完全离线的端到端演示")
    parser.add_argument("--eval", action="store_true", help="运行离线路由和检索评测")
    parser.add_argument("--api", action="store_true", help="启动 FastAPI 服务")
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="允许把当前问题、最近消息和必要证据发送给 DeepSeek 润色答案",
    )
    parser.add_argument("--user", default="demo-user")
    parser.add_argument("--thread", default="day14-demo")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIRECTORY)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    runtime = EcommerceAgentRuntime.create(
        data_directory=args.data_dir,
        use_llm=args.use_llm,
        rate_limit=100 if args.eval else 30,
    )
    if args.eval:
        print(_pretty(run_offline_evaluation(runtime)))
        return
    if args.api:
        import uvicorn

        from chapter06_ecommerce.api import create_app

        uvicorn.run(
            create_app(runtime),
            host=args.host,
            port=args.port,
        )
        return
    run_cli(runtime, user_id=args.user, thread_id=args.thread)


if __name__ == "__main__":
    main()
