import os
import sys

from dotenv import load_dotenv
from langchain.agents.middleware import ToolErrorMiddleware
from langchain_deepseek import ChatDeepSeek

from mini_repo_agent.graph import create_deep_agent
from mini_repo_agent.langchain_tools import TOOLS
from mini_repo_agent.middleware.logging import LangChainLoggingMiddleware


def on_tool_error(exc, request):
    if isinstance(exc, OSError):
        return f"{type(exc).__name__}: 文件操作失败，请检查路径"
    return None


def main():
    load_dotenv()

    model = ChatDeepSeek(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
        api_key=os.environ["DEEPSEEK_API_KEY"],
        api_base=os.getenv(
            "DEEPSEEK_BASE_URL",
            "https://api.deepseek.com",
        ),
        extra_body={"thinking": {"type": "disabled"}},
    )

    agent = create_deep_agent(
        model=model,
        tools=TOOLS,
        system_prompt=(
            "你是一个只读代码分析助手。需要事实时先用工具检查文件，不得猜测文件内容。"
        ),
        middleware=[
            LangChainLoggingMiddleware(),
            ToolErrorMiddleware(on_error=on_tool_error),
        ],
    )

    question = " ".join(sys.argv[1:]) or "读取 security.py，解释权限控制逻辑"

    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"recursion_limit": 30},
    )

    print("\n[最终回答]\n" + str(result["messages"][-1].content))


if __name__ == "__main__":
    main()
