# Mini Repo Agent — 第一章实战

不依赖 LangChain / LangGraph。使用 Python + OpenAI 兼容 Chat Completions 的 `tools` API。

## 1. 准备环境

需要 Python >= 3.10、`uv`、可用的模型 API Key（模型必须支持 function calling）。

```bash
git clone https://github.com/h173317887/mini-repo-agent.git
cd mini-repo-agent
uv sync
```

## 2. 配置模型

下面为 OpenAI 官方 API 示例：

```bash
export OPENAI_API_KEY='你的密钥'
export OPENAI_MODEL='gpt-4.1-mini'
```

如果使用其他兼容服务商，额外配置其 Chat Completions 兼容地址，并将模型改成该服务商**支持工具调用**的模型 ID：

```bash
export OPENAI_BASE_URL='https://你的服务商/v1'
export OPENAI_MODEL='对应的模型 ID'
```

不要把 API Key 提交到 Git。

## 3. 运行

```bash
uv run python agent.py "先列出文件，再读取 security.py，回答 reader 角色能否删除文档以及原因。"
```

观察日志：
- `第 N 轮`：Harness 调用模型
- `[Action]`：模型选择工具及参数
- `[Observation]`：Harness 执行工具并返回结果
- `[最终回答]`：模型无工具调用时返回的最终文字

模型行为具有概率性，不保证每次都恰好调用相同数量的工具。

## 4. 三个实验

1. 正常运行，记录每一轮动作和观察。
2. 删除 `messages.append({"role": "tool", ...})` **不建议直接这样改**，因为会破坏协议；改为保留 tool 消息但令它的 `content` 为固定空字符串，观察模型表现。实验后恢复。
3. 暂时在 API 请求中移除 `tools=TOOL_SCHEMAS`，观察模型如何回答。实验后恢复。

第 2、3 个实验的输出不能被当作正确结果，只是观察模型如何依赖上下文。

## 安全边界

- 只读 `workspace/` 目录里的普通文本文件，拒绝路径越界、隐藏文件和其他后缀。
- `TOOL_HANDLERS` 是工具白名单。模型请求未知工具也不会执行。
- 不提供写文件、shell、联网能力。
- 这是教学工程，不是生产环境沙盒。正式产品应使用更强的隔离和身份授权机制。
