"""Verify a full LangGraph tool-call round trip using DeepSeek.

Run from the repository root:
    uv run python check_agent.py
"""

import os

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from mini_repo_agent.graph import create_deep_agent
from mini_repo_agent.langchain_tools import TOOLS


def main() -> None:
    load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未找到 DEEPSEEK_API_KEY，请先配置 .env")

    model = ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        extra_body={"thinking": {"type": "disabled"}},
    )
    agent = create_deep_agent(
        model=model,
        tools=TOOLS,
        system_prompt="你是只读代码分析助手，需要事实时必须先读取文件。",
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "请调用 read_file 读取 security.py，然后解释 can_execute 的权限判断逻辑。",
                }
            ]
        }
    )

    messages = result["messages"]
    for message in messages:
        print(type(message).__name__, getattr(message, "name", None))

    read_results = [
        message
        for message in messages
        if isinstance(message, ToolMessage) and message.name == "read_file"
    ]
    if not read_results:
        raise AssertionError("未发现 read_file 的 ToolMessage，完整工具执行链未通过")

    requested_call_ids = {
        call["id"]
        for message in messages
        if isinstance(message, AIMessage)
        for call in message.tool_calls
    }
    if any(message.tool_call_id not in requested_call_ids for message in read_results):
        raise AssertionError("ToolMessage 的 tool_call_id 与 AIMessage 不匹配")

    if any(message.status == "error" for message in read_results):
        raise AssertionError("read_file 工具执行失败")

    print("\n[工具调用链验证通过]")
    print("\n[最终回答]\n" + str(messages[-1].content))


if __name__ == "__main__":
    main()
