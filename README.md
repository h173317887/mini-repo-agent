# Mini Repo Agent — 轻量级 Deep Agents Harness

通过 Python 学习并逐步实现 Deep Agents 风格的 Agent Harness。当前处于 **W5**：正式入口基于 LangChain / LangGraph，不直接调用完整的 `deepagents.create_deep_agent()`。

## 环境与启动

需要 Python >= 3.10、[uv](https://docs.astral.sh/uv/) 和 [DeepSeek API Key](https://platform.deepseek.com/)。

```bash
uv sync
cp .env.example .env
# 在 .env 中填入 DEEPSEEK_API_KEY
uv run python agent.py "读取 security.py，解释 can_execute 的权限判断"
```

Windows PowerShell 可用 `Copy-Item .env.example .env` 复制模板。已有的系统环境变量优先于 `.env`。**不要把真实 API Key 提交到 Git。**

正式调用链：

```text
agent.py
  → mini_repo_agent.graph.create_deep_agent()
  → langchain.agents.create_agent()
  → LangGraph Runtime / ToolNode
```

正式入口使用 `ChatDeepSeek`、LangChain Tools 及 Middleware。W6 才会实现 `BackendProtocol` 和 `FilesystemMiddleware`。

## 测试

```bash
uv run pytest -q
uv run pytest tests/test_langgraph_agent.py -v
uv run python check_agent.py
```

- `tests/test_langgraph_agent.py`：假模型 + 假工具，无需 DeepSeek Key；验证成功调用、缺失文件、未知工具、参数错误、Middleware 顺序与日志。
- `tests/test_runtime.py`、`tests/test_w4_middleware.py`、`tests/test_tool_error_middleware.py`：W1–W4 手写 Runtime 的教学回归测试。
- `check_agent.py`：真实模型的冒烟验证，需要 API Key。

## 代码结构

- `mini_repo_agent/graph.py`：正式 `create_deep_agent()` 组装入口。
- `mini_repo_agent/legacy/graph.py`、`mini_repo_agent/legacy/runtime.py`：W1–W4 手写实现，仅供学习与旧测试使用；**正式入口不会导入它们**。
- `mini_repo_agent/middleware/`：当前同时放置教学版与新版日志中间件，下一阶段按需继续整理。
- `docs/mini-deep-agents-18周开发计划.md`：开发路线与验收要求。
- `docs/每周开发约束.md`：对齐 Deep Agents 官方源码的约束。

## 安全边界

当前仅提供受限的 `workspace/` 文件读取工具，不允许任意目录读取、文件写入或 Shell 命令执行。教学代码不等于生产级沙盒；生产环境需要进一步的权限控制和隔离。
