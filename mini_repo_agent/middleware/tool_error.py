import json

from .base import AgentMiddleware


class ToolErrorMiddleware(AgentMiddleware):
    def __init__(self, handle_exceptions: tuple[type[Exception], ...] = (OSError,)):
        self.handle_exceptions = handle_exceptions

    def wrap_tool_call(self, request, handle):
        try:
            return handle(request)
        except self.handle_exceptions as exc:
            return {
                "role": "tool",
                "tool_call_id": request["tool_call"]["id"],
                "status": "error",
                "content": json.dumps(
                    {
                        "ok": False,
                        "error": {
                            "type": type(exc).__name__,
                            "message": str(exc),
                        },
                    },
                    ensure_ascii=False,
                ),
            }
