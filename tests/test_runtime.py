"""Mock-model regression tests for the ReAct Runtime (no LLM API calls)."""

import json
from unittest.mock import patch
from uuid import UUID

import pytest

from mini_repo_agent.graph import create_agent
from mini_repo_agent._models import ModelResponse, to_api_messages
from mini_repo_agent._tools import TOOL_SCHEMAS, execute_tool
from mini_repo_agent.middleware.base import AgentMiddleware
from mini_repo_agent.middleware.logging import LoggingMiddleware
from mini_repo_agent.runtime import run_react_loop


class FakeModel:
    name = "fake-model"

    def __init__(
        self,
        tool_name: str = "list_files",
        arguments: str = "{}",
        finish_immediately: bool = False,
    ):
        self.tool_name = tool_name
        self.arguments = arguments
        self.finish_immediately = finish_immediately
        self.step = 0

    def invoke(self, messages, tools):
        self.step += 1

        if self.finish_immediately:
            assert self.step == 1
            return ModelResponse(
                content="任务完成",
                tool_calls=[],
                usage={"input_tokens": 10, "output_tokens": 5},
            )

        if self.step == 1:
            return ModelResponse(
                content=None,
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": self.tool_name,
                            "arguments": self.arguments,
                        },
                    }
                ],
                usage={"input_tokens": 10, "output_tokens": 5},
            )

        # The second model call must receive the previous tool observation,
        # even when that observation is an error.
        assert self.step == 2
        assert messages[-1]["role"] == "tool"
        assert messages[-1]["tool_call_id"] == "call_1"

        return ModelResponse(
            content="任务完成",
            tool_calls=[],
            usage={"input_tokens": 8, "output_tokens": 2},
        )


def run_case(model, tool_executor=execute_tool):
    messages = [{"role": "user", "content": "执行测试任务"}]
    trace = []

    result = run_react_loop(
        model,
        messages,
        TOOL_SCHEMAS,
        tool_executor,
        max_steps=3,
        trace=trace,
        task_id="w2-mock-001",
    )

    return result, messages, trace


