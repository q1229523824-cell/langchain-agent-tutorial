import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chapter03_agent.project_learning_agent import (  # noqa: E402
    AgentRuntimeSettings,
    build_agent_middleware,
    calculate,
    ensure_retrieval_citations,
    read_project_file,
    retrieve_project_knowledge,
    search_project_files,
    stream_agent_turn,
    print_thread_history,
)
from chapter03_agent.sqlite_chat_store import SQLiteChatStore  # noqa: E402
from langchain_core.messages import AIMessage, RemoveMessage, ToolMessage  # noqa: E402
from langchain_core.language_models.fake_chat_models import FakeListChatModel  # noqa: E402


class FakeStreamingAgent:
    def __init__(self):
        self.received_config = None
        self.received_input_data = None

    def stream(self, input_data, config, stream_mode, version):
        self.received_config = config
        self.received_input_data = input_data
        yield {
            "type": "updates",
            "data": {
                "model": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "calculate",
                                    "args": {"expression": "6 * 7"},
                                    "id": "call-1",
                                    "type": "tool_call",
                                }
                            ],
                        )
                    ]
                }
            },
        }
        yield {
            "type": "updates",
            "data": {
                "tools": {
                    "messages": [
                        ToolMessage(content="42", tool_call_id="call-1", name="calculate")
                    ]
                }
            },
        }
        yield {
            "type": "updates",
            "data": {"model": {"messages": [AIMessage(content="答案是 42。")]}},
        }


class FakeSummarizingAgent(FakeStreamingAgent):
    def stream(self, input_data, config, stream_mode, version):
        yield {
            "type": "updates",
            "data": {
                "SummarizationMiddleware.before_model": {
                    "messages": [
                        RemoveMessage(id="__remove_all__"),
                        AIMessage(content="旧历史摘要"),
                    ]
                }
            },
        }
        yield from super().stream(input_data, config, stream_mode, version)


class ProjectLearningAgentToolTests(unittest.TestCase):
    def test_runtime_settings_reject_invalid_limits(self):
        with self.assertRaises(ValueError):
            AgentRuntimeSettings(summary_trigger_messages=10, summary_keep_messages=10).validate()
        with self.assertRaises(ValueError):
            AgentRuntimeSettings(tool_call_limit=0).validate()

    def test_builds_context_and_budget_middleware(self):
        settings = AgentRuntimeSettings(
            summary_trigger_messages=20,
            summary_keep_messages=8,
            model_call_limit=5,
            tool_call_limit=4,
        )
        model = FakeListChatModel(responses=["摘要"])

        middleware = build_agent_middleware(model, settings)

        self.assertEqual(middleware[0].trigger, ("messages", 20))
        self.assertEqual(middleware[0].keep, ("messages", 8))
        self.assertIn("不可信数据", middleware[0].summary_prompt)
        self.assertEqual(middleware[1].run_limit, 5)
        self.assertEqual(middleware[2].run_limit, 4)

    def test_calculate_expression(self):
        result = calculate.invoke({"expression": "(18 * 5 + 10) / 4"})
        self.assertEqual(result, "25.0")

    def test_calculator_rejects_code(self):
        result = calculate.invoke({"expression": "__import__('os').system('dir')"})
        self.assertIn("计算失败", result)

    def test_search_finds_agent_source(self):
        result = search_project_files.invoke({"keyword": "ChatDeepSeek"})
        self.assertIn("chapter03_agent/project_learning_agent.py", result)

    def test_read_allows_source_but_blocks_env(self):
        source = read_project_file.invoke(
            {"relative_path": "chapter03_agent/project_learning_agent.py"}
        )
        blocked = read_project_file.invoke({"relative_path": ".env"})
        self.assertIn("def build_agent", source)
        self.assertIn("读取失败", blocked)

    def test_read_blocks_local_interview_notes(self):
        blocked = read_project_file.invoke(
            {"relative_path": "interview_note/day01-day03-agent-interview.md"}
        )
        self.assertIn("读取失败", blocked)

    def test_rag_tool_returns_source_citations(self):
        result = retrieve_project_knowledge.invoke(
            {"query": "Day 4 上下文摘要和工具调用预算", "top_k": 3}
        )
        self.assertIn("[来源 1]", result)
        self.assertIn(":L", result)
        self.assertIn("day04-context-engineering.md", result)

    def test_missing_model_citations_are_filled_from_real_tool_sources(self):
        answer = ensure_retrieval_citations(
            "Day 4 使用摘要中间件控制上下文。",
            [
                "docs/day04-context-engineering.md:L1-L24",
                "chapter03_agent/project_learning_agent.py:L185-L206",
            ],
        )

        self.assertIn("检索来源（系统补全）", answer)
        self.assertIn("[docs/day04-context-engineering.md:L1-L24]", answer)

    def test_existing_real_citation_is_not_duplicated(self):
        original = "结论。[docs/day04-context-engineering.md:L1-L24]"

        answer = ensure_retrieval_citations(
            original,
            ["docs/day04-context-engineering.md:L1-L24"],
        )

        self.assertEqual(answer, original)

    def test_stream_logs_tools_and_uses_thread_id(self):
        agent = FakeStreamingAgent()
        output = StringIO()
        with redirect_stdout(output):
            answer = stream_agent_turn(agent, "memory-test", "算一下 6 * 7")

        self.assertEqual(answer, "答案是 42。")
        self.assertEqual(
            agent.received_config,
            {"configurable": {"thread_id": "memory-test"}},
        )
        self.assertIn("[工具调用] calculate", output.getvalue())
        self.assertIn("[工具结果] calculate", output.getvalue())

    def test_stream_hydrates_persisted_messages_before_current_input(self):
        agent = FakeStreamingAgent()
        prior_messages = [
            {"role": "user", "content": "我叫小林"},
            {"role": "assistant", "content": "你好，小林"},
        ]

        with redirect_stdout(StringIO()):
            stream_agent_turn(
                agent,
                "persistent-test",
                "我叫什么？",
                prior_messages=prior_messages,
            )

        self.assertEqual(
            agent.received_input_data["messages"],
            [*prior_messages, {"role": "user", "content": "我叫什么？"}],
        )

    def test_stream_logs_context_summarization(self):
        agent = FakeSummarizingAgent()
        output = StringIO()

        with redirect_stdout(output):
            answer = stream_agent_turn(agent, "summary-test", "继续")

        self.assertEqual(answer, "答案是 42。")
        self.assertIn("[上下文摘要]", output.getvalue())

    def test_print_history_reads_persisted_messages(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteChatStore(Path(directory) / "chat.db")
            store.add_message("study", "user", "学习 Agent")
            store.add_message("study", "assistant", "从工具调用开始")
            output = StringIO()

            with redirect_stdout(output):
                print_thread_history(store, "study")

        self.assertIn("你> 学习 Agent", output.getvalue())
        self.assertIn("助手> 从工具调用开始", output.getvalue())


if __name__ == "__main__":
    unittest.main()
