from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bedrock_agent.security import make_private_dir, make_private_file

_SECRET_PATTERN = re.compile(r"(api[_-]?key|token|password|secret)", re.IGNORECASE)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***REDACTED***" if _SECRET_PATTERN.search(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


class TraceWriter:
    def __init__(self, directory: Path, *, file_limit: int = 500) -> None:
        self.directory = make_private_dir(directory)
        self.file_limit = max(50, file_limit)
        self._prune_old_files()

    def _prune_old_files(self) -> None:
        """Bound trace-file growth once at startup, not on every write."""

        files = sorted(
            self.directory.glob("*.jsonl"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for path in files[self.file_limit :]:
            try:
                path.unlink()
            except OSError:
                # Trace retention must never prevent the Agent from starting.
                continue

    def write(self, trace_id: str, event: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "event": event,
            "payload": _redact(payload),
        }
        path = self.directory / f"{trace_id}.jsonl"
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
        make_private_file(path)