def get_tool_result(messages):
    tool_messages = [message for message in messages if message["role"] == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call_1"
    return json.loads(tool_messages[0]["content"])


def test_runtime():
    # Mock the tool as well, so this case does not depend on workspace files.
    def fake_tool(name, raw_arguments):
        assert name == "list_files"
        assert raw_arguments == "{}"
        return json.dumps({"ok": True, "result": ["security.py"]})

    model = FakeModel()
    result, messages, trace = run_case(model, tool_executor=fake_tool)

    assert result == "任务完成"
    assert model.step == 2
    assert get_tool_result(messages) == {"ok": True, "result": ["security.py"]}

    model_events = [event for event in trace if event["event"] == "model"]
    tool_events = [event for event in trace if event["event"] == "tool"]
    assert len(model_events) == 2
    assert [event["step"] for event in model_events] == [1, 2]
    assert [event["usage"] for event in model_events] == [
        {"input_tokens": 10, "output_tokens": 5},
        {"input_tokens": 8, "output_tokens": 2},
    ]
    assert all(event["task_id"] == "w2-mock-001" for event in model_events)
    assert all(event["model"] == "fake-model" for event in model_events)
    assert len(tool_events) == 1
    assert "usage" not in tool_events[0]

    assert any(
        record.get("call_id") == "call_1"
        and record.get("name") == "list_files"
        and record.get("task_id") == "w2-mock-001"
        for record in trace
    )


def test_unknown_tool():
    model = FakeModel(tool_name="not_exist")
    result, messages, trace = run_case(model)

    error_result = get_tool_result(messages)
    assert result == "任务完成"
    assert model.step == 2
    assert error_result["ok"] is False
    assert error_result["error"]["type"] == "ValueError"
    assert "未知或未授权" in error_result["error"]["message"]
    assert any(record.get("name") == "not_exist" for record in trace)


def test_invalid_arguments():
    model = FakeModel(tool_name="read_file", arguments='{"path":')
    result, messages, trace = run_case(model)

    error_result = get_tool_result(messages)
    assert result == "任务完成"
    assert model.step == 2
    assert error_result["ok"] is False
    assert error_result["error"]["type"] == "JSONDecodeError"
    assert any(
        record.get("arguments") == '{"path":'
        and record.get("call_id") == "call_1"
        for record in trace
    )


def test_model_ends_without_tools():
    model = FakeModel(finish_immediately=True)
    result, messages, trace = run_case(model)

    assert result == "任务完成"
    assert model.step == 1
    assert messages == [
        {"role": "user", "content": "执行测试任务"},
        {
            "role": "assistant",
            "content": "任务完成",
            "usage_metadata": {"input_tokens": 10, "output_tokens": 5},
        },
    ]
    assert len(trace) == 1
    assert trace[0]["event"] == "model"
    assert trace[0]["usage"] == {"input_tokens": 10, "output_tokens": 5}
    assert trace[0]["task_id"] == "w2-mock-001"


def test_default_task_id():
    # Patch only agent assembly; the Runtime still executes normally.
    with patch(
        "mini_repo_agent.graph.create_model",
        return_value=FakeModel(finish_immediately=True),
    ):
        agent = create_agent(TOOL_SCHEMAS, execute_tool, max_steps=3)

    trace = []
    assert agent("直接回答", trace=trace) == "任务完成"
    assert len(trace) == 1
    assert trace[0]["event"] == "model"

    task_id = trace[0]["task_id"]
    assert isinstance(task_id, str)
    assert len(task_id) == 32
    assert UUID(hex=task_id).hex == task_id


@pytest.mark.parametrize("task_id", [None, "middleware-task-001"])
def test_middleware_context_and_message_updates(task_id):
    instruction = {"role": "system", "content": "中间件添加的指令"}
    observed_roles = []

    class InstructionMiddleware(AgentMiddleware):
        def before_model(self, state, runtime):
            assert runtime.context.task_id == (task_id or "")
            observed_roles.append([message["role"] for message in state["messages"]])
            if len(observed_roles) == 1:
                return {"messages": [instruction, *state["messages"]]}
            return None

    class InspectingModel(FakeModel):
        def invoke(self, messages, tools):
            assert messages[0] == instruction
            return super().invoke(messages, tools)

    def fake_tool(name, raw_arguments):
        return json.dumps({"ok": True, "result": []})

    model = InspectingModel()
    result = run_react_loop(
        model,
        [{"role": "user", "content": "执行测试任务"}],
        TOOL_SCHEMAS,
        fake_tool,
        max_steps=3,
        task_id=task_id,
        middlewares=[InstructionMiddleware()],
    )

    assert result == "任务完成"
    assert model.step == 2
    assert observed_roles == [["user"], ["system", "user", "assistant", "tool"]]


# W3 middleware lifecycle and provider-message boundary regression tests

def test_middleware_order_and_state_visibility():
    """before hooks run A→B, after hooks B→A; updates are visible downstream."""
    events = []
    initial_messages = [{"role": "user", "content": "测试执行顺序"}]
    final_messages = []

    class MiddlewareA(AgentMiddleware):
        def before_model(self, state, runtime):
            events.append("A.before")
            return {
                "messages": [
                    *state["messages"],
                    {"role": "system", "content": "规则A"},
                ]
            }

        def after_model(self, state, runtime):
            events.append("A.after")
            assert state["messages"][-1]["verified_by"] == "B"
            final_messages.extend(state["messages"])

    class MiddlewareB(AgentMiddleware):
        def before_model(self, state, runtime):
            events.append("B.before")
            assert state["messages"][-1]["content"] == "规则A"
            return {
                "messages": [
                    *state["messages"],
                    {"role": "system", "content": "规则B"},
                ]
            }

        def after_model(self, state, runtime):
            events.append("B.after")
            last_message = state["messages"][-1]
            assert last_message["role"] == "assistant"
            assert last_message["usage_metadata"] == {
                "input_tokens": 10,
                "output_tokens": 5,
            }
            return {
                "messages": [
                    *state["messages"][:-1],
                    {**last_message, "verified_by": "B"},
                ]
            }

    class InspectingModel(FakeModel):
        def invoke(self, messages, tools):
            events.append("model")
            assert [message["content"] for message in messages] == [
                "测试执行顺序",
                "规则A",
                "规则B",
            ]
            return super().invoke(messages, tools)

    model = InspectingModel(finish_immediately=True)
    result = run_react_loop(
        model,
        initial_messages,
        TOOL_SCHEMAS,
        execute_tool,
        max_steps=2,
        middlewares=[MiddlewareA(), MiddlewareB()],
    )

    assert result == "任务完成"
    assert events == ["A.before", "B.before", "model", "B.after", "A.after"]
    assert initial_messages == [{"role": "user", "content": "测试执行顺序"}]
    assert [message["role"] for message in final_messages] == [
        "user", "system", "system", "assistant",
    ]


def test_middleware_hooks_run_on_each_model_call():
    """Hooks run even when the model does not request a tool on its last turn."""
    observations = []

    class SpyMiddleware(AgentMiddleware):
        def before_model(self, state, runtime):
            observations.append(("before", state["messages"][-1]["role"]))

        def after_model(self, state, runtime):
            observations.append(("after", state["messages"][-1]["role"]))

    def fake_tool(name, raw_arguments):
        assert name == "list_files"
        return json.dumps({"ok": True, "result": []})

    result = run_react_loop(
        FakeModel(),
        [{"role": "user", "content": "执行测试任务"}],
        TOOL_SCHEMAS,
        fake_tool,
        max_steps=3,
        middlewares=[SpyMiddleware()],
    )

    assert result == "任务完成"
    assert observations == [
        ("before", "user"),
        ("after", "assistant"),
        ("before", "tool"),
        ("after", "assistant"),
    ]


def test_to_api_messages_drops_internal_metadata_without_mutation():
    """State metadata must not leak to the DeepSeek request message payload."""
    messages = [
        {"role": "user", "content": "你好"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "call_1", "function": {"name": "list_files", "arguments": "{}"}, "type": "function"}],
            "usage_metadata": {"input_tokens": 100, "output_tokens": 20},
            "verified_by": "B",
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": '{"ok": true}',
            "internal_trace_id": "trace-1",
        },
    ]

    api_messages = to_api_messages(messages)

    assert api_messages == [
        {"role": "user", "content": "你好"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": messages[1]["tool_calls"],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": '{"ok": true}'},
    ]
    assert "usage_metadata" in messages[1]
    assert "verified_by" in messages[1]
    assert "internal_trace_id" in messages[2]


@pytest.mark.parametrize("enabled", [True, False])
def test_logging_middleware_is_optional(capsys, enabled):
    with patch(
        "mini_repo_agent.graph.create_model",
        return_value=FakeModel(finish_immediately=True),
    ):
        agent = create_agent(
            TOOL_SCHEMAS,
            execute_tool,
            max_steps=2,
            middleware=[LoggingMiddleware()] if enabled else [],
        )

    assert agent("直接回答") == "任务完成"
    output = capsys.readouterr().out
    assert ("[Context]" in output) is enabled
    assert ("[Tokens]" in output) is enabled
