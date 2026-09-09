from __future__ import annotations

import json
from pathlib import Path

from bedrock_agent.integrations.mcp import MCPManager, MCPServerCatalog
from bedrock_agent.tools import ToolRegistry
from bedrock_agent.tools.base import RiskLevel


class FakeMCPBackend:
    def available(self) -> bool:
        return True

    def list_tools(self, server):
        return [
            {
                "name": "echo-message",
                "title": "Echo",
                "description": "Echo text",
                "input_schema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                    "additionalProperties": False,
                },
            }
        ]

    def call_tool(self, server, tool_name, arguments):
        return {"server": server.server_id, "tool": tool_name, "value": arguments["text"]}


def test_mcp_config_import_is_disabled_until_user_enables_it(tmp_path: Path) -> None:
    config = tmp_path / "claude.json"
    config.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "demo-server": {
                        "command": "python",
                        "args": ["server.py"],
                        "env": {"DEMO": "1"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    catalog = MCPServerCatalog(tmp_path / "private" / "mcp_servers.json")

    imported = catalog.import_file(config)

    assert imported[0].enabled is False
    assert catalog.get("demo-server").command == "python"


def test_enabled_mcp_tools_are_namespaced_and_always_external(tmp_path: Path) -> None:
    catalog = MCPServerCatalog(tmp_path / "private" / "mcp_servers.json")
    source = tmp_path / "config.json"
    source.write_text(
        json.dumps({"mcpServers": {"demo": {"command": "python", "args": ["server.py"]}}}),
        encoding="utf-8",
    )
    catalog.import_file(source)
    catalog.set_enabled("demo", True)
    registry = ToolRegistry()
    manager = MCPManager(catalog, registry, backend=FakeMCPBackend())

    result = manager.sync_tools()
    tool = registry.get("mcp_demo_echo_message")

    assert result["registered"] == ["mcp_demo_echo_message"]
    assert tool.risk is RiskLevel.EXTERNAL
    assert tool.handler({"text": "hello"})["value"] == "hello"


def test_mcp_optional_dependency_accepts_v2_release_candidate() -> None:
    import tomllib

    root = Path(__file__).resolve().parents[1]
    payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert payload["project"]["optional-dependencies"]["mcp"] == ["mcp>=2.0.0rc1,<3"]


def test_official_backend_rejects_incompatible_v1_sdk(monkeypatch) -> None:
    from bedrock_agent.integrations.mcp import OfficialMCPBackend

    backend = OfficialMCPBackend()
    monkeypatch.setattr(backend, "sdk_version", lambda: "1.28.1")
    monkeypatch.setattr(backend, "_client_api_available", lambda: True)

    assert backend.available() is False
    try:
        backend._require_available()
    except RuntimeError as exc:
        assert "requires MCP Python SDK v2" in str(exc)
    else:
        raise AssertionError("Expected an incompatible v1 SDK error")


def test_official_backend_accepts_v2_release_candidate(monkeypatch) -> None:
    from bedrock_agent.integrations.mcp import OfficialMCPBackend

    backend = OfficialMCPBackend()
    monkeypatch.setattr(backend, "sdk_version", lambda: "2.0.0rc1")
    monkeypatch.setattr(backend, "_client_api_available", lambda: True)

    assert backend.available() is True
    backend._require_available()
