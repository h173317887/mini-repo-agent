from .base import AgentMiddleware


class LoggingMiddleware(AgentMiddleware):
    def before_model(self, state, runtime):
        print(f"[Context] 当前消息数量：{len(state['messages'])}")

    def after_model(self, state, runtime):
        message = state["messages"][-1]

        usage = message.get("usage_metadata")

        if usage:
            print(f"[Tokens] 输入：{usage['input_tokens']}, 输出：{usage['output_tokens']}")
