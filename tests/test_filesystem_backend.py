"""W6: deterministic tests for the read-only filesystem backend."""

import pytest

from mini_repo_agent.backends.filesystem import FilesystemBackend


SOURCE = (
    "ROLE_PERMISSIONS = {'reader': {'read'}}\n"
    "\n"
    "def can_execute(role, action):\n"
    "    return action in ROLE_PERMISSIONS[role]\n"
)


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "security.py").write_text(SOURCE, encoding="utf-8")
    (tmp_path / "README.md").write_text("can_execute is defined in security.py\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "more.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / ".env").write_text("PRIVATE=SECRET\n", encoding="utf-8")
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "secret.py").write_text("SECRET\n", encoding="utf-8")
    (tmp_path / "blob.bin").write_bytes(b"SECRET")
    return tmp_path


def test_read_returns_line_window_and_metadata(workspace):
    result = FilesystemBackend(workspace).read("/security.py", offset=1, limit=2)
    assert result.error is None
    assert result.file_data == {"content": "\ndef can_execute(role, action):\n", "encoding": "utf-8"}
    assert (result.total_lines, result.start_line, result.end_line, result.next_offset) == (4, 2, 3, 3)


def test_read_negative_offset_and_eof(workspace):
    backend = FilesystemBackend(workspace)
    result = backend.read("/security.py", offset=-3, limit=1)
    assert result.start_line == 1
    assert result.file_data["content"] == "ROLE_PERMISSIONS = {'reader': {'read'}}\n"
    result = backend.read("/security.py", offset=3, limit=100)
    assert result.end_line == 4
    assert result.next_offset is None
    assert backend.read("/security.py", offset=4, limit=1).error


def test_read_zero_limit_and_empty_file(workspace):
    backend = FilesystemBackend(workspace)
    no_lines = backend.read("/security.py", limit=0)
    assert no_lines.no_lines_requested is True
    assert no_lines.file_data["content"] == ""
    assert no_lines.start_line is None

    (workspace / "empty.txt").write_text("", encoding="utf-8")
    empty = backend.read("/empty.txt")
    assert empty.error is None
    assert empty.file_data["content"] == ""
    assert empty.total_lines is None


def test_ls_lists_immediate_entries_and_filters_sensitive_items(workspace):
    backend = FilesystemBackend(workspace)
    listed = backend.ls("/")
    assert listed.error is None
    assert {x["path"] for x in listed.entries} == {"/README.md", "/security.py", "/src/"}
    assert backend.ls("/src").entries == [{"path": "/src/more.py", "is_dir": False}]
    assert backend.ls("/missing").error
    assert backend.ls("/security.py").error


def test_grep_finds_exact_text_path_and_line(workspace):
    backend = FilesystemBackend(workspace)
    result = backend.grep("can_execute", glob="*.py")
    assert result.error is None
    assert result.truncated is False
    assert result.matches == [{
        "path": "/security.py", "line": 3, "text": "def can_execute(role, action):"
    }]
    assert backend.grep("never_exists", glob="*.py").matches == []
    assert backend.grep("hello", path="/src").matches[0]["path"] == "/src/more.py"


def test_grep_max_count_only_marks_real_truncation(workspace):
    (workspace / "three.py").write_text("needle\nneedle\nneedle\n", encoding="utf-8")
    backend = FilesystemBackend(workspace)
    cutoff = backend.grep("needle", max_count=2)
    assert len(cutoff.matches) == 2
    assert cutoff.truncated is True
    exact = backend.grep("needle", max_count=3)
    assert len(exact.matches) == 3
    assert exact.truncated is False


def test_grep_validates_arguments_and_path(workspace):
    backend = FilesystemBackend(workspace)
    assert backend.grep("").error
    assert backend.grep("needle", max_count=0).error
    assert backend.grep("needle", path="/missing").error
    assert backend.grep("SECRET", glob="*.py").matches == []


@pytest.mark.parametrize("path", ["../outside.py", "/.env", "/.hidden/secret.py", "/blob.bin"])
def test_read_rejects_invalid_or_sensitive_paths(workspace, path):
    result = FilesystemBackend(workspace).read(path)
    assert result.error
    assert result.file_data is None


def test_grep_rejects_parent_escape(workspace):
    result = FilesystemBackend(workspace).grep("PRIVATE", path="/../")
    assert result.error
    assert result.matches is None


def test_symlink_outside_workspace_is_not_read_or_listed(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    secret = tmp_path / "outside.py"
    secret.write_text("SECRET_OUTSIDE=1\n", encoding="utf-8")
    link = root / "escape.py"
    try:
        link.symlink_to(secret)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks unavailable in this environment")

    backend = FilesystemBackend(root)
    assert backend.read("/escape.py").error
    assert backend.grep("SECRET_OUTSIDE").matches == []
    assert backend.grep("SECRET_OUTSIDE", path="/escape.py").error
    assert "/escape.py" not in {x["path"] for x in backend.ls("/").entries}
