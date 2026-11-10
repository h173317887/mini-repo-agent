
from uuid import uuid4

from ._models import create_model
from .middleware.base import AgentMiddleware
from .runtime import run_react_loop


def create_agent(tool_schema: list[dict], execute_tool, max_steps: int, middleware: list[AgentMiddleware] | None = None):
    # 从项目根目录读取 .env；已经存在的进程环境变量优先。
    model = create_model()
    def invoke(task, trace: list[dict] | None = None, task_id: str | None = None):
        if task_id is None:
            task_id = uuid4().hex

        messages = [
            {
                "role": "system",
                "content": "你是一个只读代码分析助手。需要事实时先用工具检查文件；不得猜测文件内容。只能使用提供的工具。",
            },
            {"role": "user", "content": task},
        ]
        return run_react_loop(model, messages, tool_schema, execute_tool, max_steps, trace=trace, task_id=task_id, middlewares=middleware)

    return invoke
