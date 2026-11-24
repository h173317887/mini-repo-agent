"""W5 regression: LangGraph executes a tool call and returns the result to the model.

Runs entirely with fake model/tool; no DeepSeek API key or workspace files needed.
"""

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from mini_repo_agent.graph import create_deep_agent


class MockToolCallingModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        """Fake model: accept tool binding without requiring a provider API."""
        return self


def test_tool_call_round_trip():
    calls = []

    @tool
    def read_file(path: str) -> str:
        """Read a file in the test fixture."""
        calls.append(path)
        return "def can_execute(): return True"

    model = MockToolCallingModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "read_file",
                        "args": {"path": "security.py"},
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="任务完成"),
        ]
    )

    agent = create_deep_agent(model=model, tools=[read_file])
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "读取 security.py"}]}
    )

    messages = result["messages"]
    assert [type(message) for message in messages] == [
        HumanMessage,
        AIMessage,
        ToolMessage,
        AIMessage,
    ]
    assert calls == ["security.py"]
    assert messages[1].tool_calls[0]["id"] == "call_1"
    assert messages[2].name == "read_file"
    assert messages[2].tool_call_id == "call_1"
    assert messages[2].status == "success"
    assert messages[2].content == "def can_execute(): return True"
    assert messages[-1].content == "任务完成"
