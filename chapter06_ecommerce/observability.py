"""线程安全的本地限流、Trace 和聚合指标。"""

from __future__ import annotations

import threading
import time
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from statistics import mean


class RateLimitExceeded(RuntimeError):
    """当前演示用户超过滑动窗口请求上限。"""


class SlidingWindowRateLimiter:
    def __init__(self, *, limit: int = 30, window_seconds: int = 60):
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("限流次数和窗口必须大于 0。")
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, *, now: float | None = None) -> None:
        current = time.monotonic() if now is None else now
        threshold = current - self.window_seconds
        with self._lock:
            history = self._requests[key]
            while history and history[0] <= threshold:
                history.popleft()
            if len(history) >= self.limit:
                raise RateLimitExceeded(
                    f"请求过于频繁：{self.window_seconds} 秒内最多 {self.limit} 次。"
                )
            history.append(current)


@dataclass(frozen=True)
class TraceRecord:
    request_id: str
    user_id: str
    thread_id: str
    intent: str
    route: str
    duration_ms: float
    success: bool
    citations: tuple[str, ...]
    error_type: str | None = None


class TraceStore:
    """只记录运行元数据，不保存用户原始问题和模型回答。"""

    def __init__(self, max_records: int = 1000):
        self._records: deque[TraceRecord] = deque(maxlen=max_records)
        self._lock = threading.Lock()

    def add(self, record: TraceRecord) -> None:
        with self._lock:
            self._records.append(record)

    def recent(self, limit: int = 20) -> list[dict[str, object]]:
        if not 1 <= limit <= 100:
            raise ValueError("limit 必须位于 1 到 100 之间。")
        with self._lock:
            return [asdict(record) for record in list(self._records)[-limit:]]

    def recent_for_user(self, user_id: str, limit: int = 20) -> list[dict[str, object]]:
        """只返回指定用户自己的Trace，避免普通用户查看其他人的运行元数据。"""

        if not 1 <= limit <= 100:
            raise ValueError("limit 必须位于 1 到 100 之间。")
        with self._lock:
            records = [record for record in self._records if record.user_id == user_id]
        return [asdict(record) for record in records[-limit:]]

    def metrics(self) -> dict[str, object]:
        with self._lock:
            records = list(self._records)
        durations = [record.duration_ms for record in records]
        intent_counts = Counter(record.intent for record in records)
        error_count = sum(not record.success for record in records)
        sorted_durations = sorted(durations)
        p95_index = max(0, math_ceil(0.95 * len(sorted_durations)) - 1)
        return {
            "request_count": len(records),
            "success_count": len(records) - error_count,
            "error_count": error_count,
            "success_rate": round((len(records) - error_count) / len(records), 4)
            if records
            else 1.0,
            "average_duration_ms": round(mean(durations), 3) if durations else 0.0,
            "p95_duration_ms": round(sorted_durations[p95_index], 3)
            if sorted_durations
            else 0.0,
            "intent_counts": dict(sorted(intent_counts.items())),
        }


def math_ceil(value: float) -> int:
    """避免仅为一个简单运算引入整个 math 命名空间。"""

    integer = int(value)
    return integer if value == integer else integer + 1
