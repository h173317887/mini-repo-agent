from langchain.agents.middleware import AgentMiddleware
from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool

from ..backends.protocol import BackendProtocol


class FilesystemMiddleware(AgentMiddleware):
    def __init__(self, backend: BackendProtocol):
        self.backend = backend
        self.tools = [
            self._create_ls_tool(),
            self._create_read_file_tool(),
            self._create_grep_tool(),
        ]

    def _create_ls_tool(self):
        @tool
        def ls(path: str, runtime: ToolRuntime) -> ToolMessage:
            """列出指定目录下的文件和子目录。"""
            result = self.backend.ls(path)

            if result.error:
                return ToolMessage(
                    content=result.error,
                    name="ls",
                    tool_call_id=runtime.tool_call_id,
                    status="error",
                )

            paths = [item["path"] for item in result.entries or []]

            return ToolMessage(
                content="\n".join(paths) or "目录为空",
                name="ls",
                tool_call_id=runtime.tool_call_id,
                status="success",
            )

        return ls

    def _create_read_file_tool(self):
        @tool
        def read_file(
            file_path: str,
            runtime: ToolRuntime,
            offset: int = 0,
            limit: int = 2000,
        ) -> ToolMessage:
            """按行读取工作区内的文本文件。"""
            result = self.backend.read(file_path, offset, limit)

            if result.error or result.file_data is None:
                return ToolMessage(
                    content=result.error or "文件内容为空",
                    name="read_file",
                    tool_call_id=runtime.tool_call_id,
                    status="error",
                )

            if result.no_lines_requested:
                content = "未请求任何行"
            elif result.start_line is None:
                content = result.file_data["content"] or "文件为空"
            else:
                lines = result.file_data["content"].splitlines()

                content = "\n".join(
                    f"{i}: {line}" for i, line in enumerate(lines, result.start_line)
                )

                if result.next_offset is not None:
                    content += f"\n下一次读取 offset={result.next_offset}"

            return ToolMessage(
                content=content,
                name="read_file",
                tool_call_id=runtime.tool_call_id,
                status="success",
            )

        return read_file

    def _create_grep_tool(self):
        @tool
        def grep(
            pattern: str,
            runtime: ToolRuntime,
            path: str = "/",
            glob: str | None = None,
            max_count: int = 20,
        ) -> ToolMessage:
            """搜索工作区内包含指定文本的代码行，返回路径和行号。"""
            result = self.backend.grep(
                pattern,
                path=path,
                glob=glob,
                max_count=max_count,
            )

            if result.error:
                return ToolMessage(
                    content=result.error,
                    name="grep",
                    tool_call_id=runtime.tool_call_id,
                    status="error",
                )

            matches = result.matches or []

            content = (
                "\n".join(
                    f"{item['path']}:{item['line']}: {item['text']}" for item in matches
                )
                or "没有找到匹配内容"
            )

            if result.truncated:
                content += "\n结果已截断，请缩小搜索范围"

            return ToolMessage(
                content=content,
                name="grep",
                tool_call_id=runtime.tool_call_id,
                status="success",
            )

        return grep
