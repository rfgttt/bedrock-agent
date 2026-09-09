from __future__ import annotations

from collections import deque
from pathlib import Path

from bedrock_agent.agent import AgentRunner
from bedrock_agent.domain import ModelResponse
from bedrock_agent.learning import MemoryService, SkillManager
from bedrock_agent.store import SQLiteStore
from bedrock_agent.tools import ToolRegistry, build_default_tools
from bedrock_agent.tracing import TraceWriter


class ScriptedModel:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = deque(responses)
        self.seen_messages = []

    def complete(self, messages, tools):
        self.seen_messages.append(messages)
        return self.responses.popleft()


def test_memory_is_retrieved_as_untrusted_context(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "agent.db")
    store.add_memory(
        kind="lesson",
        content="移动端发送按钮问题先检查浏览器网络请求。",
        tags=["mobile", "debug"],
        importance=5,
    )
    memory = MemoryService(store)
    model = ScriptedModel([ModelResponse(text="收到。")])
    runner = AgentRunner(
        model=model,
        tools=ToolRegistry(build_default_tools(tmp_path / "workspace")),
        store=store,
        tracer=TraceWriter(tmp_path / "traces"),
        memory=memory,
    )

    result = runner.run("移动端发送为什么没反应")

    assert result.status == "completed"
    system_texts = [message.content or "" for message in model.seen_messages[0] if message.role.value == "system"]
    assert any("untrusted memory" in text for text in system_texts)
    assert any("浏览器网络请求" in text for text in system_texts)
    assert any(record.kind == "episode" for record in store.list_memories())


def test_recipe_skill_composes_existing_tools(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "agent.db")
    registry = ToolRegistry(build_default_tools(tmp_path / "workspace"))
    manager = SkillManager(store, registry)

    installed = manager.install_from_proposal(
        {
            "name": "double_number",
            "description": "Double a number using the safe calculator.",
            "parameters": {
                "type": "object",
                "properties": {"value": {"type": "number"}},
                "required": ["value"],
                "additionalProperties": False,
            },
            "steps": [
                {
                    "tool": "calculator",
                    "arguments": {"expression": "{{input.value}}*2"},
                }
            ],
        }
    )

    assert installed["installed"] is True
    tool = registry.get("double_number")
    result = tool.handler({"value": 5})
    assert result["steps"][0]["result"]["result"] == 10


def test_recipe_skill_inherits_write_risk(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "agent.db")
    registry = ToolRegistry(build_default_tools(tmp_path / "workspace"))
    manager = SkillManager(store, registry)

    manager.install_from_proposal(
        {
            "name": "save_note",
            "description": "Save a note in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["path", "text"],
                "additionalProperties": False,
            },
            "steps": [
                {
                    "tool": "write_text_file",
                    "arguments": {
                        "path": "{{input.path}}",
                        "content": "{{input.text}}",
                    },
                }
            ],
        }
    )

    assert registry.get("save_note").risk.value == "write"


def test_agent_skill_proposal_waits_for_local_approval(tmp_path: Path) -> None:
    from bedrock_agent.domain import ToolCall
    from bedrock_agent.learning import build_skill_learning_tool

    store = SQLiteStore(tmp_path / "agent.db")
    registry = ToolRegistry(build_default_tools(tmp_path / "workspace"))
    manager = SkillManager(store, registry)
    registry.register(build_skill_learning_tool(manager))
    proposal = {
        "name": "triple_number",
        "description": "Triple a number with the calculator.",
        "parameters": {
            "type": "object",
            "properties": {"value": {"type": "number"}},
            "required": ["value"],
            "additionalProperties": False,
        },
        "steps": [
            {"tool": "calculator", "arguments": {"expression": "{{input.value}}*3"}}
        ],
    }
    model = ScriptedModel(
        [
            ModelResponse(tool_calls=[ToolCall("skill-1", "propose_recipe_skill", proposal)]),
            ModelResponse(text="技能已安装。"),
        ]
    )
    runner = AgentRunner(
        model=model,
        tools=registry,
        store=store,
        tracer=TraceWriter(tmp_path / "traces"),
    )

    first = runner.run("以后把数字乘三做成技能")
    assert first.status == "approval_required"
    assert not registry.contains("triple_number")

    finished = runner.resume(first.pending_approval.approval_id, approved=True)
    assert finished.status == "completed"
    assert registry.contains("triple_number")
