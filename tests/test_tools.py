from pathlib import Path

import pytest

from bedrock_agent.tools.builtin import Workspace, build_default_tools


def test_workspace_blocks_path_escape(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "workspace")
    with pytest.raises(PermissionError):
        workspace.resolve("../outside.txt")


def test_calculator_rejects_code_execution(tmp_path: Path) -> None:
    tools = {tool.name: tool for tool in build_default_tools(tmp_path / "workspace")}
    with pytest.raises(ValueError):
        tools["calculator"].handler({"expression": "__import__('os').system('echo bad')"})


def test_calculator_rejects_huge_exponent(tmp_path: Path) -> None:
    tools = {tool.name: tool for tool in build_default_tools(tmp_path / "workspace")}
    with pytest.raises(ValueError):
        tools["calculator"].handler({"expression": "9**999999"})
