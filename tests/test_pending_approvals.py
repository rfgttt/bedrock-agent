from __future__ import annotations

from pathlib import Path

from bedrock_agent.domain import ToolCall
from bedrock_agent.store import SQLiteStore


def test_pending_approvals_are_listed_and_survive_ui_restart(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "bedrock.db")
    created = store.create_pending("session-1", ToolCall("call-1", "launch_allowed_app", {"app": "微信"}), "external")

    rows = store.list_pending()

    assert [row.approval_id for row in rows] == [created.approval_id]
    assert rows[0].tool_call.arguments == {"app": "微信"}
    store.resolve_pending(created.approval_id, True)
    assert store.list_pending() == []
