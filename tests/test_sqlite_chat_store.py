import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chapter03_agent.sqlite_chat_store import SQLiteChatStore  # noqa: E402


class SQLiteChatStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_directory.name) / "chat.db"

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_messages_survive_store_recreation(self):
        first_store = SQLiteChatStore(self.db_path)
        first_store.add_message("study", "user", "我叫小林")
        first_store.add_message("study", "assistant", "你好，小林")

        reopened_store = SQLiteChatStore(self.db_path)
        messages = reopened_store.get_messages("study")

        self.assertEqual([message.role for message in messages], ["user", "assistant"])
        self.assertEqual([message.content for message in messages], ["我叫小林", "你好，小林"])

    def test_threads_are_isolated_and_listed_by_recent_activity(self):
        store = SQLiteChatStore(self.db_path)
        store.add_message("study", "user", "学习问题")
        store.add_message("interview", "user", "面试问题")

        self.assertEqual(store.list_threads(), ["interview", "study"])
        self.assertEqual(
            [message.content for message in store.get_messages("study")],
            ["学习问题"],
        )

    def test_clear_only_removes_selected_thread(self):
        store = SQLiteChatStore(self.db_path)
        store.add_message("study", "user", "需要删除")
        store.add_message("interview", "user", "需要保留")

        deleted = store.clear_thread("study")

        self.assertEqual(deleted, 1)
        self.assertEqual(store.get_messages("study"), [])
        self.assertEqual(len(store.get_messages("interview")), 1)

    def test_rejects_invalid_role_and_empty_content(self):
        store = SQLiteChatStore(self.db_path)

        with self.assertRaises(ValueError):
            store.add_message("study", "system", "不允许")
        with self.assertRaises(ValueError):
            store.add_message("study", "user", "   ")


if __name__ == "__main__":
    unittest.main()
