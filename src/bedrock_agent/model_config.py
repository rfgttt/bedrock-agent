from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values

from bedrock_agent.config import (
    DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_MODEL,
)
from bedrock_agent.security import make_private_file


@dataclass(frozen=True, slots=True)
class DeepSeekConfig:
    api_key: str
    base_url: str = DEEPSEEK_BASE_URL
    model: str = DEFAULT_DEEPSEEK_MODEL

    def validate(self) -> None:
        if not self.api_key.strip():
            raise ValueError("DeepSeek API Key 不能为空")
        parsed = urlparse(self.base_url.strip())
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("DeepSeek API 地址必须是有效的 HTTPS 地址")
        if parsed.hostname not in {"api.deepseek.com"}:
            raise ValueError("当前版本只允许连接 DeepSeek 官方 API：api.deepseek.com")
        if not self.model.strip():
            raise ValueError("模型名称不能为空")


class EnvModelConfigStore:
    """Read and atomically update only the model-related .env keys."""

    KEYS = {
        "AGENT_PROVIDER": "deepseek",
        "DEEPSEEK_API_KEY": "",
        "AGENT_BASE_URL": DEEPSEEK_BASE_URL,
        "AGENT_MODEL": DEFAULT_DEEPSEEK_MODEL,
    }

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> DeepSeekConfig:
        values = dotenv_values(self.path) if self.path.exists() else {}
        return DeepSeekConfig(
            api_key=(values.get("DEEPSEEK_API_KEY") or values.get("AGENT_API_KEY") or "").strip(),
            base_url=(values.get("AGENT_BASE_URL") or DEEPSEEK_BASE_URL).strip().rstrip("/"),
            model=(values.get("AGENT_MODEL") or DEFAULT_DEEPSEEK_MODEL).strip(),
        )

    def save(self, config: DeepSeekConfig) -> None:
        config.validate()
        replacements = {
            "AGENT_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": config.api_key.strip(),
            "AGENT_BASE_URL": config.base_url.strip().rstrip("/"),
            "AGENT_MODEL": config.model.strip(),
        }
        existing = self.path.read_text(encoding="utf-8").splitlines() if self.path.exists() else []
        output: list[str] = []
        written: set[str] = set()
        managed = set(replacements) | {"AGENT_API_KEY"}

        for line in existing:
            stripped = line.strip()
            key = stripped.split("=", 1)[0].strip() if "=" in stripped and not stripped.startswith("#") else None
            if key == "AGENT_API_KEY":
                # Migrate the old generic secret name without preserving a duplicate.
                continue
            if key in replacements:
                if key not in written:
                    output.append(f"{key}={replacements[key]}")
                    written.add(key)
                continue
            output.append(line)

        if output and output[-1].strip():
            output.append("")
        if not any(line.strip() == "# DeepSeek model configuration" for line in output):
            output.append("# DeepSeek model configuration")
        for key, value in replacements.items():
            if key not in written:
                output.append(f"{key}={value}")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(self.path.name + ".tmp")
        temp_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
        temp_path.replace(self.path)
        make_private_file(self.path)

    @staticmethod
    def masked_key(api_key: str) -> str:
        if not api_key:
            return "未配置"
        if len(api_key) <= 8:
            return "*" * len(api_key)
        return f"{api_key[:4]}…{api_key[-4:]}"
