from dataclasses import dataclass


@dataclass(frozen=True)
class AgentContext:
    task_id: str

@dataclass(frozen=True)
class MiddlewareRuntime:
    context: AgentContext

