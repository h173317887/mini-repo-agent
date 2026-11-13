
from uuid import uuid4

from ._models import create_model
from .middleware.base import AgentMiddleware
from .runtime import run_react_loop


def _chain_model_call_handlers(handles):
    if not handles:
        return None
    if len(handles) == 1:
        return handles[0]

    def compose_two(outer, inner):
        def composed(request, handler):
            def inner_handler(req):
                return inner(req, handler)

            return outer(request, inner_handler)

        return composed

    composed_handler = compose_two(handles[-2], handles[-1])

    for h in reversed(handles[:-2]):
        composed_handler = compose_two(h, composed_handler)

    return composed_handler


def _chain_tool_call_wrappers(wrappers):
    if not wrappers:
        return None

    if len(wrappers) == 1:
        return wrappers[0]

    def compose_two(outer, inner):
        def composed(request, execute):
            def inner_handler(req):
                return inner(req, execute)

            return outer(request, inner_handler);

        return composed;

    result = wrappers[-1]

    for wrapper in reversed(wrappers[:-1]):
        result = compose_two(wrapper, result)

    return result

def create_agent(tool_schema: list[dict], execute_tool, max_steps: int, middleware: list[AgentMiddleware] | None = None):
    # 从项目根目录读取 .env；已经存在的进程环境变量优先。
    model = create_model()

    handlers = [
        m.wrap_model_call
        for m in middleware or []
        if m.__class__.wrap_model_call is not AgentMiddleware.wrap_model_call
    ]

    wrap_model_call_handler = _chain_model_call_handlers(handlers)

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
        return run_react_loop(
            model,
            messages,
            tool_schema,
            execute_tool,
            max_steps,
            trace=trace,
            task_id=task_id,
            middlewares=middleware,
            wrap_model_call_handler=wrap_model_call_handler,
        )

    return invoke
