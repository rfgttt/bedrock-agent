from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePath
from typing import Any

from bedrock_agent.security import make_private_dir, make_private_file
from bedrock_agent.tools.base import RiskLevel, Tool
from bedrock_agent.tools.builtin import Workspace


_EXTENSION_BUCKETS = {
    "Documents": {".txt", ".md", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"},
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"},
    "Video": {".mp4", ".mkv", ".avi", ".mov", ".webm"},
    "Archives": {".zip", ".7z", ".rar", ".tar", ".gz"},
    "Code": {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".toml", ".yaml", ".yml", ".html", ".css", ".sql"},
}


class FileOrganizer:
    """Plans and applies reversible file moves inside the isolated workspace."""

    def __init__(self, workspace: Workspace, plan_dir: Path) -> None:
        self.workspace = workspace
        self.plan_dir = make_private_dir(plan_dir)

    @staticmethod
    def _bucket(path: Path) -> str:
        suffix = path.suffix.casefold()
        for bucket, extensions in _EXTENSION_BUCKETS.items():
            if suffix in extensions:
                return bucket
        return "Other"

    def _plan_path(self, plan_id: str) -> Path:
        if not plan_id.isalnum() or len(plan_id) > 64:
            raise ValueError("Invalid plan id")
        return self.plan_dir / f"{plan_id}.json"

    @staticmethod
    def _portable_path(path: PurePath) -> str:
        """Serialize internal relative paths with forward slashes on every OS."""
        return path.as_posix()

    @staticmethod
    def _digest(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def plan(self, directory: str = ".", strategy: str = "by_extension") -> dict[str, Any]:
        root = self.workspace.resolve(directory)
        if not root.is_dir():
            raise NotADirectoryError(directory)
        if strategy not in {"by_extension", "by_month"}:
            raise ValueError("strategy must be by_extension or by_month")
        files = [path for path in root.iterdir() if path.is_file()]
        if len(files) > 500:
            raise ValueError("A single organization plan may contain at most 500 files")
        operations: list[dict[str, str]] = []
        reserved_targets: set[Path] = set()
        for source in sorted(files, key=lambda path: path.name.casefold()):
            if strategy == "by_extension":
                folder = self._bucket(source)
            else:
                folder = datetime.fromtimestamp(source.stat().st_mtime).strftime("%Y-%m")
            target = root / folder / source.name
            counter = 1
            while target.exists() or target in reserved_targets:
                target = root / folder / f"{source.stem}_{counter}{source.suffix}"
                counter += 1
            reserved_targets.add(target)
            operations.append(
                {
                    "source": self._portable_path(source.relative_to(self.workspace.root)),
                    "target": self._portable_path(target.relative_to(self.workspace.root)),
                }
            )
        plan_id = uuid.uuid4().hex
        body = {
            "plan_id": plan_id,
            "directory": self._portable_path(root.relative_to(self.workspace.root)),
            "strategy": strategy,
            "status": "planned",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "operations": operations,
        }
        body["digest"] = self._digest(body)
        path = self._plan_path(plan_id)
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
        make_private_file(path)
        return body

    def _load(self, plan_id: str) -> dict[str, Any]:
        path = self._plan_path(plan_id)
        if not path.is_file():
            raise FileNotFoundError(f"Unknown organization plan: {plan_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        digest = payload.pop("digest", "")
        if digest != self._digest(payload):
            raise ValueError("Organization plan integrity check failed")
        payload["digest"] = digest
        return payload

    def apply(self, plan_id: str) -> dict[str, Any]:
        payload = self._load(plan_id)
        if payload["status"] != "planned":
            raise ValueError(f"Plan status is {payload['status']}, expected planned")
        completed: list[dict[str, str]] = []
        try:
            for operation in payload["operations"]:
                source = self.workspace.resolve(operation["source"])
                target = self.workspace.resolve(operation["target"])
                if not source.is_file():
                    raise FileNotFoundError(operation["source"])
                if target.exists():
                    raise FileExistsError(operation["target"])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(target))
                completed.append(operation)
        except Exception:
            for operation in reversed(completed):
                source = self.workspace.resolve(operation["source"])
                target = self.workspace.resolve(operation["target"])
                if target.exists() and not source.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(target), str(source))
            raise
        payload["status"] = "applied"
        payload["applied_at"] = datetime.now(timezone.utc).isoformat()
        payload_without_digest = {key: value for key, value in payload.items() if key != "digest"}
        payload["digest"] = self._digest(payload_without_digest)
        path = self._plan_path(plan_id)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        make_private_file(path)
        return {"plan_id": plan_id, "moved": len(completed), "operations": completed}

    def undo(self, plan_id: str) -> dict[str, Any]:
        payload = self._load(plan_id)
        if payload["status"] != "applied":
            raise ValueError(f"Plan status is {payload['status']}, expected applied")
        restored: list[dict[str, str]] = []
        for operation in reversed(payload["operations"]):
            original = self.workspace.resolve(operation["source"])
            current = self.workspace.resolve(operation["target"])
            if not current.is_file():
                raise FileNotFoundError(operation["target"])
            if original.exists():
                raise FileExistsError(operation["source"])
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(current), str(original))
            restored.append(operation)
        payload["status"] = "undone"
        payload["undone_at"] = datetime.now(timezone.utc).isoformat()
        payload_without_digest = {key: value for key, value in payload.items() if key != "digest"}
        payload["digest"] = self._digest(payload_without_digest)
        path = self._plan_path(plan_id)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        make_private_file(path)
        return {"plan_id": plan_id, "restored": len(restored)}


def build_file_organizer_tools(service: FileOrganizer) -> list[Tool]:
    return [
        Tool(
            name="plan_workspace_organization",
            description=(
                "Create a preview-only, reversible plan to organize files in one workspace directory. "
                "Strategies: by_extension or by_month. Does not move files."
            ),
            parameters={
                "type": "object",
                "properties": {"directory": {"type": "string"}, "strategy": {"type": "string"}},
                "additionalProperties": False,
            },
            handler=lambda arguments: service.plan(
                arguments.get("directory", "."), arguments.get("strategy", "by_extension")
            ),
        ),
        Tool(
            name="apply_workspace_organization",
            description="Apply a previously previewed organization plan. Requires local approval.",
            parameters={
                "type": "object",
                "properties": {"plan_id": {"type": "string"}},
                "required": ["plan_id"],
                "additionalProperties": False,
            },
            handler=lambda arguments: service.apply(arguments["plan_id"]),
            risk=RiskLevel.WRITE,
        ),
        Tool(
            name="undo_workspace_organization",
            description="Undo an applied organization plan when its target files are unchanged. Requires local approval.",
            parameters={
                "type": "object",
                "properties": {"plan_id": {"type": "string"}},
                "required": ["plan_id"],
                "additionalProperties": False,
            },
            handler=lambda arguments: service.undo(arguments["plan_id"]),
            risk=RiskLevel.WRITE,
        ),
    ]
