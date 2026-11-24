"""W4 integration tests: the real ReAct loop must honor middleware wrappers."""

import json
from unittest.mock import patch

import pytest

from tests.test_runtime import FakeModel
from mini_repo_agent._tools import TOOL_SCHEMAS
from mini_repo_agent.legacy.graph import create_agent
from mini_repo_agent.middleware.base import AgentMiddleware


def make_agent(model, executor, middlewares):
    with patch("mini_repo_agent.legacy.graph.create_model", return_value=model):
        return create_agent(TOOL_SCHEMAS, executor, max_steps=3, middleware=middlewares)


def test_wrap_model_call_integration():
    events = []

    class MiddlewareA(AgentMiddleware):
        def wrap_model_call(self, request, handler):
            events.append("A.before")
            response = handler(request)
            events.append("A.after")
            return response

    class MiddlewareB(AgentMiddleware):
        def wrap_model_call(self, request, handler):
            events.append("B.before")
            response = handler(request)
            events.append("B.after")
            return response

    class InspectingModel(FakeModel):
        def invoke(self, messages, tools):
            events.append("model")
            return super().invoke(messages, tools)

    agent = make_agent(InspectingModel(finish_immediately=True), lambda *args: None, [MiddlewareA(), MiddlewareB()])
    assert agent("直接回答") == "任务完成"
    assert events == ["A.before", "B.before", "model", "B.after", "A.after"]


def test_wrap_tool_call_integration_order_and_pairing():
    events = []

    class MiddlewareA(AgentMiddleware):
        def wrap_tool_call(self, request, handler):
            events.append("A.before")
            assert request["tool_call"]["id"] == "call_1"
            result = handler(request)
            events.append("A.after")
            return result

    class MiddlewareB(AgentMiddleware):
        def wrap_tool_call(self, request, handler):
            events.append("B.before")
            result = handler(request)
            events.append("B.after")
            return result

    def fake_tool(name, raw_arguments):
        events.append("tool")
        assert (name, raw_arguments) == ("list_files", "{}")
        return json.dumps({"ok": True, "result": []})

    model = FakeModel()
    agent = make_agent(model, fake_tool, [MiddlewareA(), MiddlewareB()])
    trace = []
    assert agent("列出文件", trace=trace) == "任务完成"
    assert model.step == 2
    assert events == ["A.before", "B.before", "tool", "B.after", "A.after"]
    tool_events = [e for e in trace if e["event"] == "tool"]
    assert len(tool_events) == 1
    assert tool_events[0]["call_id"] == "call_1"
    assert json.loads(tool_events[0]["result"]) == {"ok": True, "result": []}


def test_wrap_tool_call_short_circuit_skips_executor():
    calls = []

    class DenyMiddleware(AgentMiddleware):
        def wrap_tool_call(self, request, handler):
            call = request["tool_call"]
            return {
                "role": "tool", "tool_call_id": call["id"],
                "content": json.dumps({"ok": False, "error": {"type": "PermissionError", "message": "denied"}}),
            }

    class InspectingModel(FakeModel):
        def invoke(self, messages, tools):
            if self.step == 1:
                tool_message = messages[-1]
                assert tool_message["tool_call_id"] == "call_1"
                payload = json.loads(tool_message["content"])
                assert payload["ok"] is False
                assert payload["error"]["type"] == "PermissionError"
            return super().invoke(messages, tools)

    def fake_tool(name, raw_arguments):
        calls.append(name)
        return json.dumps({"ok": True})

    agent = make_agent(InspectingModel(), fake_tool, [DenyMiddleware()])
    assert agent("列出文件") == "任务完成"
    assert calls == []


def test_wrap_tool_call_rewrites_request_without_mutating_original():
    original_calls = []
    modified_calls = []

    class RewriteMiddleware(AgentMiddleware):
        def wrap_tool_call(self, request, handler):
            original_calls.append(request["tool_call"].copy())
            new_call = {**request["tool_call"], "raw_arguments": '{"path": "README.md"}'}
            result = handler({**request, "tool_call": new_call})
            modified_calls.append(new_call)
            return result

    def fake_tool(name, raw_arguments):
        assert name == "read_file"
        assert json.loads(raw_arguments) == {"path": "README.md"}
        return json.dumps({"ok": True, "result": "ok"})

    agent = make_agent(FakeModel(tool_name="read_file", arguments='{"path": "security.py"}'), fake_tool, [RewriteMiddleware()])
    assert agent("读取文件") == "任务完成"
    assert original_calls[0]["raw_arguments"] == '{"path": "security.py"}'
    assert modified_calls[0]["id"] == "call_1"


def test_wrap_tool_call_rejects_mismatched_tool_call_id():
    class IncorrectMiddleware(AgentMiddleware):
        def wrap_tool_call(self, request, handler):
            return {"role": "tool", "tool_call_id": "other_call", "content": "{}"}

    def should_not_execute(*args):
        pytest.fail("Tool executor must not run when middleware short-circuits")

    agent = make_agent(FakeModel(), should_not_execute, [IncorrectMiddleware()])
    with pytest.raises(ValueError, match="tool_call_id 不匹配"):
        agent("列出文件")


def test_wrap_tool_call_wrapper_exception_propagates():
    class BrokenMiddleware(AgentMiddleware):
        def wrap_tool_call(self, request, handler):
            raise RuntimeError("wrapper failed")

    def should_not_execute(*args):
        pytest.fail("Tool executor must not run after wrapper raises")

    agent = make_agent(FakeModel(), should_not_execute, [BrokenMiddleware()])
    with pytest.raises(RuntimeError, match="wrapper failed"):
        agent("列出文件")
