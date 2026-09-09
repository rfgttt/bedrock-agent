from __future__ import annotations

import getpass
from collections import deque
from pathlib import Path

from bedrock_agent.bootstrap import build_runtime
from bedrock_agent.config import Settings
from bedrock_agent.desktop_controller import DesktopController
from bedrock_agent.domain import ModelResponse, ToolCall


class ScriptedModel:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = deque(responses)

    def complete(self, messages, tools):
        return self.responses.popleft()


def settings_for(tmp_path: Path) -> Settings:
    data = tmp_path / "private"
    return Settings(
        api_key="test",
        base_url="http://local.invalid/v1",
        model="fake-model",
        data_dir=data,
        db_path=data / "bedrock.db",
        workspace=tmp_path / "workspace",
        trace_dir=data / "traces",
        token_file=data / "token",
        bind_host="127.0.0.1",
        bind_port=8765,
        owner_user=getpass.getuser(),
    )


def test_controller_runs_and_lists_session(tmp_path: Path) -> None:
    runtime = build_runtime(
        settings_for(tmp_path),
        model=ScriptedModel([ModelResponse(text="桌面回复")]),
    )
    controller = DesktopController(runtime)

    result = controller.send("你好")

    assert result.status == "completed"
    assert controller.messages()[-1].content == "桌面回复"
    sessions = controller.sessions()
    assert sessions[0]["session_id"] == controller.session_id
    assert sessions[0]["title"] == "你好"


def test_controller_resolves_approval(tmp_path: Path) -> None:
    runtime = build_runtime(
        settings_for(tmp_path),
        model=ScriptedModel(
            [
                ModelResponse(
                    tool_calls=[
                        ToolCall(
                            "write-1",
                            "write_text_file",
                            {"path": "desktop.txt", "content": "ok"},
                        )
                    ]
                ),
                ModelResponse(text="写入完成"),
            ]
        ),
    )
    controller = DesktopController(runtime)

    first = controller.send("写文件")
    assert first.status == "approval_required"
    pending = first.pending_approval
    assert pending is not None

    final = controller.resolve_approval(pending.approval_id, True)

    assert final.status == "completed"
    assert (tmp_path / "workspace" / "desktop.txt").read_text(encoding="utf-8") == "ok"


def test_controller_exposes_memory_skills_and_security(tmp_path: Path) -> None:
    runtime = build_runtime(
        settings_for(tmp_path),
        model=ScriptedModel([ModelResponse(text="完成")]),
    )
    runtime.store.add_memory(kind="lesson", content="桌面测试", importance=4)
    controller = DesktopController(runtime)

    memories = controller.memories("桌面")
    security = controller.security_summary()

    assert memories[0]["content"] == "桌面测试"
    assert security["运行模式"].startswith("桌面进程内")
    assert security["本地用户"] == getpass.getuser()


def test_controller_can_save_netease_executable_path(tmp_path: Path) -> None:
    runtime = build_runtime(
        settings_for(tmp_path),
        model=ScriptedModel([ModelResponse(text="完成")]),
    )
    controller = DesktopController(runtime)
    executable = tmp_path / "apps" / "cloudmusic.exe"
    executable.parent.mkdir()
    executable.write_bytes(b"fake")

    status = controller.configure_allowed_app("netease_cloud_music", executable)

    assert status["available"] is True
    assert status["executable"] == str(executable.resolve())


def test_controller_deletes_only_selected_conversation(tmp_path: Path) -> None:
    runtime = build_runtime(
        settings_for(tmp_path),
        model=ScriptedModel([ModelResponse(text="第一个回复"), ModelResponse(text="第二个回复")]),
    )
    controller = DesktopController(runtime)

    first_session = controller.session_id
    controller.send("第一个会话")
    second_session = controller.new_session()
    controller.send("第二个会话")

    result = controller.delete_session(first_session)

    assert result["deleted_session_id"] == first_session
    assert result["replaced_current"] is False
    assert runtime.store.count_messages(first_session) == 0
    assert runtime.store.count_messages(second_session) == 2
    assert controller.session_id == second_session


def test_deleting_current_conversation_creates_clean_replacement(tmp_path: Path) -> None:
    runtime = build_runtime(
        settings_for(tmp_path),
        model=ScriptedModel([ModelResponse(text="回复")]),
    )
    runtime.store.add_memory(kind="preference", content="不要删除这条长期记忆")
    controller = DesktopController(runtime)
    deleted_session = controller.session_id
    controller.send("需要删除")

    result = controller.delete_session(deleted_session)

    assert result["replaced_current"] is True
    assert controller.session_id != deleted_session
    assert controller.messages() == []
    assert controller.memories()[0]["content"] == "不要删除这条长期记忆"
