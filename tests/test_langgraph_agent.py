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


def _tool_call_model(name, args, call_id="call_1"):
    return MockToolCallingModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": name, "args": args, "id": call_id}],
            ),
            AIMessage(content="任务完成"),
        ]
    )


def test_missing_file_error_becomes_tool_message_and_continues():
    from langchain.agents.middleware import ToolErrorMiddleware

    calls = []

    @tool
    def read_file(path: str) -> str:
        """Read a fixture file."""
        calls.append(path)
        raise FileNotFoundError(path)

    def on_error(exc, request):
        if isinstance(exc, OSError):
            return f"{type(exc).__name__}: 文件读取失败"
        return None

    result = create_deep_agent(
        model=_tool_call_model("read_file", {"path": "missing.py"}, "missing_1"),
        tools=[read_file],
        middleware=[ToolErrorMiddleware(on_error=on_error)],
    ).invoke({"messages": [{"role": "user", "content": "读取缺失文件"}]})

    messages = result["messages"]
    assert calls == ["missing.py"]
    assert [type(m) for m in messages] == [HumanMessage, AIMessage, ToolMessage, AIMessage]
    assert messages[2].tool_call_id == "missing_1"
    assert messages[2].name == "read_file"
    assert messages[2].status == "error"
    assert "FileNotFoundError" in messages[2].content
    assert messages[3].content == "任务完成"


def test_unhandled_tool_error_propagates():
    import pytest
    from langchain.agents.middleware import ToolErrorMiddleware

    @tool
    def read_file(path: str) -> str:
        """Read a fixture file."""
        raise RuntimeError("unexpected backend error")

    def on_error(exc, request):
        return "file unavailable" if isinstance(exc, OSError) else None

    agent = create_deep_agent(
        model=_tool_call_model("read_file", {"path": "security.py"}),
        tools=[read_file],
        middleware=[ToolErrorMiddleware(on_error=on_error)],
    )
    with pytest.raises(RuntimeError, match="unexpected backend error"):
        agent.invoke({"messages": [{"role": "user", "content": "读取文件"}]})


def test_unknown_tool_returns_error_without_execution():
    executed = []

    @tool
    def read_file(path: str) -> str:
        """Read a fixture file."""
        executed.append(path)
        return "ok"

    result = create_deep_agent(
        model=_tool_call_model("unregistered_tool", {}, "unknown_1"),
        tools=[read_file],
    ).invoke({"messages": [{"role": "user", "content": "调用未知工具"}]})

    assert executed == []
    assert result["messages"][2].tool_call_id == "unknown_1"
    assert result["messages"][2].status == "error"
    assert result["messages"][-1].content == "任务完成"


def test_invalid_tool_arguments_return_error_without_execution():
    executed = []

    @tool
    def read_file(path: str) -> str:
        """Read a fixture file."""
        executed.append(path)
        return "ok"

    result = create_deep_agent(
        model=_tool_call_model("read_file", {"wrong_key": "security.py"}, "invalid_1"),
        tools=[read_file],
    ).invoke({"messages": [{"role": "user", "content": "读取文件"}]})

    assert executed == []
    assert result["messages"][2].tool_call_id == "invalid_1"
    assert result["messages"][2].status == "error"
    assert result["messages"][-1].content == "任务完成"


def test_official_middleware_hook_and_tool_wrapper_order():
    from langchain.agents.middleware import AgentMiddleware

    events = []

    class OuterMiddleware(AgentMiddleware):
        def before_model(self, state, runtime):
            events.append("outer.before_model")

        def after_model(self, state, runtime):
            events.append("outer.after_model")

        def wrap_tool_call(self, request, handler):
            events.append("outer.before_tool")
            result = handler(request)
            events.append("outer.after_tool")
            return result

    class InnerMiddleware(AgentMiddleware):
        def before_model(self, state, runtime):
            events.append("inner.before_model")

        def after_model(self, state, runtime):
            events.append("inner.after_model")

        def wrap_tool_call(self, request, handler):
            events.append("inner.before_tool")
            result = handler(request)
            events.append("inner.after_tool")
            return result

    @tool
    def read_file(path: str) -> str:
        """Read a fixture file."""
        events.append("read_file")
        return "ok"

    result = create_deep_agent(
        model=_tool_call_model("read_file", {"path": "security.py"}),
        tools=[read_file],
        middleware=[OuterMiddleware(), InnerMiddleware()],
    ).invoke({"messages": [{"role": "user", "content": "读取文件"}]})

    assert result["messages"][-1].content == "任务完成"
    assert events == [
        "outer.before_model", "inner.before_model",
        "inner.after_model", "outer.after_model",
        "outer.before_tool", "inner.before_tool", "read_file",
        "inner.after_tool", "outer.after_tool",
        "outer.before_model", "inner.before_model",
        "inner.after_model", "outer.after_model",
    ]


def test_langchain_logging_middleware_uses_ai_message_usage(capsys):
    from mini_repo_agent.middleware.logging import LangChainLoggingMiddleware

    model = MockToolCallingModel(
        responses=[AIMessage(
            content="完成",
            usage_metadata={"input_tokens": 12, "output_tokens": 3, "total_tokens": 15},
        )]
    )
    result = create_deep_agent(
        model=model,
        middleware=[LangChainLoggingMiddleware()],
    ).invoke({"messages": [{"role": "user", "content": "直接回答"}]})

    assert result["messages"][-1].content == "完成"
    logs = capsys.readouterr().out
    assert "[Context] 当前消息数量：" in logs
    assert "[Tokens] 输入：12, 输出：3" in logs
