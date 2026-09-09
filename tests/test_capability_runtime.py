from __future__ import annotations

import getpass
from collections import deque
from pathlib import Path

from bedrock_agent.bootstrap import build_runtime
from bedrock_agent.config import Settings
from bedrock_agent.domain import ModelResponse


class ScriptedModel:
    def __init__(self) -> None:
        self.responses = deque([ModelResponse(text="ok")])

    def complete(self, messages, tools):
        return self.responses.popleft()


def test_runtime_registers_decoupled_capability_groups(tmp_path: Path) -> None:
    settings = Settings(
        api_key="unused",
        base_url="http://unused",
        model="unused",
        data_dir=tmp_path / "private",
        db_path=tmp_path / "private" / "bedrock.db",
        workspace=tmp_path / "workspace",
        trace_dir=tmp_path / "private" / "traces",
        token_file=tmp_path / "private" / "local_api.token",
        bind_host="127.0.0.1",
        bind_port=8765,
        owner_user=getpass.getuser(),
    )
    runtime = build_runtime(settings, model=ScriptedModel())

    status = runtime.capabilities.status()
    assert len(status) == 7
    assert runtime.registry.contains("launch_allowed_app")
    assert runtime.registry.contains("control_system_media")
    assert runtime.registry.contains("search_public_web")
    assert runtime.registry.contains("plan_workspace_organization")
    assert runtime.registry.contains("check_python_syntax")
    assert runtime.registry.contains("get_learning_dashboard")
