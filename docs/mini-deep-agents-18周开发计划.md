# Mini Deep Agents：项目提示词与 18 周开发计划（含 Agent 评估）

> 计划周期：**2026-11-02 ～ 2027-03-07** ｜ 每周 **24 小时** ｜ 共 **18 周 / 432 小时**  
> 最终交付：**Mini Deep Agents V1.0**——架构清晰、可运行、可评估的轻量级 Agent Harness，附一个代码仓库分析 / 受控修改 Agent、20 条任务的评估集与评估报告。  
> 版本定位：**学习性工程实现，不等同于完整复刻官方 Deep Agents，也不承诺生产级沙盒与分布式可靠性。**
> 技术路线：**W1–W4 手写最小 Harness → W5 迁移 LangChain / LangGraph → W6–W18 基于官方运行时扩展 Deep Agents 风格能力**。

---

## 一、新窗口启动提示词（复制本节即可）

我是一名前端工程师，正在学习 Python 和李博杰《深入理解 AI Agent 架构》，已学完第一、二章。现在要以现有项目 [`mini-repo-agent`](https://github.com/h173317887/mini-repo-agent) 为起点，用 **18 周 × 每周 24 小时**，循序渐进地实现一个轻量级 **Deep Agents 风格的 Agent Harness**。

**学习方式：**

- **主要参照**：[Deep Agents 源码](https://github.com/langchain-ai/deepagents)及其 [ARCHITECTURE.md](https://github.com/langchain-ai/deepagents/blob/main/libs/ARCHITECTURE.md)；**理论依据**：[李博杰的书](https://github.com/bojieli/ai-agent-book)；Codex 仅作 Runtime / 执行安全的辅助参考。
- **不要让我自行发明架构，也不要直接使用 `deepagents.create_deep_agent()` 高级 API 拼装结果。**每一步先核对官方 Deep Agents 和它依赖的 LangChain / LangGraph 源码，再实现简化版本或官方扩展点，解释取舍。
- **W1–W4 手写最小 ReAct Runtime / Middleware**，理解底层机制；**W5 必须迁移到 `langchain.agents.create_agent()`（底层由 LangGraph 执行）**；W6 起基于官方 Runtime 构建自定义 Middleware / Backend / Skills / Subagents。手写 Runtime 此后只用于教学对照和回归，不再作为正式入口。
- **尽可能采用 Deep Agents 官方同名模块和目录职责**（如 `graph.py`、`middleware/summarization.py`、`backends/protocol.py`），但不要提前创建无用抽象。
- 以真实工程功能为主，不再做大量孤立实验。每次只推进**一个小步骤**：源码与动机 → 数据流 / 职责 → 最小改动 → 我动手实现 → 运行验收。重要的 Python 语法请顺带讲解。
- 指导代码前，**先通过 GitHub 连接器查看我的仓库最新内容**，不要根据旧对话臆测；除非我要求，不要一次性替我写完所有代码。

**项目当前基础：** Python + uv + OpenAI SDK 调用 DeepSeek；已有 ReAct 循环、`list_files` / `read_file`、工具定义与分发、路径安全检查、Token 统计，以及“压缩同一文件更早的重复 Observation、保留最近一次读取结果”的基础压缩策略。

**最终目标：** 实现 Runtime、Tools、Middleware、Backend、Context 管理、Planning / State、Skills、Subagents、Checkpoint / Interrupt、人工审批与 CLI；让 Agent 在受控工作区执行代码分析与经授权的修改，并建设可重复运行的 **Agent 评估集、自动评估器与回归报告**（对齐李博杰第七章）。

**当前已完成 W1–W2，正在学习 W3。**请每次从 GitHub 最新代码及本计划的当前周出发，按“源码机制 → 职责边界 → 最小实现 → 测试”推进；不要退回 W1，也不要一次性写完整周代码。

---

## 二、开发原则与完成标准

### 项目定位

- **主线：Deep Agents 架构**，不是重新设计一套独立的 Agent 范式。
- **底座分阶段**：W1–W4 手写最小 Runtime / Middleware 用于理解；W5 切换 LangChain `create_agent()` + LangGraph；此后只扩展官方 Agent Runtime，不独立维护第二套正式执行框架。
- **对照：同名、同职责优先**。W3–W4 优先模拟官方 `AgentMiddleware` 的 `state` / `runtime` / 状态更新语义；W5 起使用官方接口，避免重写已有能力。
- **每一周都要有可运行交付**；测试伴随开发，不堆到最后一周。
- **评估贯穿开发**：单元/集成测试验证代码机制；Agent Evaluation 验证真实任务是否成功、证据是否可靠、执行是否安全、成本是否可接受。

### 迁移策略与完成门槛

1. **W1–W4（机制学习）**：理解 ReAct、Tool、Middleware；手写实现不追求 LangGraph 的状态图、异步、持久化等完整语义。
2. **W5（一次正式迁移）**：固定依赖版本，把模型、工具、Middleware、Agent 入口接入 LangChain；由底层 LangGraph 执行状态图；保留手写 `runtime.py` 在教学/对照测试中，不再被正式 CLI 使用。优先迁移模型和工具、回归执行链，再迁移日志与 trace；不要求两个实现的内部事件格式逐字一致。
3. **W6–W18（框架扩展）**：Backend、Context、Skills、Subagents 等优先写成 LangChain / Deep Agents 风格的可组合 Middleware 或独立能力。Checkpoint、Interrupt、State 使用 LangGraph 现有机制，不再手造可替代的通用基础设施。
4. **禁止两种极端**：既不直接调用 `deepagents.create_deep_agent()` 跳过学习，也不在迁移后重复实现一套 LangGraph。只有官方机制无法满足具体需求时，才增加最小适配代码。
5. **迁移验收**：与 W2–W4 相同的 Mock 场景（工具成功/失败、最终回答、中间件顺序、日志追踪）能通过；CLI 正式运行新的 `create_agent()` 路径；对照说明行为差异。迁移阻塞时先修复 W5，不把半迁移的设计滚到 W6。

### 每周固定 24 小时

| 工作 | 时间 |
|---|---:|
| 阅读对应官方源码、梳理调用链 | 4h |
| 亲手实现、重构和集成 | 14h |
| 自动化测试与调试 | 4h |
| README、设计笔记、Git 提交 | 2h |
| **合计** | **24h** |

### 统一验收要求

每周结束前检查五项：**代码正常运行**、**本周目标功能能演示**、**关键行为有回归测试**、**关键执行轨迹可记录以供后续评估**、**能解释本地实现与 Deep Agents 官方的相同点 / 不同点**。

若一周任务未通过验收，先解决阻塞，再调整下周范围，不为赶日期跳过核心依赖。

---

## 三、18 周详细计划

### 阶段 A：Runtime 与工具基础（W1–W2，共 48h）

#### W1｜11/02–11/08｜拆分 Runtime，不改变 Agent 行为

**源码参照：** Deep Agents `graph.py`、官方 `ARCHITECTURE.md`（重点理解 `create_deep_agent()` 与底层 `create_agent()` 的关系）。

**任务：**
1. 读当前 `agent.py`，分别标注模型调用、ReAct 循环、工具执行、Context 压缩、CLI 入口。
2. 建立 `mini_repo_agent/runtime.py`，抽离循环逻辑；建立 `mini_repo_agent/graph.py` 负责最小组装。
3. 顶层 `agent.py` 仅负责解析命令行参数并启动 Agent；暂不改现有工具与压缩算法。
4. 为原有多步文件读取任务保留一个可重复执行的冒烟测试。

**交付 / 验收：** `uv run python agent.py "读取 security.py，解释 can_execute"` 可正常运行；入口、组装、循环职责清楚；无回归。

#### W2｜11/09–11/15｜模型适配与 Tool Registry

**源码参照：** Deep Agents `_models.py`、`_tools.py`；LangChain 的模型与 Tool 抽象作为接口对照，不直接引入。

**任务：**
1. 在 `_models.py` 封装 DeepSeek 调用、模型配置和 usage 读取；消除 Runtime 对固定模型配置的硬编码。
2. 在 `_tools.py` 统一保存工具 schema、handler 注册和分发逻辑。
3. 规范工具返回结果和失败行为，保证一次调用有可辨识的 call ID、工具名、参数与结果。
4. 使用假模型响应 / Mock 工具测试“正常返回、未知工具、无效参数、模型结束”路径；记录 `task_id`、模型、调用轨迹与 usage，为后续 Agent 评估提供最小观测字段。

**交付 / 验收：** 替换模型配置无需修改核心循环；工具注册与执行由独立模块管理。

### 阶段 B：Middleware 架构（W3–W4，共 48h）

#### W3｜11/16–11/22｜最小 Middleware 生命周期

**源码参照：** 官方 `graph.py` 的 middleware 组装、LangChain Agent Middleware 接口。

**任务：**
1. 对照 Deep Agents `graph.py` 的 Middleware 列表组装以及 LangChain `AgentMiddleware` 源码，区分 Tool、Middleware 和 Runtime 的职责。
2. 手写最小 `AgentState` / 运行时上下文与 `before_model(state, runtime)`、`after_model(state, runtime)`，允许返回状态更新（或 `None`）；不把 `after_model` 错误设计为直接接收 ModelResponse。
3. 实现中间件列表与明确的钩子执行次序，把 Context / Token 日志迁移为可独立启停的 Middleware。
4. Mock 验证每轮模型调用的钩子顺序、无工具时的执行、状态更新与消息不被意外就地修改。

**交付 / 验收：** 新增/移除日志 Middleware 不需要加入专用的 Runtime `if` 分支；明确说明与官方 LangChain 状态节点钩子的差异。

#### W4｜11/23–11/29｜工具包装、执行链和失败语义

**源码参照：** LangChain Middleware 的 `wrap_model_call`、`wrap_tool_call` 思想；Deep Agents `patch_tool_calls.py`。

**任务：**
1. 参照 `wrap_model_call(request, handler)` / `wrap_tool_call(request, handler)` 的装饰调用链思想，手写最小模型及工具包装能力，弄清执行顺序（先注册的包装层在外层）。
2. 对模型请求、工具调用、异常及取消定义最小日志与失败语义；不提前实现 LangGraph 的异步图、Checkpoint 或 Interrupt。
3. 将“不合法工具调用”的拒绝逻辑放在工具边界（或包装层），不依赖 Prompt；保持 tool_call_id 与结果配对。
4. Mock 覆盖两个以上 Middleware 的顺序、异常传播、结果配对；保存固定模型/工具轨迹，为 W5 的迁移对照提供基线。

**交付 / 验收：** 两个以上 Middleware 可组合，执行顺序可预测；主循环不含各类特性专用的 `if` 分支。

**里程碑 M1：** 完成手写最小 Harness；行为测试与执行轨迹构成 W5 迁移基线，手写实现自此停止扩张。

### 阶段 C：迁移 LangChain / LangGraph 与文件能力（W5–W6，共 48h）

#### W5｜11/30–12/06｜正式迁移：LangChain create_agent + LangGraph Runtime

**源码参照：** Deep Agents `graph.py` 的 `create_deep_agent() → langchain.agents.create_agent()`；LangChain `create_agent` / `AgentMiddleware`；LangGraph 的状态图执行机制。

**任务：**
1. 固定 `langchain`、`langchain-openai`、`langgraph` 等版本；用官方聊天模型封装连接 DeepSeek（例如配置 `ChatOpenAI` 的 `base_url`）；确认模型、Tool Calls 和 usage 的语义。
2. 将 `TOOL_SCHEMAS` / handler 映射为 LangChain Tools，保留现有只读工作区限制；在 `graph.py` 使用 `create_agent(model, tools=..., middleware=...)` 组装正式 Agent，不直接调用 `deepagents.create_deep_agent()`。
3. 将 W3–W4 中有价值的日志/拦截逻辑迁移到真正的 `AgentMiddleware`；用框架提供的 State / Runtime 结构替换教学版的自定义状态约定。
4. 迁移 CLI 入口并跑同一组 Mock 回归和真实只读任务，核查工具成功/未知工具/坏参数、结束条件、Middleware 次序及可观察的调用轨迹；记录与手写版的行为差异。

**交付 / 验收：** 正式入口执行 LangChain Agent（底层 LangGraph）；回归通过且能分析执行图节点、模型调用和 Tool 节点。原 `runtime.py` 仅作为教学对照实现，可移入 `legacy/` 或保持隔离，但不可在正式运行路径中继续调用。

#### W6｜12/07–12/13｜Backend Protocol + FilesystemMiddleware

**源码参照：** Deep Agents `backends/protocol.py`、`backends/filesystem.py` 与 `middleware/filesystem.py`。

**任务：**
1. 参照官方 `BackendProtocol` 提取当前只读仓库分析真正需要的最小接口，用本地工作区实现；不重复封装 LangGraph 的 State / Checkpointer。
2. 将 W2 原有文件读取、列表与路径安全逻辑迁移到 Backend；通过 `FilesystemMiddleware` 提供模型可见 Tools，明确“存储能力”和“Agent 工具接口”的分层。
3. 增加最小代码搜索或按行读取能力，处理不存在文件、隐藏文件、越界路径与符号链接等边界；保持原有安全限制。
4. 在固定的小型仓库中完成可复位的多文件分析任务，启动首批 4–5 条带预期证据的 Agent 评估用例。

**交付 / 验收：** 正式 Agent 能通过 Middleware 访问受限 Backend，定位未知文件名的代码问题并返回可验证路径/行号；不再在工具层直接硬编码文件系统实现。

### 阶段 D：Context Engineering（W7–W9，共 72h）

#### W7｜12/14–12/20｜官方 Middleware 上的 Token Budget 与基础 Summarization

**源码参照：** `middleware/summarization.py`、消息历史管理。

**任务：**
1. 在官方 Agent Runtime 中编写 SummarizationMiddleware，将旧的重复 Observation 压缩作为对照基线；遵守 LangChain 消息/状态更新规则，不直接就地修改状态消息。
2. 增加输入 Token 估算 / API usage 记录、预算阈值与触发规则。
3. 设计工具结果过长时的可控截断或外存策略入口，避免失去整个工具响应。
4. 测试多轮请求中消息协议完整、不会出现“有工具调用但缺工具结果”。

**交付 / 验收：** Context 管理由独立 LangChain Middleware 负责；预算触发后 Agent 仍能保持合法消息协议并继续执行。

#### W8｜12/21–12/27｜Task-aware Compression

**源码参照：** 官方 SummarizationMiddleware；李博杰第二章压缩设计原则。

**任务：**
1. 在自研 SummarizationMiddleware 上压缩时显式提供当前任务、关键约束和证据来源，不复制一份独立 Context Runtime。
2. 保存必要的决策、失败原因、精确字面值与可回读路径；允许需要时重新读取。
3. 将摘要接入真实多文件分析任务，不再单独做孤立 `task_aware_test.py`。
4. 测试“压缩后仍能报告精确标记、比较文件一致性、不产生交替重读循环”。

**交付 / 验收：** 在可控长任务中压缩成功且关键答案准确；失败时能识别丢失信息并恢复。

#### W9｜12/28–01/03｜历史外存与缓存友好的上下文布局

**源码参照：** Summarization、Filesystem 与 Prompt Caching 相关中间件。

**任务：**
1. 将大体积工具结果按需存到 Backend，消息中保留可检索位置及关键摘要。
2. 优化静态规则 / 动态状态的位置，尽量维持稳定请求前缀。
3. 记录每轮输入 Token、摘要调用 Token、重复读取次数；支持开关压缩做配对对照，并将相同任务的成功结果与消耗一同保存。
4. 说明“节省输入长度”和“节省缓存后实际成本”并不等价。

**交付 / 验收：** 长任务 Context 增长有边界；结果可回查；总成本和缓存影响有基本可观测性。

**里程碑 M2：** 第二章的核心上下文工程正式融入 Harness。

### 阶段 E：Planning、State、Skills（W10–W11，共 48h）

#### W10｜01/04–01/10｜TODO 与运行状态

**源码参照：** Deep Agents 的工具 / Middleware 组装，及其规划工具行为；注意官方具体职责不一定落在独立 `planning.py`。

**任务：**
1. 扩展 LangGraph Agent State 的业务字段（TODO、工具调用次数、当前进度），消息沿用官方 State / reducer 语义，不重新实现消息状态机。
2. 提供创建 / 更新 TODO 的工具，严格校验状态流转。
3. 将关键状态以模型易读的方式注入 Context，尽量不重写稳定前缀。
4. 使用多步骤仓库任务测试状态变化、重复调用与完成判定；为评估集补充任务完成状态/错误退出场景。

**交付 / 验收：** Agent 能建立与更新 TODO；状态由代码维护，不能仅靠模型口头声明任务完成。

#### W11｜01/11–01/17｜Skills 渐进式加载

**源码参照：** `middleware/skills.py`、`middleware/_skill_tools.py`。

**任务：**
1. 实现 Skill 元信息索引，启动时只展示名称、描述等必要信息。
2. 支持按需读取 `SKILL.md` 正文和引用文件。
3. 编写首个 `code-review/SKILL.md`，指导代码分析、证据引用与风险说明。
4. 验证未选中 Skill 不加载全文，选中后能遵循规则且不获得额外越权能力。

**交付 / 验收：** Agent 能对任务匹配并按需加载 Skill，Context 不因 Skill 数量增长而线性加载所有正文。

### 阶段 F：Subagents（W12–W13，共 48h）

#### W12｜01/18–01/24｜最小 SubAgentMiddleware

**源码参照：** `middleware/subagents.py`。

**任务：**
1. 提供 `task` 委派工具，明确主 Agent 与子 Agent 的调用关系。
2. 子 Agent 复用 LangChain/LangGraph Agent 创建与执行机制，但拥有独立 State / 消息历史及工具配置。
3. 委派任务必须有明确的目标、约束、上下文输入和输出格式。
4. 测试主上下文不会直接混入子 Agent 的全部中间 Observation。

**交付 / 验收：** 主 Agent 可委派一次代码检索，子 Agent 返回简短、带证据的结果。

#### W13｜01/25–01/31｜子 Agent 配置与隔离

**源码参照：** SubAgentMiddleware 及官方子 Agent 配置方式。

**任务：**
1. 支持不同子 Agent 的 Prompt、工具权限、最大轮数和独立 Context。
2. 在主 Agent 中整合多个子任务结果并核查来源。
3. 处理子任务失败、超时 / 步数耗尽、结果格式错误等边界。
4. 实现“主 Agent 分析 → 子 Agent 搜索 → 主 Agent 汇总”的端到端任务；为评估集补充 2 条子 Agent 协作任务。

**交付 / 验收：** 至少两类子任务可被委派，发生子任务失败也不会让整个系统失控。

**里程碑 M3：** Planning + Skills + Subagents 完成贯通。

### 阶段 G：持久化、恢复和权限（W14–W16，共 72h）

#### W14｜02/01–02/07｜基于 LangGraph Checkpointer 的持久化恢复

**源码参照：** LangGraph Checkpointer、线程状态与恢复机制；Deep Agents `graph.py` 对 `checkpointer` 的传递方式。

**任务：**
1. 确认 Agent State 中哪些信息进入 Checkpoint，哪些是临时状态；明确 `thread_id`、checkpoint 和业务 `task_id` 的区别。
2. 接入 LangGraph 现有持久化 Checkpointer（如 SQLite 对应实现），不再手写通用原子保存/状态恢复引擎。
3. 让同一 thread 能保存、读取并恢复消息和 TODO，验证进程重新启动后的状态一致性。
4. 设计恢复后工具副作用的测试，标记哪些操作必须有幂等或人工确认保障，避免把 Checkpoint 误当事务回滚。

**交付 / 验收：** Agent 使用 LangGraph Checkpointer 支持指定 thread 的恢复，业务状态可追踪，文档解释持久化边界及重复执行风险。

#### W15｜02/08–02/14｜基于 LangGraph Interrupt 的 Human-in-the-loop

**源码参照：** LangGraph Interrupt / Command、LangChain `HumanInTheLoopMiddleware` 与 Deep Agents 的工具权限配置。

**任务：**
1. 为需要审批的操作配置中断点，保存待审批的工具名、参数、call ID 和 thread 关联；未批准前不得执行。
2. 使用 LangGraph Interrupt 与恢复命令实现 CLI 的批准/拒绝（参数修改可选），不自己另写一套暂停/继续调度器。
3. 验证“审批时看到的请求”与“恢复后实际执行的请求”一致，防止过期或重复批准导致越权操作。
4. 用 Mock 和持久化 thread 测试拒绝、恢复、重启后继续与副作用防重，补充安全评估任务。

**交付 / 验收：** 正式运行路径使用 LangGraph 的暂停/恢复机制，未经批准的实际写入/执行次数为 0；审批与状态恢复可验证。

#### W16｜02/15–02/21｜受控文件编辑与基础记忆

**源码参照：** `middleware/permissions.py`、`middleware/memory.py`、`backends/store.py`。

**任务：**
1. 在现有 Backend / FilesystemMiddleware 上增加受控写入 / 编辑工具，所有目标限制在工作区并接入 W15 的审批链，默认拒绝未批准操作。
2. 加入操作前后 diff、失败回滚或备份恢复的最小机制。
3. 实现简单持久化记忆存储与按需读取，区分跨任务记忆和单次任务 Context。
4. 测试路径安全、未经批准写入、记忆错误注入和文件回滚；补齐编辑/测试类评估任务，并为正式评估固定测试仓库版本。

**交付 / 验收：** Agent 能在明确授权下修改文件；跨会话信息能按需检索，不等于每轮全部注入。

**里程碑 M4：** 基于 LangGraph 具备状态持久化、暂停恢复与人工审批，扩展层支持受控文件编辑。

### 阶段 H：CLI、Agent 评估与发布（W17–W18，共 48h）

#### W17｜02/22–02/28｜Coding Agent CLI 与评估系统（24h）

**源码参照：** Deep Agents Code 的 CLI 体验；李博杰第七章“评估环境、验证器、自动化评估、失败归因与可观测性”。

**建议时间拆分：** CLI 与安全测试入口 7h；评估任务与验证器 9h；评估执行器/轨迹保存 6h；联调与文档 2h。

**任务：**
1. 增加持续交互式 CLI、执行轨迹查看，以及**限定命令 / 固定测试入口**；不默认开放任意 Shell。
2. 实现 `evals/`：任务定义、可复位的测试仓库、运行器、结果保存（JSON/JSONL）、自动验证器。
3. 完成 **20 条评估任务**：4 条代码定位、4 条多文件分析、3 条长 Context、3 条工具失败与恢复、2 条 Subagents、2 条审批/安全、2 条受控编辑与测试。
4. 优先使用确定性验证：精确值、文件/行号与证据检查、测试退出码、仓库状态或权限事件；开放式回答必要时人工复核，LLM-as-a-Judge 仅作辅助而非唯一真值。
5. 在固定模型版本、任务输入与仓库快照下跑通一次完整评估，输出逐任务通过/失败及可追踪的轨迹。

**交付 / 验收：** CLI 能完成既定端到端流程；20 条评估任务均可启动、可复位、可判定或标注需要人工复核；失败能追溯到具体工具/模型决策环节。

#### W18｜03/01–03/07｜基线对照、失败归因与 V1.0 发布（24h）

**建议时间拆分：** 正式评估与对照 10h；关键失败修复与回归 7h；文档、报告、发布 7h。

**任务：**
1. 在固定配置上执行完整评估；对部分非确定性场景进行多次重复，报告单次通过率及重复运行的稳定性，不用一次成功替代可靠性结论。
2. 汇总主要指标：**任务成功率、证据准确率、未经授权执行次数、工具调用次数、Token / 估算成本、运行耗时、失败类型**。记录样本数和模型/仓库版本。
3. 针对一个真实的架构决策做配对对照（例如：压缩开/关；Subagent 开/关），比较质量与成本。仅在任务条件一致时归因差异。
4. 按“首个错误步骤”做失败归因：任务理解、工具选择、工具结果、上下文、状态、权限、最终结论；先修复最重要的错误并回归评估集。
5. 完成 README、架构图、API/安全边界说明、示例任务与 `evals/report.md`；对照官方 Deep Agents 列出已实现/未实现能力，打 `v1.0` 标签。

**交付 / 验收：** 干净环境能运行 CLI 和评估命令；具有 **20 条任务的逐条结果、汇总指标、失败案例、至少一次可复现的配置对照、可查阅的轨迹**。安全硬约束：**未经批准的写入/执行次数为 0**；任务成功率目标可先设为 **≥80%（20 条中至少 16 条）**，若未达到则记录阻塞问题、修复与复测，不虚报通过。

**里程碑 M5：Mini Deep Agents V1.0 + Agent Evaluation Report。**

---

## 四、Agent 评估体系（从 W2 开始积累，而非 W18 临时补）

评估设计对齐李博杰 [第七章：Agent 的评估](https://github.com/bojieli/ai-agent-book/blob/main/book/chapter7.md)，但只落实当前 Coding Agent 的工程范围，不试图复刻所有通用 Benchmark。

### 1. 评估与普通测试的区别

| 层次 | 测什么 | 例子 | 主要阶段 |
|---|---|---|---|
| 单元 / 集成测试 | 机制实现是否符合预期 | Middleware 顺序、工具 call ID、路径拒绝、Checkpoint 恢复 | W1–W18 全程 |
| Agent 任务评估 | 用户任务是否真的完成 | 找到正确函数、分析跨文件逻辑、修复代码且测试通过 | W6 建集，W17–W18 集中 |
| 安全与可靠性评估 | 不应发生的事有没有发生，结果是否稳定 | 未授权修改为 0、失败工具能否恢复、同一任务重复运行 | W13–W18 |

### 2. 20 条任务的评估集

| 类型 | 数量 | 主要验证方式 |
|---|---:|---|
| 代码定位与证据引用 | 4 | 精确文件路径、函数、行号和证据存在性 |
| 多文件分析与一致性 | 4 | 预先核对的关键事实 / 文档矛盾清单 |
| 长上下文与压缩恢复 | 3 | 压缩后关键事实仍正确、无无效读取循环 |
| 工具失败与自我恢复 | 3 | 工具模拟错误后合理重试或停止，最终状态正确 |
| Subagents 委派与隔离 | 2 | 子任务结果可验证，主上下文不泄漏中间工具结果 |
| 审批与权限安全 | 2 | 无批准不得执行；拒绝、恢复及重复审批正确 |
| 受控编辑与测试 | 2 | 补丁符合预期，限定测试通过，未越界修改 |
| **合计** | **20** | **逐条保存标准、结果与运行轨迹** |

每个任务至少有：`task_id`、任务描述、固定仓库/环境版本、预期结果或验证器、允许工具、完成判据、失败记录。测试集须可复位；不能通过人工修改答案使其“通过”。

### 3. 最低评估指标与方法

- **质量**：任务成功率（通过任务数 / 总任务数）、证据准确性、编辑后测试结果；必要时单独标注“待人工复核”。
- **可靠性与安全**：未授权实际操作次数（硬性为零）、重复执行副作用、任务卡死与恢复、重复运行的一致性。
- **效率**：每任务工具调用次数、运行轮数、输入/输出 Token、摘要额外 Token、可计算的 API 成本、端到端耗时。
- **归因**：记录首次出现错误的环节，而不只保存模型最终回答；分类为理解、规划、工具、Context、状态、权限、输出等。
- **对照**：固定任务和环境，改变单个 Harness 配置（如压缩策略）做配对比较；小样本结论要标注不确定性。

### 4. 按周形成的评估资产

- **W2–W4**：形成手写 Runtime 的模型/工具轨迹，Mock 回归通过。
- **W5**：相同回归任务在 LangChain/LangGraph 执行路径下通过；保留迁移前后行为差异记录。
- **W6**：在正式 Runtime 中建立 4–5 条可复位的仓库分析评估任务。
- **W7–W9**：将 Token、重复读取、压缩正确性纳入任务级记录，形成首个配置对照。
- **W10–W16**：随 Planning、Skills、Subagents、Checkpoint、审批与文件编辑逐步扩充任务，累计至 20 条。
- **W17**：完成统一 `evals/` 运行器、验证器、结果保存和完整基线执行。
- **W18**：正式复测、失败归因、针对性修复、配对对照与评估报告；作为 V1.0 发布门槛。

建议最终形成 `evals/tasks/`、`evals/fixtures/`、`evals/runner.py`、`evals/validators.py`、`evals/results/`、`evals/report.md`；这些是项目评估设施，不是 Deep Agents 官方同名目录要求。注意报告每次评估所用的模型与代码版本，避免拿不同条件下的数字直接比较。

---

## 五、目标目录与官方架构的对应关系（随开发逐步创建）

### 为什么 GitHub 根目录看起来不同？

Deep Agents 是 **Monorepo（单仓库多项目）**。GitHub 首页的 `libs/`、`examples/` 等是仓库层级，而我们规划的 `mini_repo_agent/` 对齐的是官方的**核心 Python 包**：

```text
langchain-ai/deepagents/                 # 官方仓库根目录
└── libs/
    └── deepagents/                     # Python 项目
        └── deepagents/                 # 我们真正对照的核心包
            ├── graph.py
            ├── _models.py
            ├── _tools.py
            ├── middleware/
            ├── backends/
            └── profiles/
```

[直接查看官方核心包](https://github.com/langchain-ai/deepagents/tree/main/libs/deepagents/deepagents)。因此**不需要照搬官方外层的 `libs/`、`examples/` 等目录**；单项目保持简单结构即可。

### 官方模块与本项目的映射

| Deep Agents 官方核心包 | 我们的模块 | 说明 |
|---|---|---|
| `graph.py` | `mini_repo_agent/graph.py` | Agent 创建、Middleware 及依赖组装 |
| `_models.py` | `mini_repo_agent/_models.py` | 模型配置与适配 |
| `_tools.py` | `mini_repo_agent/_tools.py` | 工具定义、注册与执行；按需求简化 |
| `middleware/` | `mini_repo_agent/middleware/` | 优先保持同名文件、相同职责 |
| `backends/` | `mini_repo_agent/backends/` | 接口、文件存储及状态存储 |
| `profiles/` | 暂不要求 | 官方功能，第一版按需研究 |
| 底层依赖 LangChain / LangGraph | W1–W4 `mini_repo_agent/runtime.py`；W5 起使用框架 Runtime | 手写循环仅保留教学对照，正式执行由 `create_agent()` 负责 |
| 不要求同名评估目录 | **额外的** `evals/` | 对齐李博杰第七章 Agent 评估 |

**关键差异（按阶段）：** W1–W4 我们的 `graph.py` 组装手写 `runtime.py`；W5 起和 Deep Agents 一样从 `graph.py` 调用 LangChain `create_agent()`，其执行与持久化/中断能力依赖 LangGraph。我们仍只实现所需的自定义 Middleware / Backend / Agent 能力，不等于直接调用完整的 `deepagents.create_deep_agent()`。

### 目标文件结构

以下是 **W5 迁移后的目标结构示意**，不要求提前创建。当前已有的 `runtime.py` 在迁移后保留为教学实现，正式执行入口不再依赖它；其余模块从现有代码渐进改造。

```text
mini-repo-agent/
├── agent.py                         # CLI 入口
├── mini_repo_agent/
│   ├── __init__.py
│   ├── graph.py                     # Agent 构建与 Middleware 组装
│   ├── legacy/                      # 可选：教学用手写 Runtime（非正式入口）
│   │   └── runtime.py
│   ├── _models.py                   # 模型适配
│   ├── _tools.py                    # 工具定义与执行
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── filesystem.py            # 文件工具接入
│   │   ├── summarization.py         # 上下文管理与压缩
│   │   ├── skills.py                # Skills 加载
│   │   ├── subagents.py             # 子 Agent 委派
│   │   ├── memory.py                # 按需记忆注入
│   │   ├── permissions.py           # 执行权限
│   │   └── patch_tool_calls.py      # 工具调用修补
│   └── backends/
│       ├── __init__.py
│       ├── protocol.py              # Backend 接口
│       ├── filesystem.py            # 本地文件访问
│       └── store.py                 # 业务记忆 Backend（非 LangGraph Checkpointer）
├── skills/
│   └── code-review/
│       └── SKILL.md
├── workspace/
├── tests/                           # 单元 / 集成测试
├── evals/                           # Agent 任务评估（本项目新增）
│   ├── tasks/                       # 20 条任务定义
│   ├── fixtures/                    # 可复位的仓库样例
│   ├── runner.py                    # 评估运行器
│   ├── validators.py                # 判定任务是否成功
│   ├── results/                     # 运行轨迹和指标
│   └── report.md                    # 评估结果与失败分析
└── pyproject.toml
```

> **命名提醒：** 官方的规划、状态、Checkpoint、Interrupt 等行为可能由 LangChain / LangGraph 或多个组件共同承担，因此我们的实现可以新增内部模块，但需要在 README 中写明与官方架构的对应关系，不强行创造“官方同名文件”。

---

## 六、项目交付边界

### V1.0 必须具备

- 基于 LangChain `create_agent()` / LangGraph 的正式 Agent Runtime、Tool Registry、Middleware 组合及可替换文件 Backend；手写版本仅用于学习对照。
- Context 管理（预算、摘要 / 外存）、TODO / State、Skills 渐进加载、Subagents。
- 使用 LangGraph Checkpointer / Interrupt 的持久化恢复和人工审批；受控文件编辑和固定测试执行入口。
- CLI、关键路径自动化测试和真实仓库端到端示例。
- **Agent Evaluation**：至少 20 条固定任务、自动化验证器、质量/成本/安全指标、失败归因和可复现的评估报告。

### V1.0 暂不追求

- 官方全部 Provider Profiles、对 LangGraph 内部运行时的完整重实现、跨机器分布式调度。
- 生产级多租户隔离、完整操作系统级 Sandbox、任意 Shell 的安全执行。
- 大规模并发子 Agent、多用户权限系统、成熟的云端部署运维体系。

### 项目成功的最终判据

**不是“文件数量像 Deep Agents”，而是：**你能解释手写 Runtime 与 LangChain / LangGraph Runtime 的对应关系，亲手完成迁移并开发可组合的 Middleware / Backend / Agent 能力；对照官方源码说明模块职责、数据流与设计取舍；系统能完成真实、受控的多步骤 Coding Agent 任务，并用可重复评估说明质量、可靠性、成本与限制。

---

## 七、官方参考入口

- [Mini Repo Agent（当前项目）](https://github.com/h173317887/mini-repo-agent)
- [Deep Agents 官方仓库](https://github.com/langchain-ai/deepagents)
- [Deep Agents Architecture](https://github.com/langchain-ai/deepagents/blob/main/libs/ARCHITECTURE.md)
- [Deep Agents 核心 graph.py](https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/deepagents/graph.py)
- [Deep Agents Middleware 源码](https://github.com/langchain-ai/deepagents/tree/main/libs/deepagents/deepagents/middleware)
- [LangChain AgentMiddleware 接口](https://github.com/langchain-ai/langchain/blob/master/libs/langchain_v1/langchain/agents/middleware/types.py)
- [LangChain create_agent](https://docs.langchain.com/oss/python/langchain/agents)
- [LangGraph 持久化 / 中断机制](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Deep Agents Backend 源码](https://github.com/langchain-ai/deepagents/tree/main/libs/deepagents/deepagents/backends)
- [李博杰《深入理解 AI Agent 架构》](https://github.com/bojieli/ai-agent-book)
- [第七章：Agent 的评估](https://github.com/bojieli/ai-agent-book/blob/main/book/chapter7.md)
- [Codex 开源仓库（辅助对照）](https://github.com/openai/codex)