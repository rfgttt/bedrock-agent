from __future__ import annotations

import asyncio
import importlib.metadata as importlib_metadata
import importlib.util
import ipaddress
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol
from urllib.parse import urlparse

from bedrock_agent.security import make_private_file
from bedrock_agent.tools.base import RiskLevel, Tool
from bedrock_agent.tools.registry import ToolRegistry


_SERVER_ID = re.compile(r"^[a-z][a-z0-9_-]{1,39}$")
_TOOL_SAFE = re.compile(r"[^a-zA-Z0-9_]+")


@dataclass(frozen=True, slots=True)
class MCPServerDefinition:
    server_id: str
    name: str
    transport: str
    enabled: bool = False
    command: str = ""
    args: tuple[str, ...] = ()
    env: dict[str, str] | None = None
    url: str = ""


class MCPBackend(Protocol):
    def available(self) -> bool: ...
    def list_tools(self, server: MCPServerDefinition) -> list[dict[str, Any]]: ...
    def call_tool(
        self,
        server: MCPServerDefinition,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]: ...


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _jsonable(model_dump(mode="json"))
    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))
    return str(value)


class OfficialMCPBackend:
    """Thin, lazy adapter around the official MCP Python SDK v2.

    Bedrock targets the v2 client API. The optional dependency deliberately
    accepts the 2.0.0 release candidate because some mirrors may not have the
    final v2 wheel yet, while still allowing any compatible stable 2.x release.

    A connection is opened only for discovery or one tool call and is closed
    immediately afterwards. This avoids background subprocess/socket leaks in
    the desktop app. It is intentionally conservative rather than optimized for
    high-throughput MCP workloads.
    """

    @staticmethod
    def sdk_version() -> str | None:
        if importlib.util.find_spec("mcp") is None:
            return None
        try:
            return importlib_metadata.version("mcp")
        except importlib_metadata.PackageNotFoundError:
            return None

    @staticmethod
    def _major_version(version: str | None) -> int | None:
        if not version:
            return None
        match = re.match(r"^\s*(\d+)", version)
        return int(match.group(1)) if match else None

    @staticmethod
    def _client_api_available() -> bool:
        try:
            from mcp import Client, StdioServerParameters  # noqa: F401
            from mcp.client.stdio import stdio_client  # noqa: F401
        except (ImportError, AttributeError):
            return False
        return True

    def available(self) -> bool:
        version = self.sdk_version()
        return self._major_version(version) == 2 and self._client_api_available()

    def _require_available(self) -> None:
        version = self.sdk_version()
        if version is None:
            raise RuntimeError('MCP SDK is not installed. Run: python -m pip install -e ".[mcp]"')
        if self._major_version(version) != 2:
            raise RuntimeError(
                f"Incompatible MCP SDK {version}. Bedrock requires MCP Python SDK v2; "
                'run: python -m pip install --upgrade -e ".[mcp]"'
            )
        if not self._client_api_available():
            raise RuntimeError(
                f"MCP SDK {version} is installed but its v2 client API is unavailable. "
                'Run: python -m pip install --upgrade -e ".[mcp]"'
            )

    @staticmethod
    def _transport(server: MCPServerDefinition):
        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client

        if server.transport == "http":
            return server.url
        if server.transport == "stdio":
            parameters = StdioServerParameters(
                command=server.command,
                args=list(server.args),
                env=dict(server.env or {}),
            )
            return stdio_client(parameters)
        raise ValueError(f"Unsupported MCP transport: {server.transport}")

    async def _list_tools_async(self, server: MCPServerDefinition) -> list[dict[str, Any]]:
        from mcp import Client

        async with Client(self._transport(server)) as client:
            output: list[dict[str, Any]] = []
            cursor: str | None = None
            while True:
                page = await client.list_tools(cursor=cursor)
                for tool in page.tools:
                    output.append(
                        {
                            "name": str(tool.name),
                            "title": str(tool.title or tool.name),
                            "description": str(tool.description or "MCP tool"),
                            "input_schema": _jsonable(tool.input_schema),
                        }
                    )
                cursor = page.next_cursor
                if cursor is None:
                    break
            return output

    async def _call_tool_async(
        self,
        server: MCPServerDefinition,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        from mcp import Client

        async with Client(self._transport(server)) as client:
            result = await client.call_tool(tool_name, arguments)
            return {
                "is_error": bool(result.is_error),
                "content": _jsonable(result.content),
                "structured_content": _jsonable(result.structured_content),
                "server": server.name,
                "tool": tool_name,
            }

    def list_tools(self, server: MCPServerDefinition) -> list[dict[str, Any]]:
        self._require_available()
        return asyncio.run(self._list_tools_async(server))

    def call_tool(
        self,
        server: MCPServerDefinition,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_available()
        return asyncio.run(self._call_tool_async(server, tool_name, arguments))


class MCPServerCatalog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._ensure()

    def _ensure(self) -> None:
        if self.path.exists():
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {
                    "note": "Imported MCP servers are disabled until the local user enables them.",
                    "servers": [],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        make_private_file(self.path)

    def _payload(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid MCP server configuration: {exc}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("servers", []), list):
            raise ValueError("MCP configuration must contain a servers array")
        return payload

    def _write(self, servers: list[dict[str, Any]]) -> None:
        payload = self._payload()
        payload["servers"] = servers
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)
        make_private_file(self.path)

    @staticmethod
    def _validate_http_url(url: str) -> str:
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("MCP HTTP URL must use http or https")
        if parsed.scheme == "http":
            host = parsed.hostname.casefold()
            loopback = host == "localhost"
            try:
                loopback = loopback or ipaddress.ip_address(host).is_loopback
            except ValueError:
                pass
            if not loopback:
                raise ValueError("Plain HTTP MCP is allowed only on localhost; use HTTPS remotely")
        if parsed.username or parsed.password:
            raise ValueError("MCP URLs cannot contain embedded credentials")
        return url.strip()

    @staticmethod
    def _from_row(row: dict[str, Any]) -> MCPServerDefinition:
        server_id = str(row.get("id", row.get("server_id", ""))).strip()
        name = str(row.get("name", server_id)).strip()
        transport = str(row.get("transport", "stdio")).strip().lower()
        if not _SERVER_ID.fullmatch(server_id):
            raise ValueError(f"Invalid MCP server id: {server_id!r}")
        if not name:
            raise ValueError("MCP server name cannot be empty")
        if transport == "stdio":
            command = str(row.get("command", "")).strip()
            if not command:
                raise ValueError(f"MCP stdio server {server_id} has no command")
            args = tuple(str(item) for item in row.get("args", []))
            raw_env = row.get("env", {})
            if not isinstance(raw_env, dict):
                raise ValueError("MCP env must be an object")
            env = {str(key): str(value) for key, value in raw_env.items()}
            return MCPServerDefinition(server_id, name, transport, bool(row.get("enabled", False)), command, args, env)
        if transport == "http":
            url = MCPServerCatalog._validate_http_url(str(row.get("url", "")))
            return MCPServerDefinition(server_id, name, transport, bool(row.get("enabled", False)), url=url)
        raise ValueError(f"Unsupported MCP transport: {transport}")

    @staticmethod
    def _to_row(server: MCPServerDefinition) -> dict[str, Any]:
        return {
            "id": server.server_id,
            "name": server.name,
            "transport": server.transport,
            "enabled": server.enabled,
            "command": server.command,
            "args": list(server.args),
            "env": dict(server.env or {}),
            "url": server.url,
        }

    def list_servers(self) -> list[MCPServerDefinition]:
        return [self._from_row(row) for row in self._payload().get("servers", []) if isinstance(row, dict)]

    def get(self, server_id: str) -> MCPServerDefinition:
        for server in self.list_servers():
            if server.server_id == server_id:
                return server
        raise KeyError(f"Unknown MCP server: {server_id}")

    def upsert(self, server: MCPServerDefinition) -> None:
        self._from_row(self._to_row(server))
        rows = [self._to_row(item) for item in self.list_servers() if item.server_id != server.server_id]
        rows.append(self._to_row(server))
        self._write(rows)

    def set_enabled(self, server_id: str, enabled: bool) -> None:
        current = self.get(server_id)
        self.upsert(MCPServerDefinition(**{**asdict(current), "enabled": bool(enabled)}))

    def remove(self, server_id: str) -> None:
        rows = [self._to_row(item) for item in self.list_servers() if item.server_id != server_id]
        self._write(rows)

    def add_http(self, *, server_id: str, name: str, url: str) -> MCPServerDefinition:
        server = MCPServerDefinition(
            server_id=server_id.strip(),
            name=name.strip(),
            transport="http",
            enabled=False,
            url=self._validate_http_url(url),
        )
        self.upsert(server)
        return server

    def import_file(self, source: Path) -> list[MCPServerDefinition]:
        payload = json.loads(source.read_text(encoding="utf-8"))
        imported: list[MCPServerDefinition] = []
        if isinstance(payload, dict) and isinstance(payload.get("mcpServers"), dict):
            rows: Iterable[tuple[str, Any]] = payload["mcpServers"].items()
            for server_id, raw in rows:
                if not isinstance(raw, dict):
                    continue
                name = str(raw.get("name", server_id))
                if raw.get("url"):
                    server = MCPServerDefinition(
                        server_id=str(server_id), name=name, transport="http", enabled=False,
                        url=self._validate_http_url(str(raw["url"])),
                    )
                else:
                    server = MCPServerDefinition(
                        server_id=str(server_id), name=name, transport="stdio", enabled=False,
                        command=str(raw.get("command", "")),
                        args=tuple(str(item) for item in raw.get("args", [])),
                        env={str(k): str(v) for k, v in dict(raw.get("env", {})).items()},
                    )
                self.upsert(server)
                imported.append(server)
            return imported
        if isinstance(payload, dict) and isinstance(payload.get("servers"), list):
            for raw in payload["servers"]:
                if not isinstance(raw, dict):
                    continue
                raw = {**raw, "enabled": False}
                server = self._from_row(raw)
                self.upsert(server)
                imported.append(server)
            return imported
        raise ValueError("Unsupported MCP config. Expected mcpServers object or servers array")


class MCPManager:
    TOOL_PREFIX = "mcp_"

    def __init__(
        self,
        catalog: MCPServerCatalog,
        registry: ToolRegistry,
        *,
        backend: MCPBackend | None = None,
    ) -> None:
        self.catalog = catalog
        self.registry = registry
        self.backend = backend or OfficialMCPBackend()
        self._tool_index: dict[str, tuple[str, str]] = {}

    @staticmethod
    def _tool_name(server_id: str, tool_name: str) -> str:
        clean_server = _TOOL_SAFE.sub("_", server_id).strip("_").lower()
        clean_tool = _TOOL_SAFE.sub("_", tool_name).strip("_").lower()
        candidate = f"mcp_{clean_server}_{clean_tool}"
        return candidate[:64]

    def sdk_available(self) -> bool:
        return self.backend.available()

    def server_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "id": server.server_id,
                "name": server.name,
                "transport": server.transport,
                "enabled": server.enabled,
                "endpoint": server.url if server.transport == "http" else " ".join((server.command, *server.args)),
            }
            for server in self.catalog.list_servers()
        ]

    def test_server(self, server_id: str) -> dict[str, Any]:
        server = self.catalog.get(server_id)
        tools = self.backend.list_tools(server)
        return {
            "server": server.name,
            "protocol": "MCP",
            "tool_count": len(tools),
            "tools": tools,
        }

    def sync_tools(self) -> dict[str, Any]:
        self.registry.unregister_prefix(self.TOOL_PREFIX)
        self._tool_index.clear()
        failures: list[dict[str, str]] = []
        registered: list[str] = []
        if not self.sdk_available():
            return {"registered": registered, "failures": failures, "sdk_available": False}
        for server in self.catalog.list_servers():
            if not server.enabled:
                continue
            try:
                remote_tools = self.backend.list_tools(server)
            except Exception as exc:
                failures.append({"server": server.server_id, "error": f"{type(exc).__name__}: {exc}"})
                continue
            for remote in remote_tools:
                remote_name = str(remote.get("name", "")).strip()
                if not remote_name:
                    continue
                local_name = self._tool_name(server.server_id, remote_name)
                schema = remote.get("input_schema")
                if not isinstance(schema, dict):
                    schema = {"type": "object", "properties": {}, "additionalProperties": True}
                description = (
                    f"MCP tool from {server.name}: "
                    f"{str(remote.get('description') or remote.get('title') or remote_name)}. "
                    "Every call requires local approval because the remote server controls its side effects."
                )

                def handler(arguments: dict[str, Any], *, sid=server.server_id, rname=remote_name):
                    selected = self.catalog.get(sid)
                    if not selected.enabled:
                        raise PermissionError(f"MCP server {sid} is disabled")
                    return self.backend.call_tool(selected, rname, arguments)

                self.registry.register(
                    Tool(
                        name=local_name,
                        description=description,
                        parameters=schema,
                        handler=handler,
                        risk=RiskLevel.EXTERNAL,
                    ),
                    replace=True,
                )
                self._tool_index[local_name] = (server.server_id, remote_name)
                registered.append(local_name)
        return {"registered": registered, "failures": failures, "sdk_available": True}
