from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bedrock_agent.bootstrap import Runtime, build_runtime
from bedrock_agent.config import Settings
from bedrock_agent.domain import Message, RunResult
from bedrock_agent.model_config import DeepSeekConfig, EnvModelConfigStore


class DesktopController:
    """UI-neutral adapter around the Bedrock runtime.

    Keeping this layer free of Tkinter makes desktop behavior easy to test and
    prevents presentation concerns from leaking into the agent loop.
    """

    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime
        self.session_id = uuid.uuid4().hex
        self.last_trace_id: str | None = None

    def new_session(self) -> str:
        self.session_id = uuid.uuid4().hex
        self.last_trace_id = None
        return self.session_id

    def select_session(self, session_id: str) -> None:
        if not session_id.strip():
            raise ValueError("session_id cannot be empty")
        self.session_id = session_id

    def send(self, text: str) -> RunResult:
        text = text.strip()
        if not text:
            raise ValueError("Message cannot be empty")
        result = self.runtime.runner.run(text, session_id=self.session_id)
        self.last_trace_id = result.trace_id
        return result

    def resolve_approval(self, approval_id: str, approved: bool) -> RunResult:
        result = self.runtime.runner.resume(approval_id, approved=approved)
        self.session_id = result.session_id
        self.last_trace_id = result.trace_id
        return result

    def pending_approvals(self) -> list[dict[str, Any]]:
        return [
            {
                "approval_id": pending.approval_id,
                "session_id": pending.session_id,
                "tool": pending.tool_call.name,
                "arguments": pending.tool_call.arguments,
                "reason": pending.reason,
            }
            for pending in self.runtime.store.list_pending()
        ]

    def pending_approval(self, approval_id: str):
        return self.runtime.store.get_pending(approval_id)

    def messages(self, session_id: str | None = None) -> list[Message]:
        return self.runtime.store.get_messages(session_id or self.session_id)

    def message_view(
        self,
        session_id: str | None = None,
    ) -> tuple[list[Message], int]:
        selected = session_id or self.session_id
        total = self.runtime.store.count_messages(selected)
        limit = self.runtime.settings.desktop_message_limit
        messages = self.runtime.store.get_recent_messages(selected, limit=limit)
        return messages, max(0, total - len(messages))

    def sessions(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self.runtime.store.list_sessions(limit=limit)

    def delete_session(self, session_id: str) -> dict[str, Any]:
        selected = session_id.strip()
        if not selected:
            raise ValueError("session_id cannot be empty")
        counts = self.runtime.store.delete_session(selected)
        replaced_current = selected == self.session_id
        if replaced_current:
            self.new_session()
        return {
            "deleted_session_id": selected,
            "current_session_id": self.session_id,
            "replaced_current": replaced_current,
            **counts,
        }

    def memories(self, query: str = "", *, limit: int = 100) -> list[dict[str, Any]]:
        records = (
            self.runtime.store.search_memories(query, limit=min(limit, 20))
            if query.strip()
            else self.runtime.store.list_memories(limit=limit)
        )
        return [asdict(record) for record in records]

    def skills(self) -> list[dict[str, Any]]:
        return [asdict(skill) for skill in self.runtime.store.list_skills()]

    def trace_records(self, trace_id: str | None = None) -> list[dict[str, Any]]:
        selected = trace_id or self.last_trace_id
        if not selected:
            return []
        path = self.runtime.settings.trace_dir / f"{selected}.jsonl"
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"event": "invalid_trace_line", "payload": {"raw": line}})
        return records

    def capability_status(self, *, force_refresh: bool = False) -> list[dict[str, object]]:
        return self.runtime.capabilities.status(force_refresh=force_refresh)

    def allowed_apps(self, *, force_refresh: bool = False) -> list[dict[str, Any]]:
        return self.runtime.capabilities.applications.list_apps(force_refresh=force_refresh)

    def configure_allowed_app(self, app: str, executable: Path) -> dict[str, Any]:
        return self.runtime.capabilities.applications.set_explicit_path(app, executable)

    def add_allowed_app(
        self, display_name: str, executable: Path, aliases: list[str] | None = None
    ) -> dict[str, Any]:
        return self.runtime.capabilities.applications.add_custom_app(
            display_name, executable, aliases=aliases or []
        )

    def remove_allowed_app(self, app: str) -> None:
        self.runtime.capabilities.applications.remove_custom_app(app)

    def workspace_path(self) -> Path:
        return self.runtime.settings.workspace.resolve()

    def import_workspace_paths(
        self, sources: list[Path], *, destination: str = "imports"
    ) -> list[dict[str, Any]]:
        return [
            asdict(result)
            for result in self.runtime.capabilities.workspace_import.import_paths(
                sources, destination=destination
            )
        ]

    def mcp_status(self) -> dict[str, Any]:
        return {
            "sdk_available": self.runtime.mcp.sdk_available(),
            "servers": self.runtime.mcp.server_rows(),
            "registered_tools": [
                name for name in self.runtime.registry.names() if name.startswith("mcp_")
            ],
            "config_path": str(self.runtime.mcp.catalog.path.resolve()),
        }

    def import_mcp_config(self, source: Path) -> list[dict[str, Any]]:
        return [asdict(server) for server in self.runtime.mcp.catalog.import_file(source)]

    def set_mcp_enabled(self, server_id: str, enabled: bool) -> dict[str, Any]:
        self.runtime.mcp.catalog.set_enabled(server_id, enabled)
        return self.runtime.mcp.sync_tools()

    def remove_mcp_server(self, server_id: str) -> dict[str, Any]:
        self.runtime.mcp.catalog.remove(server_id)
        return self.runtime.mcp.sync_tools()

    def test_mcp_server(self, server_id: str) -> dict[str, Any]:
        return self.runtime.mcp.test_server(server_id)

    def sync_mcp_tools(self) -> dict[str, Any]:
        return self.runtime.mcp.sync_tools()

    def learning_dashboard(self, *, days: int = 30) -> dict[str, Any]:
        return self.runtime.capabilities.learning.dashboard(days)

    def model_configuration(self) -> dict[str, str]:
        settings = self.runtime.settings
        store = EnvModelConfigStore(settings.env_path)
        config = store.load()
        return {
            "提供商": "DeepSeek",
            "API Key": store.masked_key(config.api_key),
            "API 地址": config.base_url,
            "模型": config.model,
            "配置文件": str(settings.env_path.resolve()),
        }

    def reconfigure_model(self, config: DeepSeekConfig) -> dict[str, str]:
        store = EnvModelConfigStore(self.runtime.settings.env_path)
        store.save(config)
        new_settings = Settings.from_env(self.runtime.settings.env_path)
        new_runtime = build_runtime(new_settings)
        current_session = self.session_id
        current_trace = self.last_trace_id
        previous_runtime = self.runtime
        self.runtime = new_runtime
        self.session_id = current_session
        self.last_trace_id = current_trace
        previous_runtime.close()
        return self.model_configuration()

    @staticmethod
    def probe_model(config: DeepSeekConfig) -> dict[str, Any]:
        config.validate()
        from bedrock_agent.llm.openai_compatible import OpenAICompatibleModel

        model = OpenAICompatibleModel(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
        )
        try:
            return model.probe()
        finally:
            model.close()

    def security_summary(self) -> dict[str, str]:
        settings = self.runtime.settings
        return {
            "运行模式": "桌面进程内调用（不开放网络端口）",
            "本地用户": settings.owner_user,
            "工作区": str(settings.workspace.resolve()),
            "私有数据": str(settings.data_dir.resolve()),
            "数据库": str(settings.db_path.resolve()),
            "轨迹目录": str(settings.trace_dir.resolve()),
            "模型提供商": "DeepSeek",
            "模型": settings.model,
            "模型接口": settings.base_url,
            "工作区导入目录": str((settings.workspace / "imports").resolve()),
            "MCP 配置": str(self.runtime.mcp.catalog.path.resolve()),
        }

    def close(self) -> None:
        self.runtime.close()

    @staticmethod
    def open_path(path: Path) -> None:
        import os
        import subprocess
        import sys

        resolved = path.resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(resolved)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(resolved)])
        else:
            subprocess.Popen(["xdg-open", str(resolved)])
