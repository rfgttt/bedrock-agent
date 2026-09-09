from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from bedrock_agent.tools.builtin import Workspace


@dataclass(frozen=True, slots=True)
class ImportResult:
    source: str
    target: str
    kind: str
    bytes_copied: int


class WorkspaceImportService:
    """Copies user-selected files into the isolated Bedrock workspace.

    This service is intentionally UI-driven rather than model-driven. The user
    selects concrete paths with the operating-system file picker, so the model
    never receives arbitrary host filesystem access.
    """

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    @property
    def root(self) -> Path:
        return self.workspace.root

    def _ensure_outside_workspace(self, source: Path) -> None:
        resolved = source.resolve()
        root = self.root.resolve()
        if resolved == root or root in resolved.parents:
            raise ValueError("Cannot import the workspace into itself")

    @staticmethod
    def _safe_name(name: str) -> str:
        value = name.strip().rstrip(". ")
        if not value or value in {".", ".."}:
            raise ValueError("Invalid import name")
        return value

    def _unique_target(self, parent: Path, name: str) -> Path:
        name = self._safe_name(name)
        candidate = parent / name
        if not candidate.exists():
            return candidate
        source = Path(name)
        stem = source.stem or source.name
        suffix = source.suffix
        for index in range(1, 10_000):
            candidate = parent / f"{stem} ({index}){suffix}"
            if not candidate.exists():
                return candidate
        raise FileExistsError(f"Unable to choose a unique target for {name}")

    @staticmethod
    def _assert_no_links(path: Path) -> None:
        if path.is_symlink():
            raise ValueError(f"Symbolic links are not imported: {path}")
        try:
            if os.name == "nt" and path.stat().st_file_attributes & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT
                raise ValueError(f"Windows reparse points are not imported: {path}")
        except AttributeError:
            pass

    def _copy_file(self, source: Path, destination: Path) -> int:
        self._assert_no_links(source)
        if not source.is_file():
            raise ValueError(f"Not a regular file: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination.stat().st_size

    def _copy_directory(self, source: Path, destination: Path) -> int:
        self._assert_no_links(source)
        if not source.is_dir():
            raise ValueError(f"Not a directory: {source}")
        total = 0
        destination.mkdir(parents=True, exist_ok=False)
        for current, directories, files in os.walk(source, topdown=True, followlinks=False):
            current_path = Path(current)
            self._assert_no_links(current_path)
            relative = current_path.relative_to(source)
            target_current = destination / relative
            target_current.mkdir(parents=True, exist_ok=True)

            allowed_directories: list[str] = []
            for directory in directories:
                child = current_path / directory
                self._assert_no_links(child)
                allowed_directories.append(directory)
            directories[:] = allowed_directories

            for filename in files:
                child = current_path / filename
                self._assert_no_links(child)
                target = target_current / filename
                total += self._copy_file(child, target)
        return total

    def import_paths(
        self,
        sources: Iterable[Path],
        *,
        destination: str = "imports",
    ) -> list[ImportResult]:
        selected = [Path(source).expanduser() for source in sources]
        if not selected:
            raise ValueError("No files or folders were selected")
        destination_root = self.workspace.resolve(destination)
        destination_root.mkdir(parents=True, exist_ok=True)

        results: list[ImportResult] = []
        for source in selected:
            if not source.exists():
                raise FileNotFoundError(source)
            self._ensure_outside_workspace(source)
            target = self._unique_target(destination_root, source.name)
            try:
                if source.is_dir():
                    copied = self._copy_directory(source, target)
                    kind = "directory"
                else:
                    copied = self._copy_file(source, target)
                    kind = "file"
            except Exception:
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                elif target.exists():
                    target.unlink(missing_ok=True)
                raise
            results.append(
                ImportResult(
                    source=str(source.resolve()),
                    target=target.relative_to(self.root).as_posix(),
                    kind=kind,
                    bytes_copied=copied,
                )
            )
        return results
