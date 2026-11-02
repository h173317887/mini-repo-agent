
from ._model import create_model, invoke_model
from .runtime import run_react_loop


def create_agent(tool_schema: list[dict], execute_tool, max_steps: int):
    # 从项目根目录读取 .env；已经存在的进程环境变量优先。
    client, model = create_model()

    def call_model(messages, tools):
        return invoke_model(client, model, messages, tools)
    def invoke(task):
        messages = [
            {
                "role": "system",
                "content": "你是一个只读代码分析助手。需要事实时先用工具检查文件；不得猜测文件内容。只能使用提供的工具。",
            },
            {"role": "user", "content": task},
        ]
        return run_react_loop(call_model, model, messages, tool_schema, execute_tool, max_steps)

    return invoke
