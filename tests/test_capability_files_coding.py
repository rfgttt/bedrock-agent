from __future__ import annotations

from pathlib import Path, PureWindowsPath

import pytest

from bedrock_agent.capabilities.coding import CodingWorkspace
from bedrock_agent.capabilities.file_organizer import FileOrganizer
from bedrock_agent.tools.builtin import Workspace


def test_file_organization_is_previewed_applied_and_undoable(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "workspace")
    (workspace.root / "photo.png").write_text("image", encoding="utf-8")
    (workspace.root / "notes.md").write_text("notes", encoding="utf-8")
    organizer = FileOrganizer(workspace, tmp_path / "private" / "plans")

    plan = organizer.plan(".", "by_extension")
    assert (workspace.root / "photo.png").exists()
    assert {row["target"] for row in plan["operations"]} == {"Images/photo.png", "Documents/notes.md"}

    applied = organizer.apply(plan["plan_id"])
    assert applied["moved"] == 2
    assert (workspace.root / "Images" / "photo.png").is_file()

    organizer.undo(plan["plan_id"])
    assert (workspace.root / "photo.png").is_file()
    assert not (workspace.root / "Images" / "photo.png").exists()


def test_file_plan_paths_use_portable_forward_slashes() -> None:
    assert FileOrganizer._portable_path(PureWindowsPath("Documents", "notes.md")) == "Documents/notes.md"


def test_code_tools_inspect_check_edit_and_restore(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "workspace")
    project = workspace.root / "demo"
    project.mkdir()
    code = project / "main.py"
    code.write_text("def answer():\n    return 41\n", encoding="utf-8")
    service = CodingWorkspace(workspace, tmp_path / "private" / "code_backups")

    assert service.inspect("demo")["text_files"] == 1
    assert service.search("return 41", "demo")[0]["line"] == 2
    assert service.syntax_check("demo")["passed"] is True

    edited = service.replace_exact("demo/main.py", "return 41", "return 42")
    assert "return 42" in code.read_text(encoding="utf-8")
    service.restore(edited["backup_id"])
    assert "return 41" in code.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="count mismatch"):
        service.replace_exact("demo/main.py", "missing", "x")


def test_python_syntax_check_does_not_execute_code(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "workspace")
    project = workspace.root / "demo"
    project.mkdir()
    marker = tmp_path / "executed.txt"
    (project / "danger.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n",
        encoding="utf-8",
    )
    service = CodingWorkspace(workspace, tmp_path / "private" / "code_backups")

    assert service.syntax_check("demo")["passed"] is True
    assert not marker.exists()
