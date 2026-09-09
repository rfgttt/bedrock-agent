from __future__ import annotations

from pathlib import Path

import pytest

from bedrock_agent.capabilities.workspace_import import WorkspaceImportService
from bedrock_agent.tools.builtin import Workspace


def test_user_selected_files_and_folders_are_copied_into_workspace(tmp_path: Path) -> None:
    source_file = tmp_path / "outside" / "notes.txt"
    source_file.parent.mkdir()
    source_file.write_text("hello", encoding="utf-8")
    source_dir = tmp_path / "project"
    source_dir.mkdir()
    (source_dir / "main.py").write_text("print('ok')", encoding="utf-8")

    service = WorkspaceImportService(Workspace(tmp_path / "workspace"))
    result = service.import_paths([source_file, source_dir])

    assert [row.target for row in result] == ["imports/notes.txt", "imports/project"]
    assert (service.root / "imports" / "notes.txt").read_text(encoding="utf-8") == "hello"
    assert (service.root / "imports" / "project" / "main.py").exists()
    assert source_file.exists()
    assert source_dir.exists()


def test_workspace_import_avoids_overwrite_and_self_import(tmp_path: Path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("one", encoding="utf-8")
    service = WorkspaceImportService(Workspace(tmp_path / "workspace"))

    first = service.import_paths([source])
    second = service.import_paths([source])

    assert first[0].target == "imports/a.txt"
    assert second[0].target == "imports/a (1).txt"
    with pytest.raises(ValueError):
        service.import_paths([service.root])
