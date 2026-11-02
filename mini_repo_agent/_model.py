import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


def create_model() -> tuple[OpenAI, str]:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("未找到 DEEPSEEK_API_KEY")

    model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    return client, model


def invoke_model(client: OpenAI, model: str, messages: list[dict], tool_schemas):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tool_schemas,
        # 入门先使用非思考模式，避免额外处理 reasoning_content 的回传。
        extra_body={"thinking": {"type": "disabled"}},
    )
