import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek


def main() -> None:
    """通过 LangChain 调用 DeepSeek 并输出模型回答。"""
    load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，请检查 .env 文件。")

    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
        api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        temperature=0.2,
    )

    response = llm.invoke(
        [
            SystemMessage(content="你是一个简洁、专业的中文助手。"),
            HumanMessage(content="用三句话解释什么是 LangChain。"),
        ]
    )
    print(response.content)


if __name__ == "__main__":
    main()
