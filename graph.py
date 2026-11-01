
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from runtime import run_react_loop


def run_agent(task: str, tool_schema:list[dict], execute_tool, max_steps: int) -> str:
    # 从项目根目录读取 .env；已经存在的进程环境变量优先。
    load_dotenv(Path(__file__).resolve().parent / ".env")
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise SystemExit(
            "未找到 DEEPSEEK_API_KEY，请复制 .env.example 为 .env 并填入真实密钥"
        )
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    # DeepSeek 兼容 OpenAI Python SDK；实际请求发往 DeepSeek，而非 OpenAI。
    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    messages = [
        {
            "role": "system",
            "content": "你是一个只读代码分析助手。需要事实时先用工具检查文件；不得猜测文件内容。只能使用提供的工具。",
        },
        {"role": "user", "content": task},
    ]

    return run_react_loop(client, model, messages, tool_schema, execute_tool, max_steps)
