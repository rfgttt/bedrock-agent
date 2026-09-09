from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from bedrock_agent.domain import Message


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def stable_fingerprint(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def message_fingerprint(message: Message) -> str:
    return stable_fingerprint(
        {
            "role": message.role.value,
            "content": message.content,
            "tool_call_id": message.tool_call_id,
            "name": message.name,
            "tool_calls": [
                {"id": call.id, "name": call.name, "arguments": call.arguments}
                for call in message.tool_calls
            ],
        }
    )


@dataclass(frozen=True, slots=True)
class MessageRenderPlan:
    mode: Literal["none", "append", "full"]
    start_index: int = 0


@dataclass(slots=True)
class DesktopRefreshState:
    """Tracks rendered data without knowing anything about Tkinter widgets."""

    message_session_id: str | None = None
    message_keys: list[str] = field(default_factory=list)
    hidden_message_count: int = 0
    view_fingerprints: dict[str, str] = field(default_factory=dict)
    dirty_views: set[str] = field(default_factory=set)

    def plan_messages(
        self,
        session_id: str,
        messages: list[Message],
        *,
        hidden_count: int = 0,
        force: bool = False,
    ) -> MessageRenderPlan:
        keys = [message_fingerprint(message) for message in messages]
        if force or session_id != self.message_session_id or hidden_count != self.hidden_message_count:
            self.message_session_id = session_id
            self.message_keys = keys
            self.hidden_message_count = hidden_count
            return MessageRenderPlan("full")
        if keys == self.message_keys:
            return MessageRenderPlan("none")
        if len(keys) >= len(self.message_keys) and keys[: len(self.message_keys)] == self.message_keys:
            start = len(self.message_keys)
            self.message_keys = keys
            return MessageRenderPlan("append", start)
        self.message_keys = keys
        return MessageRenderPlan("full")

    def append_pending_message(self, session_id: str, message: Message) -> None:
        if self.message_session_id != session_id:
            self.message_session_id = session_id
            self.message_keys = []
            self.hidden_message_count = 0
        self.message_keys.append(message_fingerprint(message))

    def reset_messages(self, session_id: str | None = None) -> None:
        self.message_session_id = session_id
        self.message_keys = []
        self.hidden_message_count = 0

    def changed(self, view: str, value: Any, *, force: bool = False) -> bool:
        fingerprint = stable_fingerprint(value)
        if not force and self.view_fingerprints.get(view) == fingerprint:
            self.dirty_views.discard(view)
            return False
        self.view_fingerprints[view] = fingerprint
        self.dirty_views.discard(view)
        return True

    def mark_dirty(self, *views: str) -> None:
        self.dirty_views.update(views)

    def is_dirty(self, view: str) -> bool:
        return view in self.dirty_views
