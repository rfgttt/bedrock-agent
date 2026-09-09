from __future__ import annotations

import sqlite3
from pathlib import Path

from bedrock_agent.capabilities.learning_manager import LearningManager


def test_learning_manager_plan_session_dashboard_and_review(tmp_path: Path) -> None:
    manager = LearningManager(tmp_path / "private" / "learning.db")
    plan = manager.create_plan(
        title="Python 转行计划",
        goal="掌握测试与 Agent 基础",
        days=7,
        daily_minutes=90,
        topics=["Python", "HTTP", "SQL"],
        start_date="2026-07-29",
    )
    assert len(plan["schedule_preview"]) == 7

    manager.record_session(topic="Python", minutes=75, notes="函数与模块", confidence=2)
    dashboard = manager.dashboard(30)
    assert dashboard["sessions"] == 1
    assert dashboard["minutes"] == 75

    with sqlite3.connect(manager.db_path) as connection:
        connection.execute("UPDATE review_items SET due_at = '2000-01-01T00:00:00+00:00'")
        connection.commit()
    queue = manager.review_queue()
    assert queue[0]["topic"] == "Python"
