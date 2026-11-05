"""Mock-model regression tests for the ReAct Runtime (no LLM API calls)."""

import json
from unittest.mock import patch
from uuid import UUID

from mini_repo_agent.graph import create_agent
from mini_repo_agent._models import ModelResponse
from mini_repo_agent._tools import TOOL_SCHEMAS, execute_tool
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
    assert messages == [{"role": "user", "content": "执行测试任务"}]
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


if __name__ == "__main__":
    test_runtime()
    test_unknown_tool()
    test_invalid_arguments()
    test_model_ends_without_tools()
    test_default_task_id()
    print("W2 Mock 测试通过（5/5）")
