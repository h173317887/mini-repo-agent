from langchain.tools import tool

from ._tools import (
    list_files as original_list_files,
)
from ._tools import (
    read_file as original_read_file,
)


@tool
def list_files() -> list[str]:
    """列出 workspace 中允许读取的文件。"""
    return original_list_files()


@tool
def read_file(path: str) -> str:
    """读取 workspace 中的文本文件，path 为相对路径。"""
    return original_read_file(path)


TOOLS = [list_files, read_file]
