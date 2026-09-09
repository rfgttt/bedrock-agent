from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bedrock_agent.security import make_private_dir, make_private_file
from bedrock_agent.tools.base import RiskLevel, Tool


@dataclass(frozen=True, slots=True)
class StudyPlan:
    plan_id: str
    title: str
    goal: str
    start_date: str
    days: int
    daily_minutes: int
    topics: list[str]
    schedule: list[dict[str, Any]]


class LearningManager:
    """Owns learning plans, session logs and review scheduling in a separate DB."""

    def __init__(self, db_path: Path) -> None:
        make_private_dir(db_path.parent)
        self.db_path = db_path
        self._initialize()
        make_private_file(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS study_plans (
                    plan_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    days INTEGER NOT NULL,
                    daily_minutes INTEGER NOT NULL,
                    topics_json TEXT NOT NULL,
                    schedule_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS study_sessions (
                    session_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    minutes INTEGER NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    confidence INTEGER NOT NULL,
                    studied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS review_items (
                    item_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL UNIQUE,
                    confidence INTEGER NOT NULL,
                    due_at TEXT NOT NULL,
                    last_reviewed_at TEXT,
                    review_count INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            connection.commit()

    @staticmethod
    def _validate_topics(topics: list[Any]) -> list[str]:
        clean = [str(topic).strip() for topic in topics if str(topic).strip()]
        if not 1 <= len(clean) <= 30:
            raise ValueError("topics must contain 1-30 non-empty items")
        return clean

    def create_plan(
        self,
        *,
        title: str,
        goal: str,
        days: int,
        daily_minutes: int,
        topics: list[Any],
        start_date: str | None = None,
    ) -> dict[str, Any]:
        title = title.strip()
        goal = goal.strip()
        if not title or not goal:
            raise ValueError("title and goal cannot be empty")
        if not 1 <= days <= 365:
            raise ValueError("days must be between 1 and 365")
        if not 10 <= daily_minutes <= 600:
            raise ValueError("daily_minutes must be between 10 and 600")
        clean_topics = self._validate_topics(topics)
        start = date.fromisoformat(start_date) if start_date else date.today()
        schedule = [
            {
                "day": index + 1,
                "date": (start + timedelta(days=index)).isoformat(),
                "topic": clean_topics[index % len(clean_topics)],
                "minutes": daily_minutes,
            }
            for index in range(days)
        ]
        plan = StudyPlan(
            plan_id=uuid.uuid4().hex,
            title=title,
            goal=goal,
            start_date=start.isoformat(),
            days=days,
            daily_minutes=daily_minutes,
            topics=clean_topics,
            schedule=schedule,
        )
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO study_plans(
                    plan_id, title, goal, start_date, days, daily_minutes,
                    topics_json, schedule_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.plan_id,
                    plan.title,
                    plan.goal,
                    plan.start_date,
                    plan.days,
                    plan.daily_minutes,
                    json.dumps(plan.topics, ensure_ascii=False),
                    json.dumps(plan.schedule, ensure_ascii=False),
                ),
            )
            connection.commit()
        return {
            "plan_id": plan.plan_id,
            "title": plan.title,
            "goal": plan.goal,
            "start_date": plan.start_date,
            "days": plan.days,
            "daily_minutes": plan.daily_minutes,
            "topics": plan.topics,
            "schedule_preview": plan.schedule[:14],
        }

    @staticmethod
    def _next_due(confidence: int, now: datetime) -> datetime:
        interval_days = {1: 1, 2: 2, 3: 4, 4: 7, 5: 14}[confidence]
        return now + timedelta(days=interval_days)

    def record_session(
        self,
        *,
        topic: str,
        minutes: int,
        notes: str = "",
        confidence: int = 3,
    ) -> dict[str, Any]:
        topic = topic.strip()
        if not topic:
            raise ValueError("topic cannot be empty")
        if not 1 <= minutes <= 1_440:
            raise ValueError("minutes must be between 1 and 1440")
        if not 1 <= confidence <= 5:
            raise ValueError("confidence must be between 1 and 5")
        now = datetime.now(timezone.utc)
        due = self._next_due(confidence, now)
        session_id = uuid.uuid4().hex
        item_id = uuid.uuid4().hex
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO study_sessions(session_id, topic, minutes, notes, confidence, studied_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, topic, minutes, notes.strip(), confidence, now.isoformat()),
            )
            connection.execute(
                """
                INSERT INTO review_items(item_id, topic, confidence, due_at, last_reviewed_at, review_count)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(topic) DO UPDATE SET
                    confidence=excluded.confidence,
                    due_at=excluded.due_at,
                    last_reviewed_at=excluded.last_reviewed_at,
                    review_count=review_items.review_count + 1
                """,
                (item_id, topic, confidence, due.isoformat(), now.isoformat()),
            )
            connection.commit()
        return {
            "session_id": session_id,
            "topic": topic,
            "minutes": minutes,
            "confidence": confidence,
            "next_review_at": due.isoformat(),
        }

    def dashboard(self, days: int = 30) -> dict[str, Any]:
        if not 1 <= days <= 365:
            raise ValueError("days must be between 1 and 365")
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection:
            summary = connection.execute(
                """
                SELECT COUNT(*) AS sessions, COALESCE(SUM(minutes), 0) AS minutes,
                       COALESCE(AVG(confidence), 0) AS confidence
                FROM study_sessions WHERE studied_at >= ?
                """,
                (since,),
            ).fetchone()
            topics = connection.execute(
                """
                SELECT topic, SUM(minutes) AS minutes, COUNT(*) AS sessions
                FROM study_sessions WHERE studied_at >= ?
                GROUP BY topic ORDER BY minutes DESC, topic LIMIT 20
                """,
                (since,),
            ).fetchall()
            due = connection.execute(
                "SELECT COUNT(*) AS count FROM review_items WHERE due_at <= ?",
                (now,),
            ).fetchone()
            plans = connection.execute(
                "SELECT plan_id, title, goal, start_date, days, daily_minutes, status FROM study_plans ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
        return {
            "period_days": days,
            "sessions": int(summary["sessions"]),
            "minutes": int(summary["minutes"]),
            "average_confidence": round(float(summary["confidence"]), 2),
            "due_reviews": int(due["count"]),
            "topics": [dict(row) for row in topics],
            "plans": [dict(row) for row in plans],
        }

    def review_queue(self, limit: int = 10) -> list[dict[str, Any]]:
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT item_id, topic, confidence, due_at, last_reviewed_at, review_count
                FROM review_items
                WHERE due_at <= ?
                ORDER BY due_at ASC, confidence ASC
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()
        return [dict(row) for row in rows]


def build_learning_tools(manager: LearningManager) -> list[Tool]:
    return [
        Tool(
            name="create_study_plan",
            description="Create and save a structured daily study plan. Requires local approval.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "goal": {"type": "string"},
                    "days": {"type": "integer"},
                    "daily_minutes": {"type": "integer"},
                    "topics": {"type": "array"},
                    "start_date": {"type": "string"},
                },
                "required": ["title", "goal", "days", "daily_minutes", "topics"],
                "additionalProperties": False,
            },
            handler=lambda arguments: manager.create_plan(
                title=arguments["title"],
                goal=arguments["goal"],
                days=arguments["days"],
                daily_minutes=arguments["daily_minutes"],
                topics=arguments["topics"],
                start_date=arguments.get("start_date"),
            ),
            risk=RiskLevel.WRITE,
        ),
        Tool(
            name="record_study_session",
            description="Record a completed study session and schedule a review. Requires local approval.",
            parameters={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "minutes": {"type": "integer"},
                    "notes": {"type": "string"},
                    "confidence": {"type": "integer"},
                },
                "required": ["topic", "minutes"],
                "additionalProperties": False,
            },
            handler=lambda arguments: manager.record_session(
                topic=arguments["topic"],
                minutes=arguments["minutes"],
                notes=arguments.get("notes", ""),
                confidence=arguments.get("confidence", 3),
            ),
            risk=RiskLevel.WRITE,
        ),
        Tool(
            name="get_learning_dashboard",
            description="Get local study progress, active plans, topic time and due review count.",
            parameters={
                "type": "object",
                "properties": {"days": {"type": "integer"}},
                "additionalProperties": False,
            },
            handler=lambda arguments: manager.dashboard(arguments.get("days", 30)),
        ),
        Tool(
            name="get_review_queue",
            description="List learning topics whose spaced review is due.",
            parameters={
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
                "additionalProperties": False,
            },
            handler=lambda arguments: manager.review_queue(arguments.get("limit", 10)),
        ),
    ]
