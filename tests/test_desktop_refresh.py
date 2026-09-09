from bedrock_agent.desktop_refresh import DesktopRefreshState
from bedrock_agent.domain import Message, Role


def test_message_render_skips_unchanged_and_appends_only_delta() -> None:
    state = DesktopRefreshState()
    first = [Message(Role.USER, "你好")]

    assert state.plan_messages("s1", first).mode == "full"
    assert state.plan_messages("s1", first).mode == "none"

    second = [*first, Message(Role.ASSISTANT, "你好")]
    plan = state.plan_messages("s1", second)
    assert plan.mode == "append"
    assert plan.start_index == 1


def test_pending_user_message_prevents_duplicate_repaint() -> None:
    state = DesktopRefreshState()
    state.plan_messages("s1", [])
    pending = Message(Role.USER, "打开网易云")
    state.append_pending_message("s1", pending)

    committed = [pending, Message(Role.ASSISTANT, "需要调用工具")]
    plan = state.plan_messages("s1", committed)

    assert plan.mode == "append"
    assert plan.start_index == 1


def test_view_fingerprint_avoids_unchanged_rebuild() -> None:
    state = DesktopRefreshState()
    rows = [{"name": "记忆", "count": 2}]

    assert state.changed("memories", rows) is True
    assert state.changed("memories", rows) is False
    assert state.changed("memories", rows, force=True) is True
