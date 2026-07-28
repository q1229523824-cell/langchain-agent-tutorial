"""把退款业务服务包装成 LangChain 工具。

工具通过闭包取得服务端认证后的 user_id，因此 user_id 不会出现在模型可填写的
tool schema 中。大模型只能提出业务参数，不能伪造当前登录身份。
"""

from __future__ import annotations

import json
from typing import Any

from langchain.tools import tool

from chapter05_refund.refund_service import RefundService


def _tool_json(result: dict[str, object]) -> str:
    return json.dumps(result, ensure_ascii=False, sort_keys=True)


def build_refund_tools(
    service: RefundService,
    *,
    current_user_id: str,
) -> list[Any]:
    """为一个已经认证的用户创建只读/准备型退款工具。"""

    current_user_id = current_user_id.strip()
    if not current_user_id:
        raise ValueError("current_user_id 不能为空。")

    @tool("list_my_orders")
    def list_my_orders() -> str:
        """列出当前已认证用户自己的演示订单。不要要求或接受 user_id。"""

        return _tool_json(service.list_orders(current_user_id))

    @tool("get_my_order")
    def get_my_order(order_id: str) -> str:
        """查询当前用户一个订单的实时状态。只能读取属于当前用户的订单。"""

        return _tool_json(service.get_order(current_user_id, order_id))

    @tool("check_refund_eligibility")
    def check_refund_eligibility(order_id: str) -> str:
        """确定性检查当前用户订单是否符合本地自动退款规则，不执行退款。"""

        return _tool_json(service.check_eligibility(current_user_id, order_id))

    @tool("prepare_refund")
    def prepare_refund(order_id: str) -> str:
        """生成绑定订单、金额和过期时间的待确认记录，但绝不直接执行退款。"""

        return _tool_json(service.prepare_refund(current_user_id, order_id))

    @tool("query_refund_status")
    def query_refund_status(refund_id: str) -> str:
        """从业务数据库查询当前用户退款的最新权威状态，不依赖聊天记忆。"""

        return _tool_json(service.get_refund_status(current_user_id, refund_id))

    return [
        list_my_orders,
        get_my_order,
        check_refund_eligibility,
        prepare_refund,
        query_refund_status,
    ]
