from .._context import MiddlewareRuntime
from .._state import AgentState


class AgentMiddleware:
    def before_model(self, state: AgentState, runtime: MiddlewareRuntime) -> dict | None:
        return None

    def after_model(self, state: AgentState, runtime: MiddlewareRuntime) -> dict | None:
        return None

    def wrap_model_call(self, request, handler):
        raise NotImplementedError

    def wrap_tool_call(self, request, handler):
        raise NotImplementedError