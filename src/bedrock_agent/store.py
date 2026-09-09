from __future__ import annotations

import json
import re
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path
from typing import Any

from bedrock_agent.security import make_private_file

from bedrock_agent.domain import (
    MemoryRecord,
    Message,
    PendingApproval,
    Role,
    SkillDefinition,
    ToolCall,
)


_ASCII_WORD = re.compile(r"[a-zA-Z0-9_]+")
_CJK = re.compile(r"[\u3400-\u9fff]+")


def _search_terms(text: str) -> set[str]:
    text = text.lower()
    terms = set(_ASCII_WORD.findall(text))
    for block in _CJK.findall(text):
        terms.update(block)
        terms.update(block[index : index + 2] for index in range(max(0, len(block) - 1)))
    return {term for term in terms if term}


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        make_private_file(self.db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _init_schema(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    tool_call_id TEXT,
                    name TEXT,
                    tool_calls_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, id);

                CREATE TABLE IF NOT EXISTS pending_approvals (
                    approval_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    tool_call_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TEXT
                );

                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    importance INTEGER NOT NULL DEFAULT 3,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TEXT,
                    use_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_memories_kind_created
                ON memories(kind, created_at DESC);

                CREATE TABLE IF NOT EXISTS skills (
                    skill_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    steps_json TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            connection.commit()

    def append_message(self, session_id: str, message: Message) -> None:
        calls = [
            {"id": call.id, "name": call.name, "arguments": call.arguments}
            for call in message.tool_calls
        ]
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO messages(
                    session_id, role, content, tool_call_id, name, tool_calls_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    message.role.value,
                    message.content,
                    message.tool_call_id,
                    message.name,
                    json.dumps(calls, ensure_ascii=False),
                ),
            )
            connection.commit()

    def list_sessions(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent sessions with a compact display title."""
        limit = max(1, min(limit, 500))
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    session_id,
                    MAX(created_at) AS updated_at,
                    COUNT(*) AS message_count,
                    COALESCE(
                        (
                            SELECT m2.content
                            FROM messages AS m2
                            WHERE m2.session_id = messages.session_id
                              AND m2.role = 'user'
                              AND m2.content IS NOT NULL
                            ORDER BY m2.id DESC
                            LIMIT 1
                        ),
                        '新会话'
                    ) AS title
                FROM messages
                GROUP BY session_id
                ORDER BY MAX(id) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "session_id": row["session_id"],
                "title": str(row["title"])[:80],
                "updated_at": row["updated_at"],
                "message_count": int(row["message_count"]),
            }
            for row in rows
        ]

    def delete_session(self, session_id: str) -> dict[str, int]:
        """Delete one conversation and its unresolved/resolved approvals.

        Long-term memories, learned skills, workspace files and trace files are
        intentionally independent and are not deleted with a conversation.
        """
        session_id = session_id.strip()
        if not session_id:
            raise ValueError("session_id cannot be empty")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            approvals = connection.execute(
                "DELETE FROM pending_approvals WHERE session_id = ?",
                (session_id,),
            ).rowcount
            messages = connection.execute(
                "DELETE FROM messages WHERE session_id = ?",
                (session_id,),
            ).rowcount
            connection.commit()
        return {"messages": max(0, int(messages)), "approvals": max(0, int(approvals))}

    @staticmethod
    def _messages_from_rows(rows: list[sqlite3.Row]) -> list[Message]:
        messages: list[Message] = []
        for row in rows:
            calls = [ToolCall(**item) for item in json.loads(row["tool_calls_json"])]
            messages.append(
                Message(
                    role=Role(row["role"]),
                    content=row["content"],
                    tool_call_id=row["tool_call_id"],
                    name=row["name"],
                    tool_calls=calls,
                )
            )
        return messages

    def get_messages(self, session_id: str) -> list[Message]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
        return self._messages_from_rows(rows)

    def count_messages(self, session_id: str) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(row["count"]) if row is not None else 0

    def get_recent_messages(self, session_id: str, *, limit: int = 80) -> list[Message]:
        """Return a bounded, provider-safe tail of a conversation.

        The query stays bounded even when a session grows for months. Leading
        tool results are removed because a provider must not receive an orphaned
        tool message without its assistant tool call. When possible the window
        starts at a user message.
        """

        limit = max(20, min(limit, 1000))
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT * FROM (
                    SELECT * FROM messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                ) AS recent
                ORDER BY id ASC
                """,
                (session_id, limit + 12),
            ).fetchall()
        messages = self._messages_from_rows(rows)
        while messages and messages[0].role is Role.TOOL:
            messages.pop(0)
        if len(messages) > limit:
            start = len(messages) - limit
            for index in range(start, min(len(messages), start + 12)):
                if messages[index].role is Role.USER:
                    start = index
                    break
            messages = messages[start:]
            while messages and messages[0].role is Role.TOOL:
                messages.pop(0)
        return messages[-limit:]

    def create_pending(
        self,
        session_id: str,
        tool_call: ToolCall,
        reason: str,
    ) -> PendingApproval:
        approval_id = uuid.uuid4().hex
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO pending_approvals(
                    approval_id, session_id, tool_call_id, tool_name,
                    arguments_json, reason
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    session_id,
                    tool_call.id,
                    tool_call.name,
                    json.dumps(tool_call.arguments, ensure_ascii=False),
                    reason,
                ),
            )
            connection.commit()
        return PendingApproval(approval_id, session_id, tool_call, reason)

    def list_pending(self, *, limit: int = 100) -> list[PendingApproval]:
        limit = max(1, min(limit, 500))
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT * FROM pending_approvals
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        output: list[PendingApproval] = []
        for row in rows:
            output.append(
                PendingApproval(
                    approval_id=row["approval_id"],
                    session_id=row["session_id"],
                    tool_call=ToolCall(
                        id=row["tool_call_id"],
                        name=row["tool_name"],
                        arguments=json.loads(row["arguments_json"]),
                    ),
                    reason=row["reason"],
                )
            )
        return output

    def get_pending(self, approval_id: str) -> PendingApproval:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT * FROM pending_approvals
                WHERE approval_id = ? AND status = 'pending'
                """,
                (approval_id,),
            ).fetchone()
        if row is None:
            raise KeyError("Pending approval not found or already resolved")
        call = ToolCall(
            id=row["tool_call_id"],
            name=row["tool_name"],
            arguments=json.loads(row["arguments_json"]),
        )
        return PendingApproval(
            approval_id=row["approval_id"],
            session_id=row["session_id"],
            tool_call=call,
            reason=row["reason"],
        )

    def resolve_pending(self, approval_id: str, approved: bool) -> None:
        status = "approved" if approved else "denied"
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                """
                UPDATE pending_approvals
                SET status = ?, resolved_at = CURRENT_TIMESTAMP
                WHERE approval_id = ? AND status = 'pending'
                """,
                (status, approval_id),
            )
            if cursor.rowcount != 1:
                raise KeyError("Pending approval not found or already resolved")
            connection.commit()

    def add_memory(
        self,
        *,
        kind: str,
        content: str,
        tags: list[str] | None = None,
        importance: int = 3,
        memory_id: str | None = None,
    ) -> MemoryRecord:
        content = content.strip()
        if not content:
            raise ValueError("Memory content cannot be empty")
        if not 1 <= importance <= 5:
            raise ValueError("Memory importance must be between 1 and 5")
        memory_id = memory_id or uuid.uuid4().hex
        tags = sorted({tag.strip().lower() for tag in tags or [] if tag.strip()})
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO memories(memory_id, kind, content, tags_json, importance)
                VALUES (?, ?, ?, ?, ?)
                """,
                (memory_id, kind, content, json.dumps(tags, ensure_ascii=False), importance),
            )
            row = connection.execute(
                "SELECT * FROM memories WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
            connection.commit()
        assert row is not None
        return self._memory_from_row(row)

    def search_memories(
        self,
        query: str,
        *,
        limit: int = 5,
        kinds: set[str] | None = None,
    ) -> list[MemoryRecord]:
        limit = max(1, min(limit, 20))
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM memories ORDER BY importance DESC, created_at DESC LIMIT 500"
            ).fetchall()

        query_terms = _search_terms(query)
        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            if kinds and row["kind"] not in kinds:
                continue
            tags = json.loads(row["tags_json"])
            memory_terms = _search_terms(row["content"] + " " + " ".join(tags))
            overlap = len(query_terms & memory_terms)
            exact_bonus = 4 if query.strip() and query.lower() in row["content"].lower() else 0
            score = overlap * 2 + exact_bonus + int(row["importance"]) * 0.4
            if not query_terms or score > int(row["importance"]) * 0.4:
                scored.append((score, row))
        scored.sort(key=lambda item: (item[0], item[1]["created_at"]), reverse=True)
        selected = scored[:limit]

        if selected:
            ids = [row["memory_id"] for _, row in selected]
            placeholders = ",".join("?" for _ in ids)
            with closing(self._connect()) as connection:
                connection.execute(
                    f"""
                    UPDATE memories
                    SET use_count = use_count + 1, last_used_at = CURRENT_TIMESTAMP
                    WHERE memory_id IN ({placeholders})
                    """,
                    ids,
                )
                connection.commit()

        result: list[MemoryRecord] = []
        for score, row in selected:
            record = self._memory_from_row(row)
            record.score = score
            result.append(record)
        return result

    def list_memories(self, *, limit: int = 50) -> list[MemoryRecord]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
                (max(1, min(limit, 200)),),
            ).fetchall()
        return [self._memory_from_row(row) for row in rows]

    @staticmethod
    def _memory_from_row(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            memory_id=row["memory_id"],
            kind=row["kind"],
            content=row["content"],
            tags=json.loads(row["tags_json"]),
            importance=int(row["importance"]),
            created_at=row["created_at"],
        )

    def prune_episode_memories(self, *, limit: int = 1000) -> int:
        """Keep automatic episode memory bounded without deleting user lessons."""

        limit = max(100, limit)
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                """
                DELETE FROM memories
                WHERE kind = 'episode'
                  AND memory_id NOT IN (
                      SELECT memory_id FROM memories
                      WHERE kind = 'episode'
                      ORDER BY created_at DESC, rowid DESC
                      LIMIT ?
                  )
                """,
                (limit,),
            )
            connection.commit()
        return max(0, cursor.rowcount)

    def save_skill(self, skill: SkillDefinition) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO skills(
                    skill_id, name, description, parameters_json, steps_json, risk, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    description = excluded.description,
                    parameters_json = excluded.parameters_json,
                    steps_json = excluded.steps_json,
                    risk = excluded.risk,
                    status = excluded.status,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    skill.skill_id,
                    skill.name,
                    skill.description,
                    json.dumps(skill.parameters, ensure_ascii=False),
                    json.dumps(skill.steps, ensure_ascii=False),
                    skill.risk,
                    skill.status,
                ),
            )
            connection.commit()

    def list_skills(self, *, status: str = "active") -> list[SkillDefinition]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM skills WHERE status = ? ORDER BY created_at",
                (status,),
            ).fetchall()
        return [
            SkillDefinition(
                skill_id=row["skill_id"],
                name=row["name"],
                description=row["description"],
                parameters=json.loads(row["parameters_json"]),
                steps=json.loads(row["steps_json"]),
                risk=row["risk"],
                status=row["status"],
            )
            for row in rows
        ]
