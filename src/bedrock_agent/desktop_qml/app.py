from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QFont, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from bedrock_agent.bootstrap import build_runtime
from bedrock_agent.config import DEEPSEEK_BASE_URL, DEFAULT_DEEPSEEK_MODEL, Settings
from bedrock_agent.desktop_controller import DesktopController
from bedrock_agent.desktop_qml.viewmodel import BedrockViewModel
from bedrock_agent.domain import Message, Role
from bedrock_agent.model_config import DeepSeekConfig, EnvModelConfigStore


class PreviewController:
    """Read-only preview data used by packaging and QML smoke tests."""

    def __init__(self, root: Path) -> None:
        self.session_id = "preview-session"
        self._root = root
        self._messages = [
            Message(Role.USER, "帮我把 Python 项目导入工作区并检查语法。"),
            Message(Role.ASSISTANT, "我会先读取工作区结构，再执行只读语法检查。"),
            Message(Role.TOOL, '{"ok": true, "files": 18}', name="inspect_python_project"),
            Message(Role.ASSISTANT, "检查完成：18 个 Python 文件通过语法检查。"),
        ]

    def new_session(self) -> str:
        self.session_id = uuid.uuid4().hex
        self._messages = []
        return self.session_id

    def select_session(self, session_id: str) -> None:
        self.session_id = session_id

    def delete_session(self, session_id: str):
        deleted = len(self._messages) if session_id == self.session_id else 0
        if session_id == self.session_id:
            self.new_session()
        return {
            "deleted_session_id": session_id,
            "current_session_id": self.session_id,
            "replaced_current": deleted > 0,
            "messages": deleted,
            "approvals": 0,
        }

    def send(self, text: str):
        from bedrock_agent.domain import RunResult

        self._messages.extend([Message(Role.USER, text), Message(Role.ASSISTANT, "预览模式不会调用真实模型。")])
        return RunResult("completed", self.session_id, "preview-trace", output="预览完成")

    def resolve_approval(self, approval_id: str, approved: bool):
        from bedrock_agent.domain import RunResult

        return RunResult("completed", self.session_id, "preview-trace", output="审批已处理")

    def pending_approvals(self):
        return [{"approval_id": "approval-demo", "session_id": self.session_id, "tool": "launch_app", "arguments": {"app": "网易云音乐"}, "reason": "启动本地应用需要你的授权"}]

    def message_view(self):
        return list(self._messages), 0

    def sessions(self, limit: int = 100):
        return [
            {"session_id": self.session_id, "title": "检查 Python 项目", "updated_at": "刚刚", "message_count": len(self._messages)},
            {"session_id": "learning", "title": "30 天 Agent 学习计划", "updated_at": "今天", "message_count": 12},
            {"session_id": "research", "title": "pytest 资料整理", "updated_at": "昨天", "message_count": 8},
        ]

    def memories(self, query: str = "", limit: int = 100):
        return [{"memory_id": "m1", "kind": "preference", "content": "职业方向：Agent 应用开发与 AI 应用测试", "tags": ["career"], "importance": 5, "created_at": "2026-07-29"}]

    def skills(self):
        return [{"skill_id": "s1", "name": "daily_learning_note", "description": "创建带时间戳的学习笔记", "parameters": {}, "steps": [{}, {}], "risk": "medium", "status": "active"}]

    def trace_records(self, trace_id: str | None = None):
        return [{"event": "tool_call", "payload": {"tool": "inspect_python_project"}, "timestamp": "16:20:03"}]

    def allowed_apps(self, force_refresh: bool = False):
        return [
            {"display_name": "网易云音乐", "app": "cloudmusic", "path": "D:/Apps/CloudMusic/cloudmusic.exe", "source": "用户白名单", "aliases": ["网易云"]},
            {"display_name": "Visual Studio Code", "app": "vscode", "path": "C:/Apps/Code.exe", "source": "自动发现", "aliases": ["VS Code"]},
        ]

    def workspace_path(self):
        path = self._root / "workspace"
        path.mkdir(parents=True, exist_ok=True)
        (path / "README.md").write_text("preview", encoding="utf-8")
        return path

    def import_workspace_paths(self, sources, destination="imports"):
        return []

    def mcp_status(self):
        return {"sdk_available": True, "servers": [{"server_id": "filesystem", "name": "Filesystem MCP", "transport": "stdio", "enabled": False, "tool_count": 4}], "registered_tools": [], "config_path": "private/mcp_servers.json"}

    def learning_dashboard(self, days: int = 30):
        return {"total_minutes": 420, "completed_sessions": 8}

    def add_allowed_app(self, display_name, executable, aliases=None):
        return {}

    def remove_allowed_app(self, app):
        return None

    def import_mcp_config(self, source):
        return []

    def sync_mcp_tools(self):
        return {}

    def open_path(self, path):
        return None

    def close(self):
        return None


def _ensure_model_config(app: QApplication, env_path: Path) -> bool:
    store = EnvModelConfigStore(env_path)
    current = store.load()
    if current.api_key:
        return True
    QMessageBox.information(None, "配置 DeepSeek", "首次启动需要配置 DeepSeek API Key。密钥只保存在本机 .env 文件中。")
    key, ok = QInputDialog.getText(None, "DeepSeek API Key", "请输入 DeepSeek API Key：")
    if not ok or not key.strip():
        return False
    try:
        store.save(DeepSeekConfig(key.strip(), DEEPSEEK_BASE_URL, DEFAULT_DEEPSEEK_MODEL))
    except Exception as exc:  # noqa: BLE001
        QMessageBox.critical(None, "配置失败", str(exc))
        return False
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bedrock-desktop")
    parser.add_argument("--preview", action="store_true", help="Open the UI with safe preview data.")
    parser.add_argument("--ui-smoke", action="store_true", help="Load QML off-screen and exit automatically.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.ui_smoke:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Bedrock Agent")
    app.setOrganizationName("Bedrock")
    app.setFont(QFont("Microsoft YaHei UI", 10))

    package_root = Path(__file__).resolve().parent
    qml_path = package_root / "qml" / "Main.qml"
    if not qml_path.exists():
        QMessageBox.critical(None, "启动失败", f"QML 资源不存在：{qml_path}")
        return 2

    if args.preview or args.ui_smoke:
        controller: Any = PreviewController(Path.cwd())
    else:
        env_path = Path(os.getenv("BEDROCK_ENV_FILE", ".env"))
        if not _ensure_model_config(app, env_path):
            return 1
        try:
            controller = DesktopController(build_runtime(Settings.from_env(env_path)))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(None, "Bedrock 启动失败", str(exc))
            return 2

    view_model = BedrockViewModel(controller)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("bedrock", view_model)
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        view_model.close()
        return 3

    app.aboutToQuit.connect(view_model.close)
    if args.ui_smoke:
        QTimer.singleShot(700, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())


def preview_main() -> int:
    sys.argv = [sys.argv[0], "--preview", *sys.argv[1:]]
    return main()
