import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


@dataclass
class ModelResponse:
    content: str | None
    tool_calls: list[dict]
    usage: dict | None


class DeepSeekModel:
    def __init__(self, client: OpenAI, name: str):
        self.client = client
        self.name = name

    def invoke(self, messages: list[dict], tools: list[dict]):
        response = self.client.chat.completions.create(
            model=self.name,
            messages=messages,
            tools=tools,
            extra_body={"thinking": {"type": "disabled"}},
        )
        message = response.choices[0].message
        usage = None

        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
        
        return ModelResponse(
            content=message.content,
            tool_calls=[
                call.model_dump(exclude_none=True)
                for call in (message.tool_calls or [])
            ],
            usage=usage,
        )


def create_model() -> DeepSeekModel:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("未找到 DEEPSEEK_API_KEY")


    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )

    return DeepSeekModel(
        client=client,
        name=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
    )


