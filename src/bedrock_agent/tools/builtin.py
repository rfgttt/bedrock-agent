from __future__ import annotations

import ast
import operator
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import RiskLevel, Tool


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise PermissionError("Path escapes the configured workspace") from exc
        return candidate


_ALLOWED_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_calculate(expression: str) -> int | float:
    if len(expression) > 100:
        raise ValueError("Expression is too long")

    def evaluate(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINARY_OPERATORS:
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Pow) and (abs(left) > 1_000_000 or abs(right) > 12):
                raise ValueError("Exponent operation is too large")
            result = _ALLOWED_BINARY_OPERATORS[type(node.op)](left, right)
            if abs(result) > 10**15:
                raise ValueError("Result is too large")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPERATORS:
            return _ALLOWED_UNARY_OPERATORS[type(node.op)](evaluate(node.operand))
        raise ValueError("Only basic arithmetic is allowed")

    return evaluate(ast.parse(expression, mode="eval"))


def build_default_tools(workspace_path: Path) -> list[Tool]:
    workspace = Workspace(workspace_path)

    def current_time(_: dict[str, Any]) -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def calculate(arguments: dict[str, Any]) -> dict[str, int | float | str]:
        expression = arguments["expression"]
        return {"expression": expression, "result": _safe_calculate(expression)}

    def list_files(arguments: dict[str, Any]) -> list[str]:
        directory = workspace.resolve(arguments.get("directory", "."))
        if not directory.exists():
            raise FileNotFoundError(f"Directory does not exist: {arguments.get('directory', '.')}")
        if not directory.is_dir():
            raise NotADirectoryError(str(directory))
        return sorted(
            str(path.relative_to(workspace.root)) + ("/" if path.is_dir() else "")
            for path in directory.iterdir()
        )

    def read_text_file(arguments: dict[str, Any]) -> str:
        path = workspace.resolve(arguments["path"])
        if not path.is_file():
            raise FileNotFoundError(arguments["path"])
        if path.stat().st_size > 200_000:
            raise ValueError("File is too large; limit is 200 KB")
        return path.read_text(encoding="utf-8")

    def write_text_file(arguments: dict[str, Any]) -> dict[str, Any]:
        path = workspace.resolve(arguments["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        content = arguments["content"]
        if len(content.encode("utf-8")) > 200_000:
            raise ValueError("Content is too large; limit is 200 KB")
        path.write_text(content, encoding="utf-8")
        return {"path": str(path.relative_to(workspace.root)), "bytes": len(content.encode("utf-8"))}

    return [
        Tool(
            name="get_current_time",
            description="Get the current local date and time.",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            handler=current_time,
        ),
        Tool(
            name="calculator",
            description="Evaluate a basic arithmetic expression without using arbitrary code execution.",
            parameters={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
                "additionalProperties": False,
            },
            handler=calculate,
        ),
        Tool(
            name="list_workspace",
            description="List files in a directory inside the isolated workspace.",
            parameters={
                "type": "object",
                "properties": {"directory": {"type": "string"}},
                "additionalProperties": False,
            },
            handler=list_files,
        ),
        Tool(
            name="read_text_file",
            description="Read a UTF-8 text file inside the isolated workspace.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
            handler=read_text_file,
        ),
        Tool(
            name="write_text_file",
            description="Create or overwrite a UTF-8 text file inside the isolated workspace. Requires human approval.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            handler=write_text_file,
            risk=RiskLevel.WRITE,
        ),
    ]
