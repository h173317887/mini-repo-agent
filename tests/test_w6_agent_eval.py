"""W6 fixed-repository scripted trajectory checks (not LLM answer-quality scores)."""

import json
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage

from mini_repo_agent.backends.filesystem import FilesystemBackend
from mini_repo_agent.graph import create_deep_agent
from mini_repo_agent.middleware.filesystem import FilesystemMiddleware

EVAL_DIR = Path(__file__).resolve().parent.parent / "evals"


class ScriptedModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def load_cases():
    return json.loads((EVAL_DIR / "w6_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case["id"])
def test_w6_scripted_agent_eval_trajectory(case):
    """Verify the specified tool trajectory produces the expected factual evidence."""
    responses = [
        AIMessage(
            content="",
            tool_calls=[{
                "name": step["tool"],
                "args": step["args"],
                "id": f"{case['id']}_{i}",
            }],
        )
        for i, step in enumerate(case["steps"], 1)
    ]
    responses.append(AIMessage(content="脚本轨迹结束"))

    agent = create_deep_agent(
        model=ScriptedModel(responses=responses),
        middleware=[FilesystemMiddleware(FilesystemBackend(EVAL_DIR / "fixtures" / "w6_workspace"))],
    )
    result = agent.invoke({"messages": [{"role": "user", "content": case["question"]}]})
    tool_messages = [message for message in result["messages"] if isinstance(message, ToolMessage)]

    assert len(tool_messages) == len(case["steps"])
    for i, (step, message) in enumerate(zip(case["steps"], tool_messages), 1):
        assert message.tool_call_id == f"{case['id']}_{i}"
        assert message.name == step["tool"]
        assert message.status == step["status"]
        for evidence in step["contains"]:
            assert evidence in message.content

    assert result["messages"][-1].content == "脚本轨迹结束"
