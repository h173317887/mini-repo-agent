# W6 学习重点：BackendProtocol + FilesystemMiddleware

> 目标：把文件访问从 Agent Tools 中抽离，形成**可替换的 Backend + 统一的工具入口**。参照[18 周计划 W6](./mini-deep-agents-18周开发计划.md)，遵守[每周开发约束](./每周开发约束.md)：先读官方源码，再动手实现最小子集。

## 一、核心架构

```text
Agent / LangGraph
  ↓ 调用工具
FilesystemMiddleware   ← 注册 Tools、校验权限、格式化结果
  ↓
BackendProtocol        ← 定义文件操作与返回值契约
  ↓
FilesystemBackend      ← 实际读取受限的 workspace/
  ↑
ReadResult 等结构化结果 → ToolMessage → Agent
```

**关键问题**：为什么不直接注册 `read_file` 函数？因为文件存储实现和 Agent 工具接口需要解耦；未来换 Backend，不应重写 Agent 的工具逻辑。

## 二、重点掌握（按优先级）

| 优先级 | 知识点 | 要真正弄懂什么 |
| --- | --- | --- |
| P0 | **BackendProtocol** | `abc.ABC`、接口契约、多态、依赖倒置；重点理解 `ls/read/grep/glob` |
| P0 | **FilesystemMiddleware** | 如何通过 `self.tools` 向 Agent 注册工具，调用 Backend，并返回 `ToolMessage` |
| P0 | **结构化结果** | Backend 返回 `ReadResult` 等数据，Middleware 负责转换消息；`offset` 从 0 开始，展示行号从 1 开始 |
| P1 | **文件安全** | `Path.resolve()`、`relative_to()`、越界路径、隐藏文件、后缀限制、符号链接；路径限制不等于沙盒 |
| P1 | **文件定位能力** | `ls` 列目录、`glob` 找路径、`grep` 找内容、`read(offset, limit)` 分段读取 |

## 三、W6 动手任务

- [ ] 对照官方接口，定义只读 Backend 所需的最小方法及结果类型。
- [ ] 将现有 `_tools.py` 的路径校验、列文件、读文件逻辑迁入 `FilesystemBackend`。
- [ ] 实现最小 `FilesystemMiddleware`，由它注册文件 Tools；不再由正式入口重复注册旧文件工具。
- [ ] 增加**代码搜索或按行读取**能力，能够定位未知文件里的函数。
- [ ] 完成安全边界测试，并准备 4–5 条带预期路径/行号证据的 Agent 评估任务。

**验收**：Agent 能在 `workspace/` 内查找、读取并引用正确文件和行号；越界、隐藏文件及非法路径被拒绝；旧版与新版回归测试不受影响。

**本周不做**：`write/edit/delete/execute`、远程存储、生产级沙盒、重写 LangGraph Runtime，以及 W7 的上下文压缩。

## 四、官方源码

- [BackendProtocol：接口与结果类型](https://github.com/langchain-ai/deepagents/blob/master/libs/deepagents/deepagents/backends/protocol.py)
- [FilesystemBackend：磁盘操作和路径处理](https://github.com/langchain-ai/deepagents/blob/master/libs/deepagents/deepagents/backends/filesystem.py)
- [FilesystemMiddleware：工具注册与结果转换](https://github.com/langchain-ai/deepagents/blob/master/libs/deepagents/deepagents/middleware/filesystem.py)

**最终要能回答**：为什么需要 Backend 与 Middleware 两层？为什么 Backend 不直接返回 `ToolMessage`？换一种存储方式时，哪些代码无需修改？
