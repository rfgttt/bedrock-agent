from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from bedrock_agent.security import make_private_dir, make_private_file
from bedrock_agent.tools.base import RiskLevel, Tool
from bedrock_agent.tools.builtin import Workspace


_TEXT_SUFFIXES = {
    ".py", ".pyi", ".toml", ".json", ".md", ".txt", ".yaml", ".yml", ".ini", ".cfg",
    ".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".sql", ".ps1", ".bat", ".cmd",
}


class CodingWorkspace:
    """Read, inspect and make exact reversible edits without executing project code."""

    def __init__(self, workspace: Workspace, backup_dir: Path) -> None:
        self.workspace = workspace
        self.backup_dir = make_private_dir(backup_dir)

    def _project(self, path: str) -> Path:
        project = self.workspace.resolve(path)
        if not project.is_dir():
            raise NotADirectoryError(path)
        return project

    @staticmethod
    def _iter_text_files(project: Path) -> Iterator[Path]:
        for path in project.rglob("*"):
            if (
                path.is_file()
                and path.suffix.casefold() in _TEXT_SUFFIXES
                and ".venv" not in path.parts
                and "node_modules" not in path.parts
                and "__pycache__" not in path.parts
            ):
                yield path

    def inspect(self, path: str = ".") -> dict[str, Any]:
        project = self._project(path)
        suffix_counts: dict[str, int] = {}
        total_bytes = 0
        text_file_count = 0
        for file in self._iter_text_files(project):
            text_file_count += 1
            suffix = file.suffix.casefold() or "<none>"
            suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
            total_bytes += file.stat().st_size
        top_level = sorted(
            str(item.relative_to(project)) + ("/" if item.is_dir() else "")
            for item in project.iterdir()
            if item.name not in {".venv", "node_modules", "__pycache__"}
        )[:100]
        return {
            "path": str(project.relative_to(self.workspace.root)),
            "text_files": text_file_count,
            "total_bytes": total_bytes,
            "extensions": dict(sorted(suffix_counts.items(), key=lambda item: (-item[1], item[0]))),
            "top_level": top_level,
            "has_pyproject": (project / "pyproject.toml").is_file(),
            "has_git": (project / ".git").exists(),
        }

    def search(self, query: str, path: str = ".", limit: int = 50) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            raise ValueError("query cannot be empty")
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        project = self._project(path)
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        matches: list[dict[str, Any]] = []
        for file in self._iter_text_files(project):
            if file.stat().st_size > 500_000:
                continue
            try:
                with file.open("r", encoding="utf-8") as stream:
                    for line_number, line in enumerate(stream, 1):
                        if pattern.search(line):
                            matches.append(
                                {
                                    "file": str(file.relative_to(self.workspace.root)),
                                    "line": line_number,
                                    "text": line.strip()[:500],
                                }
                            )
                            if len(matches) >= limit:
                                return matches
            except UnicodeDecodeError:
                continue
        return matches

    def syntax_check(self, path: str = ".") -> dict[str, Any]:
        project = self._project(path)
        checked = 0
        failures: list[dict[str, Any]] = []
        for file in project.rglob("*.py"):
            if ".venv" in file.parts or "__pycache__" in file.parts:
                continue
            checked += 1
            try:
                source = file.read_text(encoding="utf-8")
                compile(source, str(file), "exec")
            except (SyntaxError, UnicodeDecodeError) as exc:
                failures.append(
                    {
                        "file": str(file.relative_to(self.workspace.root)),
                        "line": getattr(exc, "lineno", None),
                        "error": str(exc),
                    }
                )
        return {"checked": checked, "passed": not failures, "failures": failures[:100]}

    def replace_exact(
        self,
        path: str,
        old_text: str,
        new_text: str,
        expected_count: int = 1,
    ) -> dict[str, Any]:
        if not old_text:
            raise ValueError("old_text cannot be empty")
        if not 1 <= expected_count <= 100:
            raise ValueError("expected_count must be between 1 and 100")
        target = self.workspace.resolve(path)
        if not target.is_file() or target.suffix.casefold() not in _TEXT_SUFFIXES:
            raise ValueError("Target must be an existing supported text/code file")
        if target.stat().st_size > 1_000_000:
            raise ValueError("Target file exceeds 1 MB")
        content = target.read_text(encoding="utf-8")
        actual_count = content.count(old_text)
        if actual_count != expected_count:
            raise ValueError(f"Exact replacement count mismatch: expected {expected_count}, found {actual_count}")
        backup_id = uuid.uuid4().hex
        backup_file = self.backup_dir / backup_id / path
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        backup_file.write_text(content, encoding="utf-8")
        make_private_file(backup_file)
        metadata = {
            "backup_id": backup_id,
            "path": path,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        meta_path = self.backup_dir / backup_id / "metadata.json"
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        make_private_file(meta_path)
        updated = content.replace(old_text, new_text, expected_count)
        target.write_text(updated, encoding="utf-8")
        return {
            "path": path,
            "replacements": actual_count,
            "backup_id": backup_id,
            "new_bytes": len(updated.encode("utf-8")),
        }

    def restore(self, backup_id: str) -> dict[str, Any]:
        if not backup_id.isalnum() or len(backup_id) > 64:
            raise ValueError("Invalid backup id")
        root = self.backup_dir / backup_id
        metadata_path = root / "metadata.json"
        if not metadata_path.is_file():
            raise FileNotFoundError(f"Unknown code backup: {backup_id}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        target = self.workspace.resolve(metadata["path"])
        backup_file = root / metadata["path"]
        if not backup_file.is_file():
            raise FileNotFoundError("Backup content is missing")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(backup_file.read_text(encoding="utf-8"), encoding="utf-8")
        return {"restored": True, "path": metadata["path"], "backup_id": backup_id}


def build_coding_tools(service: CodingWorkspace) -> list[Tool]:
    return [
        Tool(
            name="inspect_code_project",
            description="Inspect a project inside workspace without executing its code.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "additionalProperties": False,
            },
            handler=lambda arguments: service.inspect(arguments.get("path", ".")),
        ),
        Tool(
            name="search_code_text",
            description="Search supported text/code files inside workspace and return matching lines.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "path": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            handler=lambda arguments: service.search(
                arguments["query"], arguments.get("path", "."), arguments.get("limit", 50)
            ),
        ),
        Tool(
            name="check_python_syntax",
            description="Compile Python source text for syntax errors without importing or executing project modules.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "additionalProperties": False,
            },
            handler=lambda arguments: service.syntax_check(arguments.get("path", ".")),
        ),
        Tool(
            name="replace_code_text_exact",
            description=(
                "Replace an exact text fragment in a workspace code file, only when the occurrence count matches. "
                "Creates a private backup and requires local approval."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                    "expected_count": {"type": "integer"},
                },
                "required": ["path", "old_text", "new_text"],
                "additionalProperties": False,
            },
            handler=lambda arguments: service.replace_exact(
                arguments["path"],
                arguments["old_text"],
                arguments["new_text"],
                arguments.get("expected_count", 1),
            ),
            risk=RiskLevel.WRITE,
        ),
        Tool(
            name="restore_code_backup",
            description="Restore a file from a Bedrock code-edit backup. Requires local approval.",
            parameters={
                "type": "object",
                "properties": {"backup_id": {"type": "string"}},
                "required": ["backup_id"],
                "additionalProperties": False,
            },
            handler=lambda arguments: service.restore(arguments["backup_id"]),
            risk=RiskLevel.WRITE,
        ),
    ]
