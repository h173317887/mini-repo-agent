"""Smoke-test the ReAct loop without making an LLM API request."""

import json

from mini_repo_agent._models import ModelResponse
from mini_repo_agent._tools import TOOL_SCHEMAS, execute_tool
from mini_repo_agent.runtime import run_react_loop


class FakeModel:
    name = "fake-model"

    def __init__(self):
        self.step = 0

    def invoke(self, messages, tools):
        self.step += 1

        if self.step == 1:
            return ModelResponse(
                content=None,
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "list_files",
                            "arguments": "{}",
                        },
                    }
                ],
                usage={"input_tokens": 10, "output_tokens": 5},
            )

        # The second model call must receive the tool observation.
        assert self.step == 2
        assert messages[-1]["role"] == "tool"
        assert messages[-1]["tool_call_id"] == "call_1"
        assert json.loads(messages[-1]["content"])["ok"] is True

        return ModelResponse(
            content="任务完成",
            tool_calls=[],
            usage={"input_tokens": 8, "output_tokens": 2},
        )


def test_runtime():
    messages = [{"role": "user", "content": "列出文件"}]
    trace = []
    model = FakeModel()

    result = run_react_loop(
        model,
        messages,
        TOOL_SCHEMAS,
        execute_tool,
        max_steps=3,
        trace=trace,
        task_id="w2-mock-001",
    )

    assert result == "任务完成"
    assert model.step == 2
    assert any(msg["role"] == "tool" for msg in messages)
    assert any(
        record.get("call_id") == "call_1"
        and record.get("name") == "list_files"
        and record.get("task_id") == "w2-mock-001"
        for record in trace
    )

    print("Mock 测试通过")


if __name__ == "__main__":
    test_runtime()
