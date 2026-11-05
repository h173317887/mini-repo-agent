import json
from pathlib import Path

ROOT = (Path(__file__).parent.parent / "workspace").resolve()


ALLOWED_EXTENSIONS = {".py", ".md", ".txt", ".json", ".toml"}


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


def execute_tool(name: str, raw_arguments: str) -> str:
    try:
        if name not in TOOL_HANDLERS:
            raise ValueError(f"未知或未授权的工具：{name}")
        arguments = json.loads(raw_arguments or "{}")
        if not isinstance(arguments, dict):
            raise TypeError("工具参数必须是 JSON 对象")
        result = TOOL_HANDLERS[name](**arguments)
        return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
    except (ValueError, TypeError, OSError, UnicodeError) as exc:
        return json.dumps(
            {
                "ok": False,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            },
            ensure_ascii=False,
        )


TOOL_HANDLERS = {"list_files": list_files, "read_file": read_file}
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出 workspace 目录下可读取的文件路径。调用时不需要参数。",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取 workspace 内的文本文件。path 是相对 workspace 的路径，例如 security.py。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "相对文件路径"}
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
]


def validate_tool_registry() -> None:
    schema_names = [schema["function"]["name"] for schema in TOOL_SCHEMAS]

    if len(schema_names) != len(set(schema_names)):
        raise ValueError("工具 Schema 存在重复名称")

    handler_names = set(TOOL_HANDLERS)

    if set(schema_names) != handler_names:
        raise ValueError("工具 Schema 与 Handler 注册不一致")


validate_tool_registry()
