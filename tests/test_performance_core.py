from __future__ import annotations

from collections import deque
from pathlib import Path

from bedrock_agent.agent import AgentRunner
from bedrock_agent.domain import Message, ModelResponse, Role, ToolCall
from bedrock_agent.store import SQLiteStore
from bedrock_agent.tools import ToolRegistry, build_default_tools
from bedrock_agent.tools.base import Tool
from bedrock_agent.tracing import TraceWriter


class ScriptedModel:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = deque(responses)
        self.seen_messages: list[list[Message]] = []

    def complete(self, messages, tools):
        self.seen_messages.append(list(messages))
        return self.responses.popleft()


class CountingMemory:
    def __init__(self) -> None:
        self.calls = 0

    def context_for(self, query: str) -> str:
        self.calls += 1
        return f"memory for {query}"

    def record_episode(self, **kwargs) -> None:
        return None


def test_recent_message_window_is_bounded_and_starts_safely(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "agent.db")
    session = "long"
    for index in range(120):
        store.append_message(session, Message(Role.USER, f"u{index}"))
        store.append_message(session, Message(Role.ASSISTANT, f"a{index}"))

    recent = store.get_recent_messages(session, limit=40)

    assert len(recent) <= 40
    assert recent[0].role is Role.USER
    assert recent[-1].content == "a119"
    assert store.count_messages(session) == 240


def test_agent_retrieves_memory_once_per_tool_loop_and_bounds_context(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "agent.db")
    session = "long"
    for index in range(80):
        store.append_message(session, Message(Role.USER, f"old user {index}"))
        store.append_message(session, Message(Role.ASSISTANT, f"old assistant {index}"))

    model = ScriptedModel(
        [
            ModelResponse(tool_calls=[ToolCall("t1", "calculator", {"expression": "1+1"})]),
            ModelResponse(text="2"),
        ]
    )
    memory = CountingMemory()
    runner = AgentRunner(
        model=model,
        tools=ToolRegistry(build_default_tools(tmp_path / "workspace")),
        store=store,
        tracer=TraceWriter(tmp_path / "traces"),
        memory=memory,
        message_limit=30,
    )

    result = runner.run("new request", session_id=session)

    assert result.status == "completed"
    assert memory.calls == 1
    assert all(len(messages) <= 32 for messages in model.seen_messages)  # 2 system + 30 recent
    assert any(message.content == "new request" for message in model.seen_messages[0])


def test_tool_schema_cache_is_invalidated_only_on_registration() -> None:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="one",
            description="one",
            parameters={"type": "object", "properties": {}},
            handler=lambda _args: 1,
        )
    )
    first = registry.schemas()
    second = registry.schemas()
    assert first is second

    registry.register(
        Tool(
            name="two",
            description="two",
            parameters={"type": "object", "properties": {}},
            handler=lambda _args: 2,
        )
    )
    third = registry.schemas()
    assert third is not first
    assert len(third) == 2


def test_trace_retention_is_bounded_at_startup(tmp_path: Path) -> None:
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    for index in range(70):
        path = trace_dir / f"{index:03}.jsonl"
        path.write_text("{}\n", encoding="utf-8")
        path.touch()

    TraceWriter(trace_dir, file_limit=50)

    assert len(list(trace_dir.glob("*.jsonl"))) == 50


def test_application_status_cache_avoids_repeated_discovery(tmp_path: Path) -> None:
    from bedrock_agent.capabilities.apps import ApplicationCatalog

    calls = 0

    def discover(_definition):
        nonlocal calls
        calls += 1
        return []

    catalog = ApplicationCatalog(
        tmp_path / "apps.json",
        path_exists=lambda _path: False,
        which=lambda _name: None,
        platform_name="win32",
        discovered_candidates=discover,
        status_cache_ttl=60,
    )

    catalog.list_apps()
    first_calls = calls
    catalog.list_apps()

    assert first_calls > 0
    assert calls == first_calls
