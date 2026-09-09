from __future__ import annotations

import getpass
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODELS = ("deepseek-v4-flash", "deepseek-v4-pro")
DEFAULT_DEEPSEEK_MODEL = DEEPSEEK_MODELS[0]


@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    data_dir: Path
    db_path: Path
    workspace: Path
    trace_dir: Path
    token_file: Path
    bind_host: str
    bind_port: int
    owner_user: str
    max_steps: int = 8
    memory_context_limit: int = 5
    model_message_limit: int = 80
    desktop_message_limit: int = 300
    model_timeout_seconds: float = 60.0
    model_max_retries: int = 1
    trace_file_limit: int = 500
    episode_memory_limit: int = 1000
    provider: str = "deepseek"
    env_path: Path = Path(".env")

    @classmethod
    def from_env(cls, env_path: Path | str | None = None) -> "Settings":
        resolved_env = Path(
            env_path or os.getenv("BEDROCK_ENV_FILE", ".env")
        ).expanduser()
        file_values = {
            key: value
            for key, value in dotenv_values(resolved_env).items()
            if value is not None
        }

        def value(name: str, default: str = "") -> str:
            return os.environ.get(name, file_values.get(name, default))

        api_key = value("DEEPSEEK_API_KEY") or value("AGENT_API_KEY")
        data_dir = Path(value("AGENT_DATA_DIR", "./private"))
        return cls(
            api_key=api_key,
            base_url=value("AGENT_BASE_URL", DEEPSEEK_BASE_URL).rstrip("/"),
            model=value("AGENT_MODEL", DEFAULT_DEEPSEEK_MODEL),
            data_dir=data_dir,
            db_path=Path(value("AGENT_DB_PATH", str(data_dir / "bedrock.db"))),
            workspace=Path(value("AGENT_WORKSPACE", "./workspace")),
            trace_dir=Path(value("AGENT_TRACE_DIR", str(data_dir / "traces"))),
            token_file=Path(value("AGENT_TOKEN_FILE", str(data_dir / "local_api.token"))),
            bind_host=value("AGENT_BIND_HOST", "127.0.0.1"),
            bind_port=int(value("AGENT_BIND_PORT", "8765")),
            owner_user=value("AGENT_OWNER_USER") or getpass.getuser(),
            max_steps=int(value("AGENT_MAX_STEPS", "8")),
            memory_context_limit=int(value("AGENT_MEMORY_CONTEXT_LIMIT", "5")),
            model_message_limit=max(20, int(value("AGENT_MODEL_MESSAGE_LIMIT", "80"))),
            desktop_message_limit=max(50, int(value("AGENT_DESKTOP_MESSAGE_LIMIT", "300"))),
            model_timeout_seconds=max(5.0, float(value("AGENT_MODEL_TIMEOUT_SECONDS", "60"))),
            model_max_retries=max(0, min(3, int(value("AGENT_MODEL_MAX_RETRIES", "1")))),
            trace_file_limit=max(50, int(value("AGENT_TRACE_FILE_LIMIT", "500"))),
            episode_memory_limit=max(100, int(value("AGENT_EPISODE_MEMORY_LIMIT", "1000"))),
            provider=value("AGENT_PROVIDER", "deepseek").lower(),
            env_path=resolved_env,
        )
