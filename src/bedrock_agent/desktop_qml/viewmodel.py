from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from bedrock_agent.desktop_controller import DesktopController
from bedrock_agent.config import DEEPSEEK_BASE_URL, DEEPSEEK_MODELS
from bedrock_agent.model_config import DeepSeekConfig, EnvModelConfigStore
from bedrock_agent.domain import Message, Role, RunResult
from bedrock_agent.desktop_qml.help_catalog import help_presets
from bedrock_agent.desktop_qml.models import StableListModel
from bedrock_agent.desktop_qml.ui_theme import THEMES, ThemePreferenceStore, theme_rows


class BedrockViewModel(QObject):
    statusChanged = Signal()
    busyChanged = Signal()
    currentPageChanged = Signal()
    currentSessionChanged = Signal()
    draftTextChanged = Signal()
    dashboardChanged = Signal()
    agentPanelChanged = Signal()
    notification = Signal(str, str)
    requestScrollToEnd = Signal()
    themeChanged = Signal()
    deleteSessionRequested = Signal(str, str)
    _workerFinished = Signal(str, int, object, object)

    def __init__(self, controller: DesktopController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._status = "就绪"
        self._busy = False
        self._current_page = "dashboard"
        self._current_session = controller.session_id
        self._draft_text = ""
        self._dashboard: dict[str, Any] = {}
        self._agent_panel: dict[str, Any] = {
            "state": "待命",
            "step": "等待你的指令",
            "tool": "—",
            "risk": "安全",
            "trace": "—",
        }
        data_dir = (
            controller.runtime.settings.data_dir
            if hasattr(controller, "runtime")
            else Path.cwd() / "private"
        )
        self._theme_store = ThemePreferenceStore(Path(data_dir) / "ui_preferences.json")
        self._current_theme = self._theme_store.load()
        self._theme_data: dict[str, Any] = dict(THEMES[self._current_theme])
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="bedrock-ui")
        self._closing = False
        self._generation = 0
        self._active_jobs: dict[str, int] = {}
        self._refresh_lock = threading.Lock()

        self._sessionsModel = StableListModel(("session_id", "title", "updated_at", "message_count"), self)
        self._messagesModel = StableListModel(("role", "title", "message_text", "summary", "payload", "accent"), self)
        self._approvalsModel = StableListModel(("approval_id", "session_id", "tool", "reason", "arguments", "risk"), self)
        self._appsModel = StableListModel(("name", "key", "path", "status", "source", "aliases"), self)
        self._skillsModel = StableListModel(("skill_id", "name", "description", "risk", "status", "steps"), self)
        self._mcpModel = StableListModel(("server_id", "name", "transport", "server_enabled", "status", "tools", "error"), self)
        self._memoriesModel = StableListModel(("memory_id", "kind", "content", "tags", "importance", "created_at"), self)
        self._tracesModel = StableListModel(("event", "title", "detail", "time", "level"), self)
        self._workspaceModel = StableListModel(("name", "path", "kind", "size", "modified"), self)
        self._helpModel = StableListModel(("preset_id", "title", "description", "prompt", "category", "risk", "needs_approval", "requirement"), self)
        self._tasksModel = StableListModel(("title", "subtitle", "state", "progress", "accent", "session_id"), self)
        self._themeOptionsModel = StableListModel(("theme_id", "label", "description", "layout", "dark", "accent", "surface", "bg"), self)
        self._helpModel.set_rows(help_presets(), force=True)
        self._themeOptionsModel.set_rows(theme_rows(), force=True)

        self._workerFinished.connect(self._on_worker_finished)
        self.refreshAll()

    @Property(QObject, constant=True)
    def sessionsModel(self) -> QObject:  # noqa: N802
        return self._sessionsModel

    @Property(QObject, constant=True)
    def messagesModel(self) -> QObject:  # noqa: N802
        return self._messagesModel

    @Property(QObject, constant=True)
    def approvalsModel(self) -> QObject:  # noqa: N802
        return self._approvalsModel

    @Property(QObject, constant=True)
    def appsModel(self) -> QObject:  # noqa: N802
        return self._appsModel

    @Property(QObject, constant=True)
    def skillsModel(self) -> QObject:  # noqa: N802
        return self._skillsModel

    @Property(QObject, constant=True)
    def mcpModel(self) -> QObject:  # noqa: N802
        return self._mcpModel

    @Property(QObject, constant=True)
    def memoriesModel(self) -> QObject:  # noqa: N802
        return self._memoriesModel

    @Property(QObject, constant=True)
    def tracesModel(self) -> QObject:  # noqa: N802
        return self._tracesModel

    @Property(QObject, constant=True)
    def workspaceModel(self) -> QObject:  # noqa: N802
        return self._workspaceModel

    @Property(QObject, constant=True)
    def helpModel(self) -> QObject:  # noqa: N802
        return self._helpModel

    @Property(QObject, constant=True)
    def tasksModel(self) -> QObject:  # noqa: N802
        return self._tasksModel

    @Property(QObject, constant=True)
    def themeOptionsModel(self) -> QObject:  # noqa: N802
        return self._themeOptionsModel

    @Property(str, notify=themeChanged)
    def currentTheme(self) -> str:  # noqa: N802
        return self._current_theme

    @Property("QVariantMap", notify=themeChanged)
    def themeData(self) -> dict[str, Any]:  # noqa: N802
        return dict(self._theme_data)

    @Property(str, notify=statusChanged)
    def statusText(self) -> str:  # noqa: N802
        return self._status

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=currentPageChanged)
    def currentPage(self) -> str:  # noqa: N802
        return self._current_page

    @Property(str, notify=currentSessionChanged)
    def currentSession(self) -> str:  # noqa: N802
        return self._current_session

    @Property(str, notify=draftTextChanged)
    def draftText(self) -> str:  # noqa: N802
        return self._draft_text

    @draftText.setter
    def draftText(self, value: str) -> None:  # noqa: N802
        if value == self._draft_text:
            return
        self._draft_text = value
        self.draftTextChanged.emit()

    @Property("QVariantMap", notify=dashboardChanged)
    def dashboard(self) -> dict[str, Any]:
        return dict(self._dashboard)

    @Property("QVariantMap", notify=agentPanelChanged)
    def agentPanel(self) -> dict[str, Any]:  # noqa: N802
        return dict(self._agent_panel)

    @Property(str, constant=True)
    def workspacePath(self) -> str:  # noqa: N802
        return str(self.controller.workspace_path())

    def _set_status(self, value: str) -> None:
        if value == self._status:
            return
        self._status = value
        self.statusChanged.emit()

    def _set_busy(self, value: bool) -> None:
        if value == self._busy:
            return
        self._busy = value
        self.busyChanged.emit()

    def _set_agent_panel(self, **changes: Any) -> None:
        updated = dict(self._agent_panel)
        updated.update(changes)
        if updated == self._agent_panel:
            return
        self._agent_panel = updated
        self.agentPanelChanged.emit()

    def _dispatch(self, name: str, function: Callable[[], Any], *, status: str, blocking: bool = True) -> None:
        if self._closing:
            return
        self._generation += 1
        generation = self._generation
        self._active_jobs[name] = generation
        if blocking:
            self._set_busy(True)
        self._set_status(status)

        def run() -> None:
            try:
                result = function()
                self._workerFinished.emit(name, generation, result, None)
            except Exception as exc:  # noqa: BLE001 - surfaced to the UI
                self._workerFinished.emit(name, generation, None, exc)

        self._executor.submit(run)

    @Slot(str, int, object, object)
    def _on_worker_finished(self, name: str, generation: int, result: Any, error: Any) -> None:
        if self._active_jobs.get(name) != generation:
            return
        self._active_jobs.pop(name, None)
        if not self._active_jobs:
            self._set_busy(False)
        if error is not None:
            message = str(error)
            self._set_status("操作失败")
            self._set_agent_panel(state="失败", step=message[:120], risk="错误")
            self.notification.emit("操作失败", message)
            return

        if name in {"send", "approve", "reject"}:
            self._handle_run_result(result)
            if name in {"approve", "reject"} and result is not None:
                self.selectSession(result.session_id)
        elif name == "apps":
            self._apply_apps(result)
        elif name == "mcp":
            self._apply_mcp(result)
        elif name == "workspace":
            self._workspaceModel.set_rows(result)
        elif name == "import":
            self.notification.emit("导入完成", f"已导入 {len(result)} 项到 workspace/imports")
            self.refreshWorkspace()
        elif name == "dashboard":
            self._apply_dashboard(result)
        elif name == "reconfigure":
            self.notification.emit("模型已重载", "DeepSeek 配置已保存并在当前进程生效")
        elif name == "model_probe":
            self.notification.emit("连接测试成功", json.dumps(result, ensure_ascii=False, default=str))
        elif name == "delete_session":
            self._current_session = str(result.get("current_session_id") or self.controller.session_id)
            self.currentSessionChanged.emit()
            self._messagesModel.clear()
            self.refreshSessions()
            self.refreshChat()
            self.refreshApprovals()
            self.refreshDashboard()
            self.notification.emit(
                "会话已删除",
                f"已删除 {result.get('messages', 0)} 条消息；长期记忆、Skills 和工作区未受影响",
            )
            self.openPage("chat")
        self._set_status("就绪")

    def _handle_run_result(self, result: RunResult) -> None:
        if result is None:
            return
        self._current_session = result.session_id
        self.currentSessionChanged.emit()
        if result.status == "pending_approval" and result.pending_approval:
            pending = result.pending_approval
            self._set_agent_panel(
                state="等待审批",
                step=pending.reason,
                tool=pending.tool_call.name,
                risk="需要确认",
                trace=result.trace_id,
            )
            self.notification.emit("等待审批", f"{pending.tool_call.name} 正在等待你的决定")
            self.openPage("approvals")
        elif result.status == "completed":
            self._set_agent_panel(state="已完成", step=result.output or "任务完成", tool="—", risk="安全", trace=result.trace_id)
        elif result.status == "error":
            self._set_agent_panel(state="失败", step=result.error or "未知错误", risk="错误", trace=result.trace_id)
        self.refreshChat()
        self.refreshApprovals()
        self.refreshDashboard()
        self.requestScrollToEnd.emit()

    @staticmethod
    def _message_rows(messages: list[Message], truncated: int = 0) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if truncated:
            rows.append({"role": "system", "title": "历史已折叠", "message_text": f"更早的 {truncated} 条消息仍保存在本地数据库中。", "summary": "", "payload": "", "accent": "muted"})
        for message in messages:
            role = message.role.value
            if role == Role.USER.value:
                rows.append({"role": role, "title": "你", "message_text": message.content or "", "summary": "", "payload": "", "accent": "blue"})
            elif role == Role.ASSISTANT.value:
                if message.content:
                    rows.append({"role": role, "title": "Bedrock", "message_text": message.content, "summary": "", "payload": "", "accent": "green"})
                for call in message.tool_calls:
                    payload = json.dumps(call.arguments, ensure_ascii=False, indent=2, default=str)
                    summary = BedrockViewModel._tool_summary(call.name, call.arguments)
                    rows.append({"role": "tool_request", "title": f"请求工具 · {call.name}", "message_text": summary, "summary": summary, "payload": payload, "accent": "amber"})
            elif role == Role.TOOL.value:
                body = message.content or ""
                summary = body if len(body) <= 220 else body[:220] + "…"
                rows.append({"role": role, "title": f"工具结果 · {message.name or 'tool'}", "message_text": summary, "summary": summary, "payload": body, "accent": "muted"})
            else:
                rows.append({"role": role, "title": "系统", "message_text": message.content or "", "summary": "", "payload": message.content or "", "accent": "red"})
        return rows

    @staticmethod
    def _tool_summary(name: str, arguments: dict[str, Any]) -> str:
        if not arguments:
            return "无参数"
        friendly = []
        for key, value in list(arguments.items())[:5]:
            if isinstance(value, list):
                rendered = f"{len(value)} 项"
            elif isinstance(value, dict):
                rendered = f"{len(value)} 个字段"
            else:
                rendered = str(value)
                if len(rendered) > 80:
                    rendered = rendered[:80] + "…"
            friendly.append(f"{key}: {rendered}")
        suffix = "" if len(arguments) <= 5 else f" · 另有 {len(arguments) - 5} 个参数"
        return " · ".join(friendly) + suffix

    def _set_message_rows_incremental(self, rows: list[dict[str, Any]]) -> None:
        existing = self._messagesModel.rows()
        if len(existing) <= len(rows) and existing == rows[: len(existing)]:
            self._messagesModel.append_rows(rows[len(existing) :])
        else:
            self._messagesModel.set_rows(rows)

    @Slot()
    def refreshAll(self) -> None:  # noqa: N802
        self.refreshSessions()
        self.refreshChat()
        self.refreshApprovals()
        self.refreshDashboard()

    @Slot(str)
    def openPage(self, page: str) -> None:  # noqa: N802
        if page != self._current_page:
            self._current_page = page
            self.currentPageChanged.emit()
        refreshers = {
            "dashboard": self.refreshDashboard,
            "chat": self.refreshChat,
            "approvals": self.refreshApprovals,
            "workspace": self.refreshWorkspace,
            "apps": self.refreshApps,
            "learning": self.refreshDashboard,
            "skills": self.refreshSkills,
            "mcp": self.refreshMcp,
            "memory": self.refreshMemories,
            "traces": self.refreshTraces,
        }
        refresher = refreshers.get(page)
        if refresher:
            refresher()

    @Slot()
    def newSession(self) -> None:  # noqa: N802
        self._current_session = self.controller.new_session()
        self.currentSessionChanged.emit()
        self._messagesModel.clear()
        self._set_agent_panel(state="待命", step="新会话已创建", tool="—", risk="安全", trace="—")
        self.refreshSessions()
        self.openPage("chat")

    @Slot(str)
    def selectSession(self, session_id: str) -> None:  # noqa: N802
        if not session_id or self._busy:
            return
        if session_id == self._current_session:
            # Navigation is still meaningful when the requested session is
            # already selected (for example, after resolving an approval).
            self.openPage("chat")
            self.requestScrollToEnd.emit()
            return
        self.controller.select_session(session_id)
        self._current_session = session_id
        self.currentSessionChanged.emit()
        self._messagesModel.clear()
        self.openPage("chat")
        self.requestScrollToEnd.emit()

    @Slot(str)
    def sendMessage(self, text: str) -> None:  # noqa: N802
        text = text.strip()
        if not text or self._busy:
            return
        self.draftText = ""
        self._messagesModel.append_rows([{"role": "user", "title": "你", "message_text": text, "summary": "", "payload": "", "accent": "blue"}])
        self._set_agent_panel(state="运行中", step="正在理解任务并选择工具", tool="分析中", risk="评估中")
        self.requestScrollToEnd.emit()
        self._dispatch("send", lambda: self.controller.send(text), status="Agent 正在运行…")

    @Slot(str, bool)
    def resolveApproval(self, approval_id: str, approved: bool) -> None:  # noqa: N802
        if self._busy or not approval_id:
            return
        name = "approve" if approved else "reject"
        self._set_agent_panel(state="运行中", step="正在恢复审批后的任务", risk="已授权" if approved else "已拒绝")
        self._dispatch(name, lambda: self.controller.resolve_approval(approval_id, approved), status="正在恢复任务…")

    @Slot(int, bool)
    def usePreset(self, row: int, run_now: bool = False) -> None:  # noqa: N802
        item = self._helpModel.get(row)
        if not item:
            return
        prompt = str(item.get("prompt") or "")
        self.draftText = prompt
        self.openPage("chat")
        if run_now:
            self.sendMessage(prompt)

    @Slot(str)
    def setTheme(self, theme_id: str) -> None:  # noqa: N802
        selected = theme_id.strip().lower()
        if selected not in THEMES or selected == self._current_theme:
            return
        self._theme_store.save(selected)
        self._current_theme = selected
        self._theme_data = dict(THEMES[selected])
        self.themeChanged.emit()
        self.notification.emit("主题已切换", str(self._theme_data.get("label") or selected))

    @Slot()
    def cycleTheme(self) -> None:  # noqa: N802
        order = ("cel", "glass", "wechat", "codex")
        index = order.index(self._current_theme) if self._current_theme in order else 0
        self.setTheme(order[(index + 1) % len(order)])

    @Slot(str, str)
    def requestDeleteSession(self, session_id: str, title: str = "") -> None:  # noqa: N802
        if not session_id or self._busy:
            return
        self.deleteSessionRequested.emit(session_id, title or "这个会话")

    @Slot(str)
    def confirmDeleteSession(self, session_id: str) -> None:  # noqa: N802
        if not session_id or self._busy:
            return
        self._dispatch(
            "delete_session",
            lambda: self.controller.delete_session(session_id),
            status="正在删除会话…",
        )

    @Slot()
    def refreshSessions(self) -> None:  # noqa: N802
        rows = self.controller.sessions(limit=80)
        self._sessionsModel.set_rows(rows)

    @Slot()
    def refreshChat(self) -> None:  # noqa: N802
        messages, truncated = self.controller.message_view()
        self._set_message_rows_incremental(self._message_rows(messages, truncated))

    @Slot()
    def refreshApprovals(self) -> None:  # noqa: N802
        rows = []
        for item in self.controller.pending_approvals():
            rows.append({
                **item,
                "arguments": json.dumps(item.get("arguments", {}), ensure_ascii=False, indent=2, default=str),
                "risk": "外部/写入操作",
            })
        self._approvalsModel.set_rows(rows)

    @Slot()
    def refreshApps(self) -> None:  # noqa: N802
        self._dispatch("apps", lambda: self.controller.allowed_apps(force_refresh=False), status="正在读取应用白名单…", blocking=False)

    def _apply_apps(self, rows: list[dict[str, Any]]) -> None:
        normalized = []
        for item in rows:
            path = str(item.get("path") or item.get("executable") or "")
            normalized.append({
                "name": item.get("display_name") or item.get("name") or item.get("app") or "未命名应用",
                "key": item.get("app") or item.get("key") or item.get("name") or "",
                "path": path,
                "status": "可用" if path else "未发现",
                "source": item.get("source") or "白名单",
                "aliases": ", ".join(item.get("aliases") or []),
            })
        self._appsModel.set_rows(normalized)

    @Slot()
    def addApplication(self) -> None:  # noqa: N802
        filename, _ = QFileDialog.getOpenFileName(None, "选择可信应用", "", "Windows 应用 (*.exe *.lnk)")
        if not filename:
            return
        default = Path(filename).stem
        name, ok = QInputDialog.getText(None, "应用名称", "给这个应用起一个容易说出的名称：", text=default)
        if not ok or not name.strip():
            return
        try:
            self.controller.add_allowed_app(name.strip(), Path(filename))
            self.notification.emit("应用已添加", f"以后可以说：打开{name.strip()}")
            self.refreshApps()
        except Exception as exc:  # noqa: BLE001
            self.notification.emit("添加失败", str(exc))

    @Slot(str)
    def removeApplication(self, key: str) -> None:  # noqa: N802
        if not key:
            return
        try:
            self.controller.remove_allowed_app(key)
            self.refreshApps()
        except Exception as exc:  # noqa: BLE001
            self.notification.emit("删除失败", str(exc))

    @Slot(str)
    def requestLaunchApplication(self, name: str) -> None:  # noqa: N802
        if not name:
            return
        self.sendMessage(f"打开{name}。")

    @Slot()
    def refreshWorkspace(self) -> None:  # noqa: N802
        root = self.controller.workspace_path()

        def scan() -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            for path in sorted(root.rglob("*"), key=lambda p: (not p.is_dir(), str(p).lower()))[:500]:
                try:
                    stat = path.stat()
                except OSError:
                    continue
                rows.append({
                    "name": path.name,
                    "path": path.relative_to(root).as_posix(),
                    "kind": "文件夹" if path.is_dir() else "文件",
                    "size": "" if path.is_dir() else self._format_size(stat.st_size),
                    "modified": str(int(stat.st_mtime)),
                })
            return rows

        self._dispatch("workspace", scan, status="正在读取工作区…", blocking=False)

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024
        return f"{size} B"

    @Slot()
    def openWorkspace(self) -> None:  # noqa: N802
        self.controller.open_path(self.controller.workspace_path())

    @Slot()
    def importFiles(self) -> None:  # noqa: N802
        files, _ = QFileDialog.getOpenFileNames(None, "导入文件到工作区", "")
        if files:
            paths = [Path(item) for item in files]
            self._dispatch("import", lambda: self.controller.import_workspace_paths(paths), status="正在导入文件…")

    @Slot()
    def importFolder(self) -> None:  # noqa: N802
        folder = QFileDialog.getExistingDirectory(None, "导入文件夹到工作区")
        if folder:
            path = Path(folder)
            self._dispatch("import", lambda: self.controller.import_workspace_paths([path]), status="正在导入文件夹…")

    @Slot()
    def refreshSkills(self) -> None:  # noqa: N802
        rows = []
        for item in self.controller.skills():
            rows.append({**item, "steps": len(item.get("steps") or [])})
        self._skillsModel.set_rows(rows)

    @Slot()
    def refreshMemories(self) -> None:  # noqa: N802
        rows = []
        for item in self.controller.memories(limit=120):
            rows.append({**item, "tags": ", ".join(item.get("tags") or [])})
        self._memoriesModel.set_rows(rows)

    @Slot()
    def refreshTraces(self) -> None:  # noqa: N802
        rows = []
        for record in self.controller.trace_records():
            event = str(record.get("event") or "event")
            payload = record.get("payload") or {}
            rows.append({
                "event": event,
                "title": event.replace("_", " ").title(),
                "detail": json.dumps(payload, ensure_ascii=False, default=str),
                "time": str(record.get("timestamp") or ""),
                "level": "error" if "error" in event else "info",
            })
        self._tracesModel.set_rows(rows[-300:])

    @Slot()
    def refreshMcp(self) -> None:  # noqa: N802
        self._dispatch("mcp", self.controller.mcp_status, status="正在读取 MCP 状态…", blocking=False)

    def _apply_mcp(self, data: dict[str, Any]) -> None:
        rows = []
        for server in data.get("servers", []):
            rows.append({
                "server_id": server.get("server_id") or server.get("id") or "",
                "name": server.get("name") or server.get("server_id") or "MCP Server",
                "transport": server.get("transport") or "",
                "server_enabled": bool(server.get("enabled")),
                "status": "已启用" if server.get("enabled") else "已禁用",
                "tools": server.get("tool_count") or 0,
                "error": server.get("last_error") or "",
            })
        self._mcpModel.set_rows(rows)

    @Slot()
    def importMcpConfig(self) -> None:  # noqa: N802
        filename, _ = QFileDialog.getOpenFileName(None, "导入 MCP 配置", "", "JSON 配置 (*.json)")
        if not filename:
            return
        try:
            rows = self.controller.import_mcp_config(Path(filename))
            self.notification.emit("MCP 配置已导入", f"发现 {len(rows)} 个服务器")
            self.refreshMcp()
        except Exception as exc:  # noqa: BLE001
            self.notification.emit("导入失败", str(exc))

    @Slot()
    def syncMcp(self) -> None:  # noqa: N802
        self._dispatch("mcp", lambda: (self.controller.sync_mcp_tools(), self.controller.mcp_status())[1], status="正在同步 MCP 工具…")

    @Slot()
    def refreshDashboard(self) -> None:  # noqa: N802
        def load() -> dict[str, Any]:
            sessions = self.controller.sessions(limit=12)
            approvals = self.controller.pending_approvals()
            skills = self.controller.skills()
            apps = self.controller.allowed_apps(force_refresh=False)
            learning = self.controller.learning_dashboard(days=30)
            return {"sessions": sessions, "approvals": approvals, "skills": skills, "apps": apps, "learning": learning}

        self._dispatch("dashboard", load, status="正在更新总览…", blocking=False)

    def _apply_dashboard(self, data: dict[str, Any]) -> None:
        sessions = data.get("sessions", [])
        approvals = data.get("approvals", [])
        skills = data.get("skills", [])
        apps = data.get("apps", [])
        learning = data.get("learning", {}) or {}
        completed = int(learning.get("completed_sessions") or learning.get("session_count") or 0)
        dashboard = {
            "sessions": len(sessions),
            "approvals": len(approvals),
            "skills": len(skills),
            "apps": sum(1 for item in apps if item.get("path") or item.get("executable")),
            "learningMinutes": int(learning.get("total_minutes") or 0),
            "learningCompleted": completed,
        }
        if dashboard != self._dashboard:
            self._dashboard = dashboard
            self.dashboardChanged.emit()
        task_rows = []
        for index, item in enumerate(sessions[:9]):
            task_rows.append({
                "title": item.get("title") or "新会话",
                "subtitle": f"{item.get('message_count', 0)} 条消息",
                "state": "等待审批" if index < len(approvals) else "已记录",
                "progress": max(18, 88 - index * 7),
                "accent": "green" if index == 2 else "silver",
                "session_id": item.get("session_id") or "",
            })
        self._tasksModel.set_rows(task_rows)


    @Slot()
    def editModelConfiguration(self) -> None:  # noqa: N802
        if not hasattr(self.controller, "runtime"):
            self.notification.emit("预览模式", "预览模式不保存模型配置")
            return
        store = EnvModelConfigStore(self.controller.runtime.settings.env_path)
        current = store.load()
        key, ok = QInputDialog.getText(
            None,
            "DeepSeek API Key",
            "输入新的 API Key；留空表示保留现有密钥：",
        )
        if not ok:
            return
        model, ok = QInputDialog.getItem(
            None,
            "DeepSeek 模型",
            "选择模型：",
            list(DEEPSEEK_MODELS),
            max(0, list(DEEPSEEK_MODELS).index(current.model) if current.model in DEEPSEEK_MODELS else 0),
            False,
        )
        if not ok:
            return
        config = DeepSeekConfig(
            api_key=key.strip() or current.api_key,
            base_url=DEEPSEEK_BASE_URL,
            model=str(model),
        )
        self._dispatch(
            "reconfigure",
            lambda: self.controller.reconfigure_model(config),
            status="正在重载 DeepSeek 模型…",
        )

    @Slot()
    def testModelConnection(self) -> None:  # noqa: N802
        if not hasattr(self.controller, "runtime"):
            self.notification.emit("预览模式", "预览模式不连接真实模型")
            return
        store = EnvModelConfigStore(self.controller.runtime.settings.env_path)
        config = store.load()
        self._dispatch(
            "model_probe",
            lambda: self.controller.probe_model(config),
            status="正在测试 DeepSeek 连接…",
        )

    @Slot(str)
    def copyText(self, text: str) -> None:  # noqa: N802
        from PySide6.QtGui import QGuiApplication

        QGuiApplication.clipboard().setText(text)
        self.notification.emit("已复制", "内容已复制到剪贴板")

    @Slot()
    def close(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.controller.close()
