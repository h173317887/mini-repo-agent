import json
from collections.abc import Callable


def compact_old_tool_results(messages: list, read_refs: dict, current_step: int):

    latest_by_path = {}

    for call_id, (path, executed_step) in read_refs.items():
        latest_by_path[path] = call_id

    keep_ids = set(latest_by_path.values())

    for msg in messages:
        if msg["role"] != "tool":
            continue

        if msg["tool_call_id"] in keep_ids:
            continue

        info = read_refs.get(msg["tool_call_id"])
        if info is None:
            continue

        path, executed_step = info

        if executed_step >= current_step - 1:
            continue

        data = json.loads(msg["content"])

        if not data.get("ok") or data.get("compressed"):
            continue

        before = len(msg["content"])
        msg["content"] = json.dumps(
            {
                "ok": True,
                "compressed": True,
                "path": path,
                "note": "历史文件内容已压缩。如需最新代码，请重新调用 read_file。",
            },
            ensure_ascii=False,
        )

        after = len(msg["content"])

        print(f"[Compact] {path}: {before} -> {after} 字符")


def run_react_loop(
    client,
    model,
    messages,
    tool_schemas: list[dict],
    execute_tool: Callable[[str, str], str],
    max_steps: int,
) -> str:
    read_refs = {}
    for step in range(1, max_steps + 1):
        print(f"\n[第 {step} 轮] 调用模型 {model}")
        print(f"[Context] 当前消息数量：{len(messages)}")

        compact_old_tool_results(messages, read_refs, step)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tool_schemas,
            # 入门先使用非思考模式，避免额外处理 reasoning_content 的回传。
            extra_body={"thinking": {"type": "disabled"}},
        )
        if response.usage:
            print(
                f"[Tokens] 输入：{response.usage.prompt_tokens}, "
                f"输出：{response.usage.completion_tokens}"
            )
        message = response.choices[0].message
        calls = message.tool_calls or []

        if not calls:
            return message.content or "模型未产生最终答案"

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [call.model_dump(exclude_none=True) for call in calls],
            }
        )
        for call in calls:
            name, raw_args = call.function.name, call.function.arguments
            print(f"  [Action] {name}({raw_args})")
            result = execute_tool(name, raw_args)
            if name == "read_file":
                try:
                    path = json.loads(raw_args)["path"]
                    read_refs[call.id] = (path, step)
                except (ValueError, TypeError, KeyError):
                    pass
            print(f"  [Observation] {result[:350]}")
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": result}
            )

    return "达到最大轮数，停止执行（不能据此认定任务成功）"
