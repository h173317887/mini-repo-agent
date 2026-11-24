# W6 学习重点：BackendProtocol + FilesystemMiddleware

> 对应 [18 周开发计划 W6](./mini-deep-agents-18周开发计划.md)（12/07–12/13）。本文件记录**必须理解的架构、源码入口、动手任务与验收标准**，不是提前实现 W6 的代码。
>
> 遵守 [每周开发约束](./每周开发约束.md)：**源码决定架构，学习决定实现深度，周计划只决定本周的功能范围**。每一小步按「官方源码 → 为什么这样设计 → 职责与调用链 → 最小实现 → 验证」推进。

## 1. W6 要解决的根本问题

**W5 解决 Agent 如何运行；W6 解决 Agent 如何访问外部文件环境，并在不修改 Agent 决策逻辑的情况下更换环境实现。**

当前 `mini_repo_agent/_tools.py` 把路径校验、目录枚举、文件读取放在同一个工具实现模块；`mini_repo_agent/langchain_tools.py` 再包装成模型可见的 LangChain Tools。能工作，但**具体文件系统实现与 Agent 的工具暴露层仍然耦合**。

W6 的目标调用链：

```text
agent.py
  → graph.create_deep_agent()
  → LangChain create_agent() / LangGraph Runtime
  → FilesystemMiddleware（向 Agent 注册工具）
      ├─ 模型可见：ls / read_file / grep / glob（只启用本周实现的子集）
      ├─ 输入校验 / 权限限制 / 结果格式化
      ↓
    BackendProtocol（定义统一文件访问接口与结果契约）
      ↓
    FilesystemBackend（限定 workspace/ 的实际文件操作）
      ↓
    操作结果 LsResult / ReadResult / GrepResult / GlobResult
      ↑
    FilesystemMiddleware → ToolMessage → Agent 下一轮决策
```

**区分三类职责：**

| 模块 | 回答的问题 | 不该承担什么 |
| --- | --- | --- |
| `BackendProtocol` | 文件能力的**接口与返回契约**是什么？ | 不负责提示词、模型消息、工具注册 |
| `FilesystemBackend` | 文件存在哪里、如何安全读取/搜索？ | 不决定模型能看到哪些工具，不构造 `ToolMessage` |
| `FilesystemMiddleware` | 如何把文件能力转换为可调用 Tools，校验权限并处理结果？ | 不直接耦合 `Path.read_text()` 等磁盘细节 |
| `LangGraph Runtime` | 如何调度模型调用与工具调用？ | W6 不重写 State / Checkpointer / ReAct 循环 |

**必须能回答：为什么不直接把 `read_file()` 等函数注册到 `create_agent(tools=...)`？**
因为直接注册仅适合能力较少、固定的场景；Backend 与 Middleware 分离后，同一套 Agent 工具接口能够对接本地文件、状态存储或远程存储，且权限、结果格式化集中在 Middleware。**不是直接注册 Tools 有错，而是 Deep Agents 需要可替换性与能力治理。**

## 2. 必须掌握的五个知识点（按优先级）

### P0① BackendProtocol：抽象接口与依赖倒置

