from __future__ import annotations

from typing import Any

from .base import Tool


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        self._schema_cache: list[dict[str, Any]] | None = None
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool, *, replace: bool = False) -> None:
        if tool.name in self._tools and not replace:
            raise ValueError(f"Duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool
        self._schema_cache = None

    def contains(self, name: str) -> bool:
        return name in self._tools

    def unregister(self, name: str) -> None:
        if name in self._tools:
            del self._tools[name]
            self._schema_cache = None

    def unregister_prefix(self, prefix: str) -> list[str]:
        removed = [name for name in self._tools if name.startswith(prefix)]
        for name in removed:
            del self._tools[name]
        if removed:
            self._schema_cache = None
        return sorted(removed)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def schemas(self) -> list[dict[str, Any]]:
        # Tool schemas are immutable after Tool construction. Cache the provider
        # representation and invalidate only when a tool is registered/replaced.
        if self._schema_cache is None:
            self._schema_cache = [tool.provider_schema() for tool in self._tools.values()]
        return self._schema_cache

    def validate_arguments(self, tool: Tool, arguments: dict[str, Any]) -> None:
        if "_invalid_json" in arguments:
            raise ValueError("Model returned invalid JSON tool arguments")

        schema = tool.parameters
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for field in required:
            if field not in arguments:
                raise ValueError(f"Missing required argument: {field}")

        if schema.get("additionalProperties") is False:
            unknown = sorted(set(arguments) - set(properties))
            if unknown:
                raise ValueError(f"Unknown arguments: {', '.join(unknown)}")

        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
        }
        for key, value in arguments.items():
            expected_name = properties.get(key, {}).get("type")
            expected_type = type_map.get(expected_name)
            if expected_type is not None and not isinstance(value, expected_type):
                raise ValueError(
                    f"Argument {key!r} must be {expected_name}, got {type(value).__name__}"
                )
