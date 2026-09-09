from __future__ import annotations

from collections import deque
from pathlib import Path

from bedrock_agent.agent import AgentRunner
from bedrock_agent.domain import ModelResponse, ToolCall
from bedrock_agent.store import SQLiteStore
from bedrock_agent.tools import ToolRegistry, build_default_tools
from bedrock_agent.tracing import TraceWriter


class ScriptedModel:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = deque(responses)
        self.seen_messages = []

    def complete(self, messages, tools):
        self.seen_messages.append(messages)
        if not self.responses:
            raise AssertionError("No scripted response left")
        return self.responses.popleft()


def build_runner(tmp_path: Path, model: ScriptedModel, max_steps: int = 8) -> AgentRunner:
    return AgentRunner(
        model=model,
        tools=ToolRegistry(build_default_tools(tmp_path / "workspace")),
        store=SQLiteStore(tmp_path / "agent.db"),
        tracer=TraceWriter(tmp_path / "traces"),
        max_steps=max_steps,
    )


def test_agent_calls_tool_then_finishes(tmp_path: Path) -> None:
    model = ScriptedModel(
        [
            ModelResponse(tool_calls=[ToolCall("call-1", "calculator", {"expression": "2+3*4"})]),
            ModelResponse(text="结果是 14。"),
        ]
    )
    runner = build_runner(tmp_path, model)

    result = runner.run("帮我计算 2+3*4")

    assert result.status == "completed"
    assert result.output == "结果是 14。"
    second_turn = model.seen_messages[1]
    assert any(message.role.value == "tool" and '"result": 14' in message.content for message in second_turn)


def test_write_requires_approval_and_can_resume(tmp_path: Path) -> None:
    model = ScriptedModel(
        [
            ModelResponse(
                tool_calls=[
                    ToolCall(
                        "call-write",
                        "write_text_file",
                        {"path": "notes/hello.txt", "content": "hello"},
                    )
                ]
            ),
            ModelResponse(text="文件已经写入。"),
        ]
    )
    runner = build_runner(tmp_path, model)

    first = runner.run("写一个 hello 文件")
    assert first.status == "approval_required"
    assert not (tmp_path / "workspace" / "notes" / "hello.txt").exists()

    resumed = runner.resume(first.pending_approval.approval_id, approved=True)
    assert resumed.status == "completed"
    assert (tmp_path / "workspace" / "notes" / "hello.txt").read_text() == "hello"


def test_denied_write_is_reported_back_to_model(tmp_path: Path) -> None:
    model = ScriptedModel(
        [
            ModelResponse(
                tool_calls=[
                    ToolCall("call-write", "write_text_file", {"path": "x.txt", "content": "x"})
                ]
            ),
            ModelResponse(text="你拒绝了写入，因此没有修改文件。"),
        ]
    )
    runner = build_runner(tmp_path, model)
    first = runner.run("写文件")

    result = runner.resume(first.pending_approval.approval_id, approved=False)

    assert result.status == "completed"
    assert "没有修改" in result.output
    assert not (tmp_path / "workspace" / "x.txt").exists()


def test_agent_stops_at_max_steps(tmp_path: Path) -> None:
    model = ScriptedModel(
        [
            ModelResponse(tool_calls=[ToolCall("call-1", "get_current_time", {})]),
            ModelResponse(tool_calls=[ToolCall("call-2", "get_current_time", {})]),
        ]
    )
    runner = build_runner(tmp_path, model, max_steps=2)

    result = runner.run("一直看时间")

    assert result.status == "failed"
    assert "max_steps" in result.error
