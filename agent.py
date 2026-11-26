import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents.middleware import ToolErrorMiddleware
from langchain_deepseek import ChatDeepSeek

from mini_repo_agent.backends.filesystem import FilesystemBackend
from mini_repo_agent.graph import create_deep_agent
from mini_repo_agent.middleware.filesystem import FilesystemMiddleware
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
    workspace = Path(__file__).resolve().parent / "workspace"
    backend = FilesystemBackend(workspace)
    agent = create_deep_agent(
        model=model,
        system_prompt=(
            "你是一个只读代码分析助手。需要事实时先用工具检查文件，不得猜测文件内容。"
        ),
        middleware=[
            LangChainLoggingMiddleware(),
            ToolErrorMiddleware(on_error=on_tool_error),
            FilesystemMiddleware(backend),
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
