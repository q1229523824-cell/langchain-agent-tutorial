import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from chapter03_agent.project_learning_agent import (  # noqa: E402
    calculate,
    read_project_file,
    search_project_files,
    stream_agent_turn,
)
from langchain_core.messages import AIMessage, ToolMessage  # noqa: E402


class FakeStreamingAgent:
    def __init__(self):
        self.received_config = None

    def stream(self, input_data, config, stream_mode, version):
        self.received_config = config
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


class ProjectLearningAgentToolTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
