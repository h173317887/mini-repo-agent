from .base import AgentMiddleware


class LoggingMiddleware(AgentMiddleware):
    def before_model(self, state, runtime):
        print(f"[Context] 当前消息数量：{len(state['messages'])}")