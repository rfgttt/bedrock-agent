from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class Message:
    role: Role
    content: str | None = None
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass(slots=True)
class ModelResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass(slots=True)
class PendingApproval:
    approval_id: str
    session_id: str
    tool_call: ToolCall
    reason: str


@dataclass(slots=True)
class RunResult:
    status: str
    session_id: str
    trace_id: str
    output: str | None = None
    pending_approval: PendingApproval | None = None
    error: str | None = None


@dataclass(slots=True)
class MemoryRecord:
    memory_id: str
    kind: str
    content: str
    tags: list[str]
    importance: int
    created_at: str
    score: float = 0.0


@dataclass(slots=True)
class SkillDefinition:
    skill_id: str
    name: str
    description: str
    parameters: dict[str, Any]
    steps: list[dict[str, Any]]
    risk: str
    status: str = "active"
