from __future__ import annotations

import getpass
from collections import deque
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bedrock_agent.bootstrap import build_runtime
from bedrock_agent.config import Settings
from bedrock_agent.domain import ModelResponse
from bedrock_agent.security import LocalTokenStore, is_loopback, require_loopback_bind
from bedrock_agent.server import create_app


class ScriptedModel:
    def __init__(self) -> None:
        self.responses = deque([ModelResponse(text="ok")])

    def complete(self, messages, tools):
        return self.responses.popleft()


def settings_for(tmp_path: Path) -> Settings:
    return Settings(
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
        max_steps=8,
        memory_context_limit=5,
    )


def test_loopback_check() -> None:
    assert is_loopback("127.0.0.1")
    assert is_loopback("::1")
    assert not is_loopback("192.168.1.2")
    with pytest.raises(ValueError):
        require_loopback_bind("0.0.0.0")


def test_local_api_requires_loopback_and_token(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    runtime = build_runtime(settings, model=ScriptedModel())
    token = LocalTokenStore(settings.token_file).get_or_create()
    app = create_app(runtime, token)

    local = TestClient(app, client=("127.0.0.1", 50000))
    assert local.get("/v1/health").status_code == 401
    response = local.get(
        "/v1/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["scope"] == "loopback-only"

    remote = TestClient(app, client=("192.168.1.50", 50000))
    response = remote.get(
        "/v1/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
