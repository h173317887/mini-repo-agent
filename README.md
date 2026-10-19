# Mini Repo Agent — 第一章实战（DeepSeek）

不依赖 LangChain / LangGraph。使用 Python 和兼容 OpenAI 格式的 **DeepSeek Chat Completions API** 实现最小只读 ReAct Agent。

> 代码里的 `from openai import OpenAI` 是 DeepSeek 官方支持的 SDK 接入方式，实际请求由 `base_url` 指向 DeepSeek，不会调用 OpenAI 模型。

## 1. 准备环境

需要 Python >= 3.10、`uv` 和 [DeepSeek 开放平台](https://platform.deepseek.com/) 的 API Key。

```bash
git clone https://github.com/h173317887/mini-repo-agent.git
cd mini-repo-agent
uv sync
```

## 2. 配置 DeepSeek

在终端设置 API Key：

```bash
export DEEPSEEK_API_KEY='替换为你自己的 DeepSeek API Key'
```

默认模型为 **`deepseek-flash`**，默认 API 地址为 `https://api.deepseek.com`，因此无需配置其他环境变量。如需显式指定：

```bash
export DEEPSEEK_MODEL='deepseek-flash'
export DEEPSEEK_BASE_URL='https://api.deepseek.com'
```

目前为了方便学习 ReAct，代码显式采用 DeepSeek **非思考模式**。以后学习上下文工程时可以再研究思考模式下 `reasoning_content` 的正确回传方式。

**不要把真实 API Key 写进代码、README 或提交到 Git。**

## 3. 运行 Agent

```bash
uv run python agent.py "先列出文件，再读取 security.py，回答 reader 角色能否删除文档以及原因。"
```

观察日志：
- `第 N 轮`：Harness 向 DeepSeek 发起一次模型请求。
- `[Action]`：DeepSeek 决定要调用的工具及参数。
- `[Observation]`：Python Harness 执行工具并返回结果。
- `[最终回答]`：模型不再请求工具时返回的回答。

模型的实际执行路径可能不同，不保证每次都恰好调用相同数量的工具。

## 4. 三个实验

1. 正常运行，记录每一轮 Action 和 Observation。
2. 保留工具结果消息，但临时将其 `content` 设为 `""`，观察模型缺少观察结果时会怎样（**不要直接删除 `role="tool"` 消息，否则可能破坏 API 协议**）。实验后恢复。
3. 临时从请求中移除 `tools=TOOL_SCHEMAS`，观察模型失去工具定义后的反应。实验后恢复。

实验的输出只用于分析上下文与工具机制，不能据此判定真实任务成功。

## 5. 安全边界

- 只读取 `workspace/` 下允许的普通文本文件；拒绝路径越界、隐藏文件和其他后缀。
- `TOOL_HANDLERS` 是工具白名单，未注册的工具不会执行。
- 不提供写入文件、执行 Shell 命令或联网工具。
- 这是教学工程，不是生产级沙盒。正式产品需要更严格的权限和隔离。

## 参考文档

- [DeepSeek API：首次调用](https://api-docs.deepseek.com/zh-cn/)
- [DeepSeek API：Tool Calls](https://api-docs.deepseek.com/zh-cn/guides/tool_calls/)
