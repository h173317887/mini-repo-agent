"""W6: tool registration, ToolRuntime injection and LangGraph ToolMessage pairing."""

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from mini_repo_agent.backends.filesystem import FilesystemBackend
from mini_repo_agent.backends.protocol import BackendProtocol, FileData, GrepResult, LsResult, ReadResult
from mini_repo_agent.graph import create_deep_agent
from mini_repo_agent.middleware.filesystem import FilesystemMiddleware


class FakeToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


@pytest.fixture
def backend(tmp_path):
    (tmp_path / "security.py").write_text(
        "ROLE_PERMISSIONS = {'reader': {'read'}}\n"
        "def can_execute(role, action):\n"
        "    return action in ROLE_PERMISSIONS[role]\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("Reader may read.\n", encoding="utf-8")
    return FilesystemBackend(tmp_path)


def invoke_scripted(backend, calls, final="任务完成"):
    responses = [
        AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"w6_{index}"}])
        for index, (name, args) in enumerate(calls, 1)
    ]
    responses.append(AIMessage(content=final))
    agent = create_deep_agent(
        model=FakeToolModel(responses=responses),
        middleware=[FilesystemMiddleware(backend)],
    )
    return agent.invoke({"messages": [{"role": "user", "content": "测试文件工具"}]})


def test_middleware_registers_read_only_tools(backend):
    middleware = FilesystemMiddleware(backend)
    assert [tool.name for tool in middleware.tools] == ["ls", "read_file", "grep"]


@pytest.mark.parametrize("name,args,expected", [
    ("ls", {"path": "/"}, "/security.py"),
    ("read_file", {"file_path": "/security.py", "offset": 1, "limit": 2}, "2: def can_execute(role, action):"),
    ("grep", {"pattern": "can_execute", "glob": "*.py"}, "/security.py:2: def can_execute(role, action):"),
])
def test_langgraph_executes_middleware_tools_and_pairs_messages(backend, name, args, expected):
    result = invoke_scripted(backend, [(name, args)])
    messages = result["messages"]
    assert [type(m) for m in messages] == [HumanMessage, AIMessage, ToolMessage, AIMessage]
    assert messages[1].tool_calls[0]["id"] == "w6_1"
    assert messages[2].name == name
    assert messages[2].tool_call_id == "w6_1"
    assert messages[2].status == "success"
    assert expected in messages[2].content
    assert messages[-1].content == "任务完成"


@pytest.mark.parametrize("name,args", [
    ("read_file", {"file_path": "/missing.py"}),
    ("read_file", {"file_path": "/../outside.py"}),
    ("grep", {"pattern": ""}),
])
def test_middleware_reports_file_errors_as_tool_messages(backend, name, args):
    result = invoke_scripted(backend, [(name, args)])
    msg = result["messages"][2]
    assert isinstance(msg, ToolMessage)
    assert msg.name == name
    assert msg.tool_call_id == "w6_1"
    assert msg.status == "error"
    assert msg.content
    assert result["messages"][-1].content == "任务完成"


def test_middleware_uses_backend_contract_not_local_disk():
    class StubBackend(BackendProtocol):
        def ls(self, path):
            return LsResult(entries=[{"path": "/remote.py", "is_dir": False}])

        def read(self, file_path, offset=0, limit=2000):
            return ReadResult(file_data=FileData(content="remote data\n", encoding="utf-8"))

        def grep(self, pattern, path=None, glob=None, *, max_count=None):
            return GrepResult(matches=[{"path": "/remote.py", "line": 1, "text": "remote data"}])

    result = invoke_scripted(StubBackend(), [("grep", {"pattern": "remote"})])
    assert result["messages"][2].content == "/remote.py:1: remote data"


def test_search_then_read_two_round_trips(backend):
    result = invoke_scripted(backend, [
        ("grep", {"pattern": "can_execute", "glob": "*.py"}),
        ("read_file", {"file_path": "/security.py", "offset": 1, "limit": 2}),
    ])
    messages = result["messages"]
    assert [type(m) for m in messages] == [HumanMessage, AIMessage, ToolMessage, AIMessage, ToolMessage, AIMessage]
    assert messages[2].tool_call_id == "w6_1"
    assert "/security.py:2:" in messages[2].content
    assert messages[4].tool_call_id == "w6_2"
    assert "2: def can_execute" in messages[4].content
    assert messages[-1].content == "任务完成"
