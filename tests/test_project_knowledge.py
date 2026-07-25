import sys
import tempfile
import unittest
from pathlib import Path

from langchain_core.documents import Document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chapter04_rag.project_knowledge import (  # noqa: E402
    BM25Index,
    ProjectKnowledgeBase,
    load_project_documents,
    split_project_documents,
    tokenize_for_bm25,
)


class ProjectKnowledgeTests(unittest.TestCase):
    def test_tokenizer_supports_chinese_and_python_identifiers(self):
        tokens = tokenize_for_bm25("SQLiteChatStore 实现持久化记忆")

        self.assertIn("sqlitechatstore", tokens)
        self.assertIn("持久", tokens)
        self.assertIn("记忆", tokens)

    def test_splitter_preserves_source_and_line_numbers(self):
        document = Document(
            page_content="第一行\n第二行介绍 Agent\n第三行介绍工具调用\n第四行",
            metadata={"source": "guide.md"},
        )

        chunks = split_project_documents([document], chunk_size=20, chunk_overlap=5)

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].metadata["source"], "guide.md")
        self.assertEqual(chunks[0].metadata["start_line"], 1)
        self.assertGreaterEqual(chunks[-1].metadata["end_line"], 3)

    def test_bm25_ranks_relevant_chunk_first(self):
        documents = [
            Document(
                page_content="SQLiteChatStore 使用 SQLite 保存持久化会话记忆",
                metadata={"source": "memory.md", "start_line": 1, "end_line": 1},
            ),
            Document(
                page_content="calculate 使用 AST 执行安全数学计算",
                metadata={"source": "tools.md", "start_line": 1, "end_line": 1},
            ),
        ]

        hits = BM25Index(documents).search("SQLite 持久化记忆", top_k=2)

        self.assertGreaterEqual(len(hits), 1)
        self.assertEqual(hits[0].source, "memory.md")
        self.assertGreater(hits[0].score, 0)

    def test_project_loader_excludes_secrets_and_local_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "interview_note").mkdir()
            (root / "tests").mkdir()
            (root / "docs" / "public.md").write_text("公开知识", encoding="utf-8")
            (root / "interview_note" / "private.md").write_text("个人笔记", encoding="utf-8")
            (root / "tests" / "test_noise.py").write_text("重复查询噪声", encoding="utf-8")
            (root / ".env").write_text("SECRET=do-not-index", encoding="utf-8")
            (root / "AGENTS.md").write_text("本地说明", encoding="utf-8")

            documents = load_project_documents(root)
            sources = {document.metadata["source"] for document in documents}

        self.assertEqual(sources, {"docs/public.md"})

    def test_formatted_results_include_citation_and_content(self):
        documents = [
            Document(
                page_content="RAG 通过检索外部知识增强模型回答",
                metadata={"source": "rag.md", "start_line": 10, "end_line": 12},
            )
        ]
        knowledge_base = ProjectKnowledgeBase(documents)

        result = knowledge_base.format_search_results("RAG 检索", top_k=1)

        self.assertIn("[来源 1] rag.md:L10-L12", result)
        self.assertIn("检索外部知识", result)

    def test_top_k_is_bounded(self):
        knowledge_base = ProjectKnowledgeBase([])

        result = knowledge_base.format_search_results("RAG", top_k=10)

        self.assertIn("top_k 必须位于 1 到 5", result)


if __name__ == "__main__":
    unittest.main()
