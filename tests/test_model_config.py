from __future__ import annotations

from pathlib import Path

import pytest

from bedrock_agent.config import DEEPSEEK_BASE_URL, DEFAULT_DEEPSEEK_MODEL, Settings
from bedrock_agent.model_config import DeepSeekConfig, EnvModelConfigStore


def test_empty_env_uses_deepseek_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DEEPSEEK_API_KEY",
        "AGENT_API_KEY",
        "AGENT_BASE_URL",
        "AGENT_MODEL",
        "AGENT_PROVIDER",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings.from_env(tmp_path / ".env")

    assert settings.provider == "deepseek"
    assert settings.base_url == DEEPSEEK_BASE_URL
    assert settings.model == DEFAULT_DEEPSEEK_MODEL


def test_model_config_store_migrates_generic_key_and_preserves_other_settings(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "AGENT_API_KEY=old-key\nAGENT_WORKSPACE=./my-workspace\nAGENT_MODEL=old-model\n",
        encoding="utf-8",
    )
    store = EnvModelConfigStore(env_path)

    store.save(
        DeepSeekConfig(
            api_key="test-deepseek-secret",
            base_url=DEEPSEEK_BASE_URL,
            model="deepseek-v4-pro",
        )
    )

    text = env_path.read_text(encoding="utf-8")
    assert "AGENT_API_KEY=" not in text
    assert "DEEPSEEK_API_KEY=test-deepseek-secret" in text
    assert "AGENT_WORKSPACE=./my-workspace" in text
    assert "AGENT_MODEL=deepseek-v4-pro" in text
    assert store.load().api_key == "test-deepseek-secret"


def test_deepseek_config_rejects_nonofficial_endpoint() -> None:
    with pytest.raises(ValueError, match="DeepSeek 官方 API"):
        DeepSeekConfig(
            api_key="secret",
            base_url="https://example.com/v1",
            model="deepseek-v4-flash",
        ).validate()
