from fnmatch import fnmatchcase
from pathlib import Path

from .protocol import BackendProtocol, FileData, GrepResult, LsResult, ReadResult

ALLOWED_EXTENSIONS = {".py", ".md", ".txt", ".json", ".toml"}


class FilesystemBackend(BackendProtocol):
    def __init__(self, root_dir: str | Path):
        self.cwd = Path(root_dir).resolve()

    def _resolve_path(self, file_path: str) -> Path:
        # 采用官方的虚拟路径语义：/security.py 对应 workspace/security.py
        relative = Path(file_path.lstrip("/"))

        if (
            relative.drive
            or ".." in relative.parts
            or any(part.startswith(".") for part in relative.parts)
        ):
            raise ValueError("非法文件路径")

        target = (self.cwd / relative).resolve()

        try:
            resolved_relative = target.relative_to(self.cwd)
        except ValueError as exc:
            raise ValueError("文件路径超出工作区") from exc

        if any(part.startswith(".") for part in resolved_relative.parts):
            raise ValueError("禁止访问隐藏文件")

        return target

    def read(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = 2000,
    ) -> ReadResult:
        try:
            target = self._resolve_path(file_path)
            if target.suffix.lower() not in ALLOWED_EXTENSIONS:
                raise ValueError("不支持的文件类型")
            if not target.is_file():
                return ReadResult(error=f"文件不存在：{file_path}")

            lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
            start = max(0, offset)
            limit = max(0, limit)
            total = len(lines)
            # 空文件
            if total == 0:
                return ReadResult(file_data=FileData(content="", encoding="utf-8"))

            # 未请求任何行
            if limit == 0:
                return ReadResult(
                    file_data=FileData(content="", encoding="utf-8"),
                    no_lines_requested=True,
                )

            # 超出文件末尾
            if start >= total:
                return ReadResult(error="读取起始位置超出文件行数")

            end = min(start + limit, total)

            content = "".join(lines[start : start + max(0, limit)])

            return ReadResult(
                file_data=FileData(
                    content=content,
                    encoding="utf-8",
                ),
                total_lines=total,
                start_line=start + 1,
                end_line=end,
                next_offset=end if end < total else None,
            )
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return ReadResult(error=str(exc))

    def ls(self, path: str) -> LsResult:
        try:
            target = self._resolve_path(path)

            if not target.is_dir():
                return LsResult(error=f"目录不存在：{path}")

            entries = []

            for child in sorted(target.iterdir()):
                if child.name.startswith(".") or child.is_symlink():
                    continue

                if child.is_file():
                    if child.suffix.lower() not in ALLOWED_EXTENSIONS:
                        continue
                elif not child.is_dir():
                    continue

                relative = child.relative_to(self.cwd).as_posix()
                is_dir = child.is_dir()

                entries.append(
                    {
                        "path": f"/{relative}" + ("/" if is_dir else ""),
                        "is_dir": is_dir,
                    }
                )

            return LsResult(entries=entries)

        except (OSError, ValueError) as exc:
            return LsResult(error=str(exc))

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
        *,
        max_count: int | None = None,
    ) -> GrepResult:
        if not pattern:
            return GrepResult(error="搜索内容不能为空")

        if max_count is not None and max_count < 1:
            return GrepResult(error="max_count 必须大于 0")

        try:
            root = self._resolve_path(path or "/")

            if not root.exists():
                return GrepResult(error="搜索路径不存在")

            files = [root] if root.is_file() else root.rglob("*")
            matches = []

            for file in files:
                if file.is_symlink() or not file.is_file():
                    continue

                relative = file.relative_to(self.cwd)

                if any(part.startswith(".") for part in relative.parts):
                    continue

                if file.suffix.lower() not in ALLOWED_EXTENSIONS:
                    continue

                if glob and not fnmatchcase(relative.as_posix(), glob):
                    continue

                # 防止通过符号链接目录访问工作区外的文件
                try:
                    file.resolve().relative_to(self.cwd)
                except ValueError:
                    continue

                with file.open(encoding="utf-8") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        if pattern not in line:
                            continue

                        if max_count is not None and len(matches) >= max_count:
                            return GrepResult(
                                matches=matches,
                                truncated=True,
                            )

                        matches.append(
                            {
                                "path": "/" + relative.as_posix(),
                                "line": line_number,
                                "text": line.rstrip("\r\n"),
                            }
                        )

            return GrepResult(matches=matches)

        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return GrepResult(error=str(exc))
