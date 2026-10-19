"""A minimal, read-only ReAct coding agent (no LangChain)."""
import json
import os
import sys
from pathlib import Path

from openai import OpenAI

ROOT = (Path(__file__).parent / "workspace").resolve()
ALLOWED_EXTENSIONS = {".py", ".md", ".txt", ".json", ".toml"}
MAX_STEPS = 6


def safe_path(relative_path: str) -> Path:
    """Limit access to visible, whitelisted text files inside workspace/."""
    target = (ROOT / relative_path).resolve()
    try:
        relative = target.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("不能访问 workspace/ 以外的文件") from exc
    if not relative.parts or any(part.startswith(".") for part in relative.parts):
        raise ValueError("禁止访问隐藏文件或隐藏目录")
    if target.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("不支持的文件类型")
    return target


def list_files() -> list[str]:
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = str(path.relative_to(ROOT))
        try:
            safe_path(relative)
        except ValueError:
            continue
        files.append(relative)
        if len(files) >= 50:
            break
    return files


def read_file(path: str) -> str:
    target = safe_path(path)
    if not target.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")
    return target.read_text(encoding="utf-8")[:12000]


TOOL_HANDLERS = {"list_files": list_files, "read_file": read_file}
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出 workspace 目录下可读取的文件路径。调用时不需要参数。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取 workspace 内的文本文件。path 是相对 workspace 的路径，例如 security.py。",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "相对文件路径"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
]


def execute_tool(name: str, raw_arguments: str) -> str:
    try:
        if name not in TOOL_HANDLERS:
            raise ValueError(f"未知或未授权的工具：{name}")
        arguments = json.loads(raw_arguments or "{}")
        if not isinstance(arguments, dict):
            raise ValueError("工具参数必须是 JSON 对象")
        result = TOOL_HANDLERS[name](**arguments)
        return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
    except (ValueError, TypeError, OSError, UnicodeError) as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)


def run_agent(task: str) -> str:
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise SystemExit("请先设置 DEEPSEEK_API_KEY 环境变量")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    # DeepSeek 兼容 OpenAI Python SDK；实际请求发往 DeepSeek，而非 OpenAI。
    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    messages = [
        {"role": "system", "content": "你是一个只读代码分析助手。需要事实时先用工具检查文件；不得猜测文件内容。只能使用提供的工具。"},
        {"role": "user", "content": task},
    ]

    for step in range(1, MAX_STEPS + 1):
        print(f"\n[第 {step} 轮] 调用模型 {model}")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            # 入门先使用非思考模式，避免额外处理 reasoning_content 的回传。
            extra_body={"thinking": {"type": "disabled"}},
        )
        message = response.choices[0].message
        calls = message.tool_calls or []

        if not calls:
            return message.content or "模型未产生最终答案"

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [call.model_dump(exclude_none=True) for call in calls],
        })
        for call in calls:
            name, raw_args = call.function.name, call.function.arguments
            print(f"  [Action] {name}({raw_args})")
            result = execute_tool(name, raw_args)
            print(f"  [Observation] {result[:350]}")
            messages.append({
                "role": "tool", "tool_call_id": call.id, "content": result
            })

    return "达到最大轮数，停止执行（不能据此认定任务成功）"


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "列出文件，读取 security.py，解释权限控制函数的实现。"
    print("\n[最终回答]\n" + run_agent(question))
