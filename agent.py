"""A minimal, read-only ReAct coding agent (no LangChain)."""


import sys

from mini_repo_agent._tools import TOOL_SCHEMAS, execute_tool
from mini_repo_agent.graph import create_agent
from mini_repo_agent.middleware.logging import LoggingMiddleware

MAX_STEPS = 10


if __name__ == "__main__":
    question = (
        " ".join(sys.argv[1:]) or "列出文件，读取 security.py，解释权限控制函数的实现。"
    )
    agent = create_agent(TOOL_SCHEMAS, execute_tool, MAX_STEPS, middleware=[LoggingMiddleware()])
    result = agent(question)
    print("\n[最终回答]\n" + result)
