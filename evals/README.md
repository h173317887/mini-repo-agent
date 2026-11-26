# W6 Agent 评估基线（固定样例仓库）

- fixtures/w6_workspace/ 是固定的小型权限仓库，与真实 workspace/ 分离。
- w6_cases.json 定义五条任务（定位代码、对照文档、不存在的符号、越权访问、分页读取）及预期工具证据。
- tests/test_w6_agent_eval.py 用脚本化 Fake Model 依次调用文件工具，校验 ToolMessage、路径、行号、错误和证据。
- 这些是确定性调用轨迹回归，不等于真实 LLM 的自主规划能力或最终答案质量评估。

运行：uv run pytest tests/test_filesystem_backend.py tests/test_w6_filesystem_middleware.py tests/test_w6_agent_eval.py -v

真实模型评估需要另外让模型自行选择工具，逐条核对预期证据，再统计成功率、漏检和幻觉；不要把 Mock 轨迹结果当成真实 Agent 任务成功率。
