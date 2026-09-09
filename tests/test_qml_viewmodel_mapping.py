import pytest
pytest.importorskip("PySide6")

from bedrock_agent.desktop_qml.viewmodel import BedrockViewModel
from bedrock_agent.domain import Message, Role, ToolCall


def test_tool_arguments_are_compacted_for_chat_but_payload_is_retained() -> None:
    call = ToolCall("1", "create_study_plan", {"title": "30 天计划", "topics": [f"Day {i}" for i in range(30)], "daily_minutes": 90})
    rows = BedrockViewModel._message_rows([Message(Role.ASSISTANT, tool_calls=[call])])
    assert len(rows) == 1
    assert "30 项" in rows[0]["message_text"]
    assert '"topics"' in rows[0]["payload"]


def test_message_mapping_preserves_roles_and_visible_text() -> None:
    rows = BedrockViewModel._message_rows([Message(Role.USER, "hi"), Message(Role.ASSISTANT, "hello")])
    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert [row["message_text"] for row in rows] == ["hi", "hello"]
    assert all("body" not in row for row in rows)


def test_selecting_current_session_still_navigates_to_chat(monkeypatch) -> None:
    class Controller:
        session_id = "same-session"

        def message_view(self):
            return [Message(Role.ASSISTANT, "history remains visible")], 0

        def select_session(self, session_id: str) -> None:
            raise AssertionError("same session should not require controller reselection")

        def close(self) -> None:
            pass

    monkeypatch.setattr(BedrockViewModel, "refreshAll", lambda self: None)
    vm = BedrockViewModel(Controller())
    vm._current_page = "approvals"

    vm.selectSession("same-session")

    assert vm.currentPage == "chat"
    assert vm.messagesModel.count == 1
    assert vm.messagesModel.get(0)["message_text"] == "history remains visible"
    vm.close()