源码：[backends/protocol.py](https://github.com/langchain-ai/deepagents/blob/master/libs/deepagents/deepagents/backends/protocol.py)

- **理解动机**：如果 Agent 直接调用本地磁盘 API，换成远程存储时需要改写工具逻辑；依赖统一 Backend 契约可避免这一点。
- **Python 基础**：`abc.ABC`、继承、方法覆盖、多态、类型注解；官方类名虽然是 `BackendProtocol`，源码使用的是 `abc.ABC`，不是直接定义一个 `typing.Protocol`。
- **接口最小子集**：重点阅读 `ls(path)`、`read(file_path, offset=0, limit=2000)`、`grep(pattern, path=None, glob=None, *, max_count=None)`、`glob(pattern, path=None)`。
- **输出契约**：能说清 `LsResult`、`ReadResult`、`GrepResult`、`GlobResult` 的用途；Backend 的结果不是 `ToolMessage`。
- **会解释**：为何 `StateBackend`、`StoreBackend` 可以没有 Shell，`grep` / `glob` 不能被简单当作执行系统命令的别名。

**掌握标准**：不参考具体磁盘实现，也能说明给 Backend 换一个实现需要遵守哪些方法、参数和返回约定。

### P0② FilesystemMiddleware：工具暴露与能力治理

源码：[middleware/filesystem.py](https://github.com/langchain-ai/deepagents/blob/master/libs/deepagents/deepagents/middleware/filesystem.py)

- 重点看 `FilesystemMiddleware(AgentMiddleware)`、`__init__()`、`_create_tools()` 以及 `_create_ls_tool()`、`_create_read_file_tool()`、`_create_grep_tool()`、`_create_glob_tool()`。
- 官方在 Middleware 内生成并注册 `self.tools`，通过 LangChain 的 `create_agent(middleware=[...])` 自动并入 Agent 工具集合；**不是在 `agent.py` 中重复维护两份文件工具清单**。
- 理解 `ToolRuntime`、`tool_call_id`、`ToolMessage(status="success" | "error")` 的职责；参数校验、权限检查、结果格式化应位于明确的边界。
- 官方的 `FilesystemMiddleware` 支持读写、删除、执行等更多能力。本项目 W6 仍是**只读 Agent**，只暴露实际实现的只读工具，其他能力不注册、不提供虚假空壳。

**掌握标准**：能跟踪一次模型调用 `read_file` 的完整链路，指出哪一层定义工具、哪一层读取文件、哪一层创建发给模型的结果。

### P0③ 结构化结果：`ReadResult` 与 `ToolMessage` 分离

源码：[backends/protocol.py — ReadResult](https://github.com/langchain-ai/deepagents/blob/master/libs/deepagents/deepagents/backends/protocol.py)

- `ReadResult` 是 Backend 的**数据结果**，包含 `file_data`、`error` 及可选的 `total_lines`、`start_line`、`end_line`、`next_offset`。
- `ToolMessage` 是 LangGraph 传给 Agent 的**对话/工具执行结果**，与当前 `tool_call_id` 配对。它不是 Backend 的返回类型。
- 行号格式化属于 Middleware；Backend 应返回原始文本及准确的行位置元信息。
- 区分三类情形：读取成功、文件不存在、请求了空行区间；不能用空字符串统一表示三者。
- **行号约定要记清**：官方 `read` 的 `offset` 是 **0-based**，`ReadResult.start_line/end_line` 是 **1-based**；`next_offset` 指向下一段的 0-based 起始位置。

**掌握标准**：能设计一次「读取第 21–40 行」的往返，说明 Backend 返回什么、Middleware 如何附行号、最终模型收到什么。

### P1④ 文件路径安全与隔离边界

源码：[backends/filesystem.py](https://github.com/langchain-ai/deepagents/blob/master/libs/deepagents/deepagents/backends/filesystem.py)；对照本项目 `mini_repo_agent/_tools.py` 的 `safe_path()`。

- 掌握 `pathlib.Path` 的 `resolve()`、`relative_to()`、`is_file()`、`is_symlink()`、`read_text()` 及目录遍历的基本用法。
- 必须测试：`..` 路径越界、绝对路径、隐藏文件/隐藏目录、符号链接指向根目录外、非法后缀、文件不存在。
- 明确「**根目录限制 ≠ 操作系统沙盒**」：官方 `FilesystemBackend(root_dir, virtual_mode=True)` 提供虚拟路径语义和路径限制，但不提供进程级隔离。
- 明确路径边界：官方接口以 `/...` 虚拟绝对路径为主；本项目 W2 的 `safe_path()` 接收相对 `workspace/` 的路径。W6 要在 Backend 边界**明确转换与规范化**，不可不经说明地混用。
- 路径检查不能只靠 `startswith()` 字符串比较；需要防御路径规范化和符号链接等情况。

**掌握标准**：正常读取有效，越界/隐藏/符号链接均无法把限制外文件内容返回给 Agent。

### P1⑤ `ls` / `read` / `grep` / `glob`：让 Agent 找到未知代码

- `ls`：列出目录内容。
- `glob`：按路径模式找文件，例如 `**/*.py`；并非按文件内容搜索。
- `grep`：按**字面文本**查找匹配位置，返回文件路径、行号、匹配行；官方该接口默认不是正则表达式搜索。
- `read`：在已知文件后按 `offset` / `limit` 分段读取，用于核实证据，避免一次读取整份超长文件。
- 结果应限制数量/长度、保留必要的行号与分页信息，避免无界搜索消耗上下文。

**掌握标准**：模型不知道函数在哪个文件时，也能先搜索，再定位文件及对应代码行，最后给出有依据的回答。

> 本周计划要求**至少实现一项最小代码搜索或按行读取能力**。四类能力都要理解接口与区别，但不以一次性复刻官方所有搜索特性为目标；其余按学习进度增量完成。

## 3. W6 需要掌握的最小接口（源码对照用）

以下是官方接口的**选摘签名**，不是可直接实例化的完整实现：

```python
class BackendProtocol:
    def ls(self, path: str) -> LsResult: ...

    def read(
        self, file_path: str, offset: int = 0, limit: int = 2000
    ) -> ReadResult: ...

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
        *,
        max_count: int | None = None,
    ) -> GrepResult: ...

    def glob(
        self, pattern: str, path: str | None = None
    ) -> GlobResult: ...
```

其中 `ReadResult`、`GrepMatch`、`FileInfo` 等具体数据结构以官方 `protocol.py` 为准。W6 应保持官方**命名、参数语义与职责**，在实现范围内简化返回数据，不自创另一套不兼容的正式接口。

## 4. 按依赖关系推进的实现顺序

- [ ] **源码对齐**：追踪 `graph.create_deep_agent → FilesystemMiddleware.tools → BackendProtocol → FilesystemBackend`；整理官方接口与当前项目的差异。
- [ ] **Backend 最小契约**：明确 `ls` / `read` 及需要的结果类型，写出接口层；避免创建无用途的写入、执行等抽象。
- [ ] **本地文件实现**：迁移 `_tools.py` 的只读文件和路径安全逻辑至受限 `FilesystemBackend`；底层不构造 `ToolMessage`。
- [ ] **Middleware 工具注册**：实现最小 `FilesystemMiddleware`，由 Middleware 暴露工具并调用 Backend；`graph.py` 保持组装职责，正式入口不继续重复注册旧 `langchain_tools.py` 文件工具。
- [ ] **补最小定位能力**：按周计划实现代码搜索或按行读取（最好逐步覆盖 `grep` 和分段 `read`）；保证路径/行号证据准确。
- [ ] **测试和评估**：先测 Backend 契约、安全边界，再测真实 LangGraph 的工具消息配对、多文件分析；建立 4–5 条可复位的 Agent 评估用例。

## 5. 测试清单与 W6 验收

### Backend / Middleware 确定性测试

- [ ] 正常 `ls` 和 `read`，返回符合接口契约的数据。
- [ ] 文件不存在：错误不伪装成正常文件内容，Agent 能收到恰当的工具错误。
- [ ] 路径越界/隐藏文件/非法后缀/越界符号链接：无敏感文件内容泄漏。
- [ ] 若实现分段读取：offset / limit、首末行、空区间与分页一致。
- [ ] 若实现搜索：返回准确路径与行号，结果数有上限。
- [ ] Middleware 注册的工具实际调用 Backend；最终 `ToolMessage.tool_call_id` 与请求一致。
- [ ] 既有 W5 和 `legacy/` 测试仍通过。

### 4–5 条 Agent 评估任务（准备固定 workspace + 预期证据）

| 用例 | 任务 | 应验证的证据 |
| --- | --- | --- |
| E1 | 在未知文件名情况下定位 `can_execute` 定义 | 正确文件路径与函数所在行 |
| E2 | 比较 `security.py` 和 `README.md` 的权限描述 | 两个文件的对应证据及一致/不一致结论 |
| E3 | 寻找指定的不存在函数 | 明确说明未找到，不编造路径和源码 |
| E4 | 请求读取 `../.env` 或隐藏文件 | 访问被拒绝，不泄漏文件内容 |
| E5（可选） | 读取较长文件中后半部分的指定逻辑 | 正确定位行区间、无跳行或凭空引用 |

> 注意：这些是**待建立的测试规范**。需要在固定的测试仓库中配置文件和预期行号，不能直接把当前 workspace 的动态行号当成不变真值。既有 Mock 测试检查机制，Agent 评估则检查任务完成质量及证据准确性。

### 本周完成标准

最终达到：模型通过 `FilesystemMiddleware` 调用限定的 `FilesystemBackend`，能够在**只读**边界内定位未知文件中的代码并提供可验证的路径/行号；底层文件逻辑不再直接写死在模型可见的工具函数里；测试和用例能重复执行。

## 6. W6 暂不深入的内容

不提前实现 `write` / `edit` / `delete` / `execute`、生产级沙盒、远程 Backend、通用持久化方案；不重新实现 LangGraph State/Checkpointer；不提前展开 W7 的 Summarization、Token Budget 与大型结果淘汰机制。

## 7. 最终自检问题

1. 为什么 `BackendProtocol` 不是另一个 Tool 接口？
2. 为什么 Backend 返回 `ReadResult`，而不是 `ToolMessage`？
3. 为什么文件工具应由 `FilesystemMiddleware.tools` 注册，而不是在 CLI 手动拼列表？
4. 为什么 `glob` 和 `grep` 不能互换？怎样保证搜索行号可验证？
5. 为什么 `Path.resolve()`、`root_dir` 或 `virtual_mode` 都不等于真正的沙盒？
6. 如果未来将本地文件 Backend 换为远程存储，Agent、Middleware、Backend 各需要修改什么？

能独立回答上述问题，并通过第五节的实际验证，才算掌握 W6 的核心内容。
