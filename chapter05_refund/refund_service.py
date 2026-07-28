"""本地模拟退款业务服务。

本模块不会连接真实支付渠道，也不会产生真实资金变化。它用 SQLite 演示高风险
Agent 工具必须具备的确定性业务边界：

    身份隔离 -> 资格校验 -> 待确认记录 -> 用户确认 -> 幂等执行 -> 状态查询

大模型不直接修改订单或退款状态。所有状态转换都由本模块的代码和数据库事务完成。
"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Iterator, Protocol


class OrderStatus(StrEnum):
    """本地演示订单的有限状态。"""

    UNSHIPPED = "unshipped"
    SHIPPED = "shipped"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class ConfirmationStatus(StrEnum):
    """退款确认记录的状态。"""

    PENDING = "pending_confirmation"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    USED = "used"


class RefundStatus(StrEnum):
    """退款状态机。"""

    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class ProviderRefundResult:
    """支付渠道返回给业务服务的结构化结果。"""

    status: RefundStatus
    provider_reference: str
    message: str
    error_code: str | None = None
    retryable: bool = False


class RefundProvider(Protocol):
    """退款渠道协议；生产环境可以替换为真实支付 SDK 适配器。"""

    def refund(
        self,
        *,
        order_id: str,
        amount_cents: int,
        idempotency_key: str,
    ) -> ProviderRefundResult: ...


class SimulatedRefundProvider:
    """只在本地内存中模拟支付渠道，并按幂等键复用第一次结果。"""

    def __init__(self, mode: RefundStatus = RefundStatus.SUCCEEDED):
        self.mode = mode
        self.call_count = 0
        self._results: dict[str, ProviderRefundResult] = {}

    def refund(
        self,
        *,
        order_id: str,
        amount_cents: int,
        idempotency_key: str,
    ) -> ProviderRefundResult:
        if idempotency_key in self._results:
            return self._results[idempotency_key]

        self.call_count += 1
        reference = f"sim_{uuid.uuid4().hex[:12]}"
        if self.mode == RefundStatus.SUCCEEDED:
            result = ProviderRefundResult(
                status=RefundStatus.SUCCEEDED,
                provider_reference=reference,
                message="本地模拟退款成功。",
            )
        elif self.mode == RefundStatus.FAILED:
            result = ProviderRefundResult(
                status=RefundStatus.FAILED,
                provider_reference=reference,
                message="本地模拟渠道明确拒绝退款。",
                error_code="SIMULATED_PROVIDER_REJECTED",
                retryable=False,
            )
        else:
            result = ProviderRefundResult(
                status=RefundStatus.PROCESSING,
                provider_reference=reference,
                message="本地模拟渠道结果仍在确认。",
                error_code="SIMULATED_RESULT_PENDING",
                retryable=False,
            )
        self._results[idempotency_key] = result
        return result


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _money(amount_cents: int) -> str:
    return f"{amount_cents / 100:.2f}"


class RefundService:
    """使用 SQLite 保存订单、确认记录和退款状态。"""

    def __init__(
        self,
        db_path: str | Path,
        *,
        provider: RefundProvider | None = None,
        confirmation_ttl_minutes: int = 10,
    ):
        if confirmation_ttl_minutes <= 0:
            raise ValueError("confirmation_ttl_minutes 必须大于 0。")
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.provider = provider or SimulatedRefundProvider()
        self.confirmation_ttl = timedelta(minutes=confirmation_ttl_minutes)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS refund_confirmations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                    status TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id)
                );

                CREATE TABLE IF NOT EXISTS refunds (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    confirmation_id TEXT NOT NULL UNIQUE,
                    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                    idempotency_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    provider_reference TEXT,
                    error_code TEXT,
                    retryable INTEGER NOT NULL DEFAULT 0,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id),
                    FOREIGN KEY (confirmation_id) REFERENCES refund_confirmations(id)
                );

                CREATE TABLE IF NOT EXISTS refund_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    refund_id TEXT NOT NULL,
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (refund_id) REFERENCES refunds(id)
                );

                CREATE INDEX IF NOT EXISTS idx_orders_user_id
                ON orders (user_id, id);

                CREATE INDEX IF NOT EXISTS idx_refunds_user_order
                ON refunds (user_id, order_id);
                """
            )

    def seed_demo_orders(self) -> None:
        """写入可重复执行的本地演示订单，不覆盖已有状态。"""
        created_at = _to_iso(_utc_now())
        demo_orders = [
            (
                "order-1001",
                "demo-user",
                "LangChain Agent 实战课程",
                19900,
                OrderStatus.UNSHIPPED,
                created_at,
            ),
            (
                "order-1002",
                "demo-user",
                "Agent 工程手册",
                9900,
                OrderStatus.SHIPPED,
                created_at,
            ),
            (
                "order-2001",
                "other-user",
                "其他用户的私有订单",
                29900,
                OrderStatus.UNSHIPPED,
                created_at,
            ),
        ]
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO orders
                    (id, user_id, item_name, amount_cents, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                demo_orders,
            )

    def list_orders(self, user_id: str) -> dict[str, object]:
        """只返回当前认证用户自己的订单。"""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, item_name, amount_cents, status, created_at
                FROM orders
                WHERE user_id = ?
                ORDER BY created_at, id
                """,
                (user_id,),
            ).fetchall()
        return {
            "ok": True,
            "status": "succeeded",
            "orders": [self._order_payload(row) for row in rows],
        }

    def get_order(self, user_id: str, order_id: str) -> dict[str, object]:
        """联合 user_id 和 order_id 查询，避免只凭订单号越权读取。"""
        with self._connect() as connection:
            row = self._find_order(connection, user_id, order_id)
        if row is None:
            return self._not_found()
        return {"ok": True, "status": "succeeded", "order": self._order_payload(row)}

    def check_eligibility(self, user_id: str, order_id: str) -> dict[str, object]:
        """根据当前订单事实给出确定性的退款资格，不让模型自由决定。"""
        with self._connect() as connection:
            return self._eligibility_in_connection(connection, user_id, order_id)

    def prepare_refund(
        self,
        user_id: str,
        order_id: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, object]:
        """创建绑定用户、订单、金额和过期时间的待确认记录。"""
        current_time = now or _utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            eligibility = self._eligibility_in_connection(connection, user_id, order_id)
            if not eligibility.get("eligible"):
                return eligibility

            # 相同订单已有未过期确认时直接复用，避免模型重复创建多个确认。
            existing = connection.execute(
                """
                SELECT id, amount_cents, status, expires_at
                FROM refund_confirmations
                WHERE user_id = ? AND order_id = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id, order_id, ConfirmationStatus.PENDING),
            ).fetchone()
            if existing is not None and datetime.fromisoformat(existing["expires_at"]) > current_time:
                return self._confirmation_payload(existing, order_id)

            confirmation_id = f"confirm_{uuid.uuid4().hex}"
            expires_at = current_time + self.confirmation_ttl
            amount_cents = int(eligibility["amount_cents"])
            connection.execute(
                """
                INSERT INTO refund_confirmations
                    (id, user_id, order_id, amount_cents, status, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    confirmation_id,
                    user_id,
                    order_id,
                    amount_cents,
                    ConfirmationStatus.PENDING,
                    _to_iso(expires_at),
                    _to_iso(current_time),
                ),
            )
            return {
                "ok": True,
                "status": ConfirmationStatus.PENDING,
                "confirmation_id": confirmation_id,
                "order_id": order_id,
                "amount_cents": amount_cents,
                "amount": _money(amount_cents),
                "expires_at": _to_iso(expires_at),
                "next_action": f"/confirm {confirmation_id}",
                "message": "请核对订单和金额后，通过 CLI 确认；尚未执行退款。",
            }

    def cancel_confirmation(self, user_id: str, confirmation_id: str) -> dict[str, object]:
        """取消属于当前用户且仍待确认的记录。"""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE refund_confirmations
                SET status = ?
                WHERE id = ? AND user_id = ? AND status = ?
                """,
                (
                    ConfirmationStatus.CANCELLED,
                    confirmation_id,
                    user_id,
                    ConfirmationStatus.PENDING,
                ),
            )
        if cursor.rowcount != 1:
            return {
                "ok": False,
                "status": "not_found_or_not_pending",
                "message": "确认记录不存在、无权访问或已不再待确认。",
            }
        return {
            "ok": True,
            "status": ConfirmationStatus.CANCELLED,
            "confirmation_id": confirmation_id,
            "message": "退款确认已取消，未执行退款。",
        }

    def confirm_and_execute(
        self,
        user_id: str,
        confirmation_id: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, object]:
        """确认并执行本地模拟退款；重复确认只返回第一次业务结果。"""
        current_time = now or _utc_now()
        idempotency_key = f"refund:{confirmation_id}"

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_refund = self._find_refund_by_confirmation(
                connection,
                user_id,
                confirmation_id,
            )
            if existing_refund is not None:
                return self._refund_payload(existing_refund, reused=True)

            confirmation = connection.execute(
                """
                SELECT id, user_id, order_id, amount_cents, status, expires_at
                FROM refund_confirmations
                WHERE id = ? AND user_id = ?
                """,
                (confirmation_id, user_id),
            ).fetchone()
            if confirmation is None:
                return {
                    "ok": False,
                    "status": "not_found",
                    "message": "确认记录不存在或无权访问。",
                }
            if confirmation["status"] != ConfirmationStatus.PENDING:
                return {
                    "ok": False,
                    "status": str(confirmation["status"]),
                    "message": "该确认记录已取消、过期或使用，不能再次执行。",
                }
            if datetime.fromisoformat(confirmation["expires_at"]) <= current_time:
                connection.execute(
                    "UPDATE refund_confirmations SET status = ? WHERE id = ?",
                    (ConfirmationStatus.EXPIRED, confirmation_id),
                )
                return {
                    "ok": False,
                    "status": ConfirmationStatus.EXPIRED,
                    "message": "确认已过期，请重新查询订单并生成新的确认。",
                }

            # 确认时的订单状态可能已变化，所以执行副作用前必须重新校验。
            eligibility = self._eligibility_in_connection(
                connection,
                user_id,
                str(confirmation["order_id"]),
            )
            if not eligibility.get("eligible"):
                return eligibility

            refund_id = f"refund_{uuid.uuid4().hex}"
            created_at = _to_iso(current_time)
            connection.execute(
                """
                INSERT INTO refunds
                    (id, user_id, order_id, confirmation_id, amount_cents,
                     idempotency_key, status, message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    refund_id,
                    user_id,
                    confirmation["order_id"],
                    confirmation_id,
                    confirmation["amount_cents"],
                    idempotency_key,
                    RefundStatus.PROCESSING,
                    "退款请求正在由本地模拟渠道处理。",
                    created_at,
                    created_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO refund_events
                    (refund_id, from_status, to_status, reason, created_at)
                VALUES (?, NULL, ?, ?, ?)
                """,
                (
                    refund_id,
                    RefundStatus.PROCESSING,
                    "用户通过确定性 CLI 命令确认退款。",
                    created_at,
                ),
            )

        # 先持久化 processing，再调用外部渠道；即使进程在调用中崩溃，也有记录可对账。
        provider_result = self.provider.refund(
            order_id=str(confirmation["order_id"]),
            amount_cents=int(confirmation["amount_cents"]),
            idempotency_key=idempotency_key,
        )
        return self._apply_provider_result(
            user_id=user_id,
            refund_id=refund_id,
            confirmation_id=confirmation_id,
            order_id=str(confirmation["order_id"]),
            result=provider_result,
            now=current_time,
        )

    def get_refund_status(self, user_id: str, refund_id: str) -> dict[str, object]:
        """查询当前用户自己的退款状态，聊天历史不能代替业务事实。"""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, order_id, amount_cents, status, provider_reference,
                       error_code, retryable, message, created_at, updated_at
                FROM refunds
                WHERE id = ? AND user_id = ?
                """,
                (refund_id, user_id),
            ).fetchone()
        if row is None:
            return {
                "ok": False,
                "status": "not_found",
                "message": "退款记录不存在或无权访问。",
            }
        return self._refund_payload(row)

    def list_refund_events(self, user_id: str, refund_id: str) -> list[dict[str, object]]:
        """返回状态转换审计事件；只允许退款所属用户读取。"""
        with self._connect() as connection:
            owner = connection.execute(
                "SELECT 1 FROM refunds WHERE id = ? AND user_id = ?",
                (refund_id, user_id),
            ).fetchone()
            if owner is None:
                return []
            rows = connection.execute(
                """
                SELECT from_status, to_status, reason, created_at
                FROM refund_events
                WHERE refund_id = ?
                ORDER BY id
                """,
                (refund_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _apply_provider_result(
        self,
        *,
        user_id: str,
        refund_id: str,
        confirmation_id: str,
        order_id: str,
        result: ProviderRefundResult,
        now: datetime,
    ) -> dict[str, object]:
        updated_at = _to_iso(now)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT status FROM refunds WHERE id = ? AND user_id = ?",
                (refund_id, user_id),
            ).fetchone()
            if current is None:
                raise RuntimeError("退款记录在渠道调用后丢失。")

            connection.execute(
                """
                UPDATE refunds
                SET status = ?, provider_reference = ?, error_code = ?,
                    retryable = ?, message = ?, updated_at = ?
                WHERE id = ? AND user_id = ? AND status = ?
                """,
                (
                    result.status,
                    result.provider_reference,
                    result.error_code,
                    int(result.retryable),
                    result.message,
                    updated_at,
                    refund_id,
                    user_id,
                    RefundStatus.PROCESSING,
                ),
            )
            connection.execute(
                """
                INSERT INTO refund_events
                    (refund_id, from_status, to_status, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    refund_id,
                    RefundStatus.PROCESSING,
                    result.status,
                    result.message,
                    updated_at,
                ),
            )
            if result.status == RefundStatus.SUCCEEDED:
                connection.execute(
                    """
                    UPDATE orders
                    SET status = ?
                    WHERE id = ? AND user_id = ? AND status = ?
                    """,
                    (
                        OrderStatus.REFUNDED,
                        order_id,
                        user_id,
                        OrderStatus.UNSHIPPED,
                    ),
                )
                connection.execute(
                    "UPDATE refund_confirmations SET status = ? WHERE id = ?",
                    (ConfirmationStatus.USED, confirmation_id),
                )

            row = connection.execute(
                """
                SELECT id, order_id, amount_cents, status, provider_reference,
                       error_code, retryable, message, created_at, updated_at
                FROM refunds
                WHERE id = ? AND user_id = ?
                """,
                (refund_id, user_id),
            ).fetchone()
        return self._refund_payload(row)

    def _eligibility_in_connection(
        self,
        connection: sqlite3.Connection,
        user_id: str,
        order_id: str,
    ) -> dict[str, object]:
        order = self._find_order(connection, user_id, order_id)
        if order is None:
            return self._not_found()

        active_refund = connection.execute(
            """
            SELECT id, status
            FROM refunds
            WHERE user_id = ? AND order_id = ? AND status IN (?, ?)
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (
                user_id,
                order_id,
                RefundStatus.PROCESSING,
                RefundStatus.SUCCEEDED,
            ),
        ).fetchone()
        if active_refund is not None:
            return {
                "ok": True,
                "status": "ineligible",
                "eligible": False,
                "order_id": order_id,
                "reason": f"订单已有 {active_refund['status']} 退款：{active_refund['id']}。",
            }
        if order["status"] != OrderStatus.UNSHIPPED:
            reason = {
                OrderStatus.SHIPPED: "订单已发货，本地演示不支持自动退款，请进入人工退货流程。",
                OrderStatus.REFUNDED: "订单已经退款。",
                OrderStatus.CANCELLED: "订单已经取消。",
            }.get(str(order["status"]), "当前订单状态不支持自动退款。")
            return {
                "ok": True,
                "status": "ineligible",
                "eligible": False,
                "order_id": order_id,
                "reason": reason,
            }
        return {
            "ok": True,
            "status": "eligible",
            "eligible": True,
            "order_id": order_id,
            "amount_cents": int(order["amount_cents"]),
            "refundable_amount": _money(int(order["amount_cents"])),
            "reason": "订单未发货，符合本地演示的全额退款规则。",
        }

    @staticmethod
    def _find_order(
        connection: sqlite3.Connection,
        user_id: str,
        order_id: str,
    ) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT id, item_name, amount_cents, status, created_at
            FROM orders
            WHERE id = ? AND user_id = ?
            """,
            (order_id, user_id),
        ).fetchone()

    @staticmethod
    def _find_refund_by_confirmation(
        connection: sqlite3.Connection,
        user_id: str,
        confirmation_id: str,
    ) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT id, order_id, amount_cents, status, provider_reference,
                   error_code, retryable, message, created_at, updated_at
            FROM refunds
            WHERE confirmation_id = ? AND user_id = ?
            """,
            (confirmation_id, user_id),
        ).fetchone()

    @staticmethod
    def _order_payload(row: sqlite3.Row) -> dict[str, object]:
        return {
            "order_id": str(row["id"]),
            "item_name": str(row["item_name"]),
            "amount_cents": int(row["amount_cents"]),
            "amount": _money(int(row["amount_cents"])),
            "status": str(row["status"]),
            "created_at": str(row["created_at"]),
        }

    @staticmethod
    def _confirmation_payload(row: sqlite3.Row, order_id: str) -> dict[str, object]:
        return {
            "ok": True,
            "status": str(row["status"]),
            "confirmation_id": str(row["id"]),
            "order_id": order_id,
            "amount_cents": int(row["amount_cents"]),
            "amount": _money(int(row["amount_cents"])),
            "expires_at": str(row["expires_at"]),
            "next_action": f"/confirm {row['id']}",
            "message": "已有待确认退款，请核对后确认；尚未执行退款。",
        }

    @staticmethod
    def _refund_payload(
        row: sqlite3.Row,
        *,
        reused: bool = False,
    ) -> dict[str, object]:
        return {
            "ok": row["status"] in {RefundStatus.PROCESSING, RefundStatus.SUCCEEDED},
            "status": str(row["status"]),
            "refund_id": str(row["id"]),
            "order_id": str(row["order_id"]),
            "amount_cents": int(row["amount_cents"]),
            "amount": _money(int(row["amount_cents"])),
            "provider_reference": row["provider_reference"],
            "error_code": row["error_code"],
            "retryable": bool(row["retryable"]),
            "message": str(row["message"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "reused": reused,
        }

    @staticmethod
    def _not_found() -> dict[str, object]:
        # 不区分“订单不存在”和“属于其他用户”，避免泄露资源是否存在。
        return {
            "ok": False,
            "status": "not_found",
            "eligible": False,
            "message": "订单不存在或无权访问。",
        }
