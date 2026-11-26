from abc import ABC
from dataclasses import dataclass
from typing import TypedDict


class FileData(TypedDict):
    content: str
    encoding: str


@dataclass
class ReadResult:
    error: str | None = None
    file_data: FileData | None = None
    total_lines: int | None = None
    start_line: int | None = None
    end_line: int | None = None
    next_offset: int | None = None
    no_lines_requested: bool = False


class FileInfo(TypedDict):
    path: str
    is_dir: bool


@dataclass
class LsResult:
    error: str | None = None
    entries: list[FileInfo] | None = None


class GrepMatch(TypedDict):
    path: str
    line: int
    text: str


@dataclass
class GrepResult:
    error: str | None = None
    matches: list[GrepMatch] | None = None
    truncated: bool = False


class BackendProtocol(ABC):
    def read(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = 2000,
    ) -> ReadResult:
        raise NotImplementedError

    def ls(self, path: str) -> LsResult:
        raise NotImplementedError

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
        *,
        max_count: int | None = None,
    ) -> GrepResult:
        raise NotImplementedError
