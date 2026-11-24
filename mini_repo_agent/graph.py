"""Deep Agents-style assembly using LangChain/LangGraph Runtime."""

from collections.abc import Callable, Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from ._models import resolve_model


def create_deep_agent(
    model: str | BaseChatModel,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    middleware: Sequence[AgentMiddleware] = (),
) -> CompiledStateGraph:
    model = resolve_model(model)
    return create_agent(
        model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
    )
