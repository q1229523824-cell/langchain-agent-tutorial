"""使用 SQLite 保存可跨进程恢复的用户与助手对话。"""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


ALLOWED_ROLES = {"user", "assistant"}


@dataclass(frozen=True)
class StoredMessage:
    """一条从 SQLite 读取的不可变对话消息。"""

    id: int
    thread_id: str
    role: str
    content: str
    created_at: str


class SQLiteChatStore:
    """按 thread_id 持久化对话消息，不保存工具调用和完整图状态。"""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_thread_id_id
                ON messages (thread_id, id)
                """
            )

    def add_message(self, thread_id: str, role: str, content: str) -> int:
        """新增一条消息并返回数据库生成的消息 ID。"""
        thread_id = thread_id.strip()
        content = content.strip()
        if not thread_id:
            raise ValueError("thread_id 不能为空。")
        if role not in ALLOWED_ROLES:
            raise ValueError(f"不支持的消息角色：{role}")
        if not content:
            raise ValueError("消息内容不能为空。")

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages (thread_id, role, content)
                VALUES (?, ?, ?)
                """,
                (thread_id, role, content),
            )
            return int(cursor.lastrowid)

    def add_exchange(self, thread_id: str, user_content: str, assistant_content: str) -> tuple[int, int]:
        """在同一个事务中保存一组用户问题和助手回答。

        Day 3 的 CLI 分两次调用 ``add_message``；如果第二次写入失败，理论上会留下
        只有用户问题的半组记录。Day 14 的 API 使用本方法保证两条消息同时成功或同时回滚。
        """

        thread_id = thread_id.strip()
        user_content = user_content.strip()
        assistant_content = assistant_content.strip()
        if not thread_id:
            raise ValueError("thread_id 不能为空。")
        if not user_content or not assistant_content:
            raise ValueError("用户问题和助手回答都不能为空。")

        with self._connect() as connection:
            user_cursor = connection.execute(
                "INSERT INTO messages (thread_id, role, content) VALUES (?, 'user', ?)",
                (thread_id, user_content),
            )
            assistant_cursor = connection.execute(
                "INSERT INTO messages (thread_id, role, content) VALUES (?, 'assistant', ?)",
                (thread_id, assistant_content),
            )
            return int(user_cursor.lastrowid), int(assistant_cursor.lastrowid)

    def get_messages(self, thread_id: str) -> list[StoredMessage]:
        """按写入顺序返回指定 thread_id 的全部消息。"""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, thread_id, role, content, created_at
                FROM messages
                WHERE thread_id = ?
                ORDER BY id ASC
                """,
                (thread_id,),
            ).fetchall()
        return [StoredMessage(**dict(row)) for row in rows]

    def clear_thread(self, thread_id: str) -> int:
        """清除指定会话并返回删除的消息数量。"""
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM messages WHERE thread_id = ?",
                (thread_id,),
            )
            return cursor.rowcount

    def list_threads(self) -> list[str]:
        """按最近活动时间返回所有会话 ID。"""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT thread_id, MAX(id) AS latest_id
                FROM messages
                GROUP BY thread_id
                ORDER BY latest_id DESC
                """
            ).fetchall()
        return [str(row["thread_id"]) for row in rows]
