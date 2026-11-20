"""W4 regression: errors at the tool invocation/implementation boundary."""

import json
from unittest.mock import patch

import pytest

from mini_repo_agent._models import ModelResponse
from mini_repo_agent._tools import TOOL_SCHEMAS, execute_tool
from mini_repo_agent.graph import create_agent
from mini_repo_agent.middleware.base import AgentMiddleware
from mini_repo_agent.middleware.tool_error import ToolErrorMiddleware


class TwoStepModel:
    name = "mock-model"

    def __init__(self, name="read_file", arguments='{"path": "__w4_missing_file_987654321.py"}', expected=None):
        self.name_of_tool = name
        self.arguments = arguments
        self.expected = expected
        self.calls = 0

    def invoke(self, messages, tools):
        self.calls += 1
        if self.calls == 1:
            return ModelResponse(
                content=None,
                tool_calls=[{"id":"call_1","type":"function",
                             "function":{"name":self.name_of_tool,"arguments":self.arguments}}],
                usage=None,
            )
        if self.calls == 2:
            tool_message = messages[-1]
            assert tool_message["role"] == "tool"
            assert tool_message["tool_call_id"] == "call_1"
            if self.expected is not None:
                self.expected(tool_message)
            return ModelResponse(content="任务完成", tool_calls=[], usage=None)
        raise AssertionError("Unexpected model invocation")


def agent_for(model, tool_executor=execute_tool, middlewares=()):
    with patch("mini_repo_agent.graph.create_model", return_value=model):
        return create_agent(TOOL_SCHEMAS, tool_executor, max_steps=3, middleware=list(middlewares))


def test_missing_file_is_caught_and_agent_continues():
    def check(msg):
        value = json.loads(msg["content"])
        assert value["ok"] is False
        assert value["error"]["type"] == "FileNotFoundError"
        assert "__w4_missing_file_987654321.py" in value["error"]["message"]

    model = TwoStepModel(expected=check)
    agent = agent_for(model, middlewares=[ToolErrorMiddleware()])
    trace = []
    assert agent("读取一个不存在的文件", trace=trace) == "任务完成"
    assert model.calls == 2
    tool_events = [record for record in trace if record["event"] == "tool"]
    assert len(tool_events) == 1
    assert tool_events[0]["call_id"] == "call_1"
    assert json.loads(tool_events[0]["result"])["error"]["type"] == "FileNotFoundError"


def test_missing_file_without_handler_propagates():
    model = TwoStepModel()
    agent = agent_for(model)
    with pytest.raises(FileNotFoundError, match="__w4_missing_file_987654321.py"):
        agent("读取一个不存在的文件")
    assert model.calls == 1


def test_unhandled_runtime_error_propagates_through_middleware():
    def broken_tool(name, raw_arguments):
        raise RuntimeError("backend exploded")

    model = TwoStepModel(name="list_files", arguments="{}")
    agent = agent_for(model, tool_executor=broken_tool, middlewares=[ToolErrorMiddleware()])
    with pytest.raises(RuntimeError, match="backend exploded"):
        agent("列出文件")
    assert model.calls == 1


def test_configured_exception_type_is_converted_to_tool_message():
    def broken_tool(name, raw_arguments):
        raise RuntimeError("temporary failure")

    def check(msg):
        payload = json.loads(msg["content"])
        assert payload["error"]["type"] == "RuntimeError"
        assert payload["error"]["message"] == "temporary failure"

    model = TwoStepModel(name="list_files", arguments="{}", expected=check)
    agent = agent_for(model, tool_executor=broken_tool,
                      middlewares=[ToolErrorMiddleware(handle_exceptions=(RuntimeError,))])
    assert agent("列出文件") == "任务完成"
    assert model.calls == 2


@pytest.mark.parametrize(
    ("arguments", "expected_type"),
    [('{"other": "hello"}', "TypeError"), ('{"path":', "JSONDecodeError")],
)
def test_bad_arguments_return_tool_error_without_reaching_handler(arguments, expected_type):
    def check(msg):
        payload = json.loads(msg["content"])
        assert payload["ok"] is False
        assert payload["error"]["type"] == expected_type

    model = TwoStepModel(arguments=arguments, expected=check)
    agent = agent_for(model, middlewares=[ToolErrorMiddleware()])
    assert agent("读取文件") == "任务完成"
    assert model.calls == 2


def test_inner_error_middleware_does_not_hide_outer_wrapper_bug():
    class OuterBrokenMiddleware(AgentMiddleware):
        def wrap_tool_call(self, request, handler):
            raise FileNotFoundError("outer middleware bug")

    model = TwoStepModel(name="list_files", arguments="{}")
    # The tool-error middleware is inner; an outer wrapper bug bypasses it.
    agent = agent_for(model, middlewares=[OuterBrokenMiddleware(), ToolErrorMiddleware()])
    with pytest.raises(FileNotFoundError, match="outer middleware bug"):
        agent("列出文件")
    assert model.calls == 1
