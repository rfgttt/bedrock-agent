from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Callable

from bedrock_agent.bootstrap import build_runtime
from bedrock_agent.config import DEEPSEEK_BASE_URL, DEEPSEEK_MODELS, Settings
from bedrock_agent.desktop_controller import DesktopController
from bedrock_agent.desktop_layout import centered_geometry
from bedrock_agent.desktop_refresh import DesktopRefreshState
from bedrock_agent.desktop_model_dialog import ModelConfigDialog
from bedrock_agent.domain import Message, PendingApproval, Role, RunResult
from bedrock_agent.model_config import DeepSeekConfig, EnvModelConfigStore


BG = "#10141c"
PANEL = "#171d28"
PANEL_ALT = "#1e2634"
TEXT = "#eef2f7"
MUTED = "#9aa7b8"
ACCENT = "#5ca7ff"
ACCENT_ACTIVE = "#77b7ff"
GOOD = "#67d391"
WARN = "#ffc66d"
DANGER = "#ff7f87"
BORDER = "#2a3444"
USER_BUBBLE = "#213650"
ASSISTANT_BUBBLE = "#1d2b27"


class BedrockDesktop:
    def __init__(self, root: tk.Tk, controller: DesktopController) -> None:
        self.root = root
        self.controller = controller
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.worker_lock = threading.Lock()
        self.busy = False
        self.session_rows: list[dict[str, Any]] = []
        self.trace_rows: list[dict[str, Any]] = []
        self.app_rows: list[dict[str, Any]] = []
        self.mcp_rows: list[dict[str, Any]] = []
        self.approval_rows: list[dict[str, Any]] = []
        self.pending_approval: PendingApproval | None = None
        self.approval_dialog: tk.Toplevel | None = None
        self.refresh_state = DesktopRefreshState()
        self._closing = False

        self.root.title("Bedrock Agent Desktop")
        self.root.geometry("1240x800")
        self.root.minsize(980, 650)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._configure_style()
        self._build_ui()
        self.tabs.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._refresh_all()
        self.root.after(100, self._poll_events)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Alt.TFrame", background=PANEL_ALT)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED)
        style.configure("Header.TLabel", background=BG, foreground=TEXT, font=("Microsoft YaHei UI", 16, "bold"))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
        style.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED)
        style.configure("Status.TLabel", background=PANEL, foreground=GOOD, font=("Microsoft YaHei UI", 9, "bold"))
        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#08111d",
            borderwidth=0,
            focusthickness=0,
            padding=(14, 9),
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.map("Accent.TButton", background=[("active", ACCENT_ACTIVE), ("disabled", BORDER)])
        style.configure(
            "Secondary.TButton",
            background=PANEL_ALT,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=(11, 7),
        )
        style.map("Secondary.TButton", background=[("active", BORDER)])
        style.configure("Danger.TButton", background=DANGER, foreground="#2a090c", padding=(11, 7))
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=30, borderwidth=0)
        style.configure("Treeview.Heading", background=PANEL_ALT, foreground=TEXT, relief="flat")
        style.map("Treeview", background=[("selected", USER_BUBBLE)])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(16, 9), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", PANEL_ALT)], foreground=[("selected", TEXT)])
        style.configure("TEntry", fieldbackground=PANEL_ALT, foreground=TEXT, insertcolor=TEXT, bordercolor=BORDER)

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(22, 16, 22, 12))
        header.pack(fill="x")
        ttk.Label(header, text="Bedrock Agent", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="桌面版 · 进程内运行 · 不开放网络端口", style="Muted.TLabel").pack(side="left", padx=(14, 0), pady=(5, 0))
        self.status_var = tk.StringVar(value="就绪")
        status = ttk.Label(header, textvariable=self.status_var, style="Status.TLabel")
        status.pack(side="right")

        body = ttk.Panedwindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        sidebar = ttk.Frame(body, style="Panel.TFrame", padding=12)
        body.add(sidebar, weight=1)
        ttk.Button(sidebar, text="＋ 新会话", style="Accent.TButton", command=self._new_session).pack(fill="x", pady=(0, 12))
        ttk.Label(sidebar, text="最近会话", style="PanelMuted.TLabel").pack(anchor="w", pady=(0, 6))
        self.session_list = tk.Listbox(
            sidebar,
            bg=PANEL,
            fg=TEXT,
            selectbackground=USER_BUBBLE,
            selectforeground=TEXT,
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            font=("Microsoft YaHei UI", 9),
        )
        self.session_list.pack(fill="both", expand=True)
        self.session_list.bind("<<ListboxSelect>>", self._on_session_selected)
        ttk.Separator(sidebar).pack(fill="x", pady=10)
        self.session_id_var = tk.StringVar()
        ttk.Label(sidebar, text="当前会话", style="PanelMuted.TLabel").pack(anchor="w")
        ttk.Label(sidebar, textvariable=self.session_id_var, style="Panel.TLabel", wraplength=210).pack(anchor="w", pady=(3, 0))

        main = ttk.Frame(body)
        body.add(main, weight=5)
        self.tabs = ttk.Notebook(main)
        self.tabs.pack(fill="both", expand=True)

        self.chat_tab = ttk.Frame(self.tabs, style="Panel.TFrame")
        self.memory_tab = ttk.Frame(self.tabs, style="Panel.TFrame")
        self.skills_tab = ttk.Frame(self.tabs, style="Panel.TFrame")
        self.approvals_tab = ttk.Frame(self.tabs, style="Panel.TFrame")
        self.mcp_tab = ttk.Frame(self.tabs, style="Panel.TFrame")
        self.activity_tab = ttk.Frame(self.tabs, style="Panel.TFrame")
        self.model_tab = ttk.Frame(self.tabs, style="Panel.TFrame")
        self.capabilities_tab = ttk.Frame(self.tabs, style="Panel.TFrame")
        self.security_tab = ttk.Frame(self.tabs, style="Panel.TFrame")
        self.tabs.add(self.chat_tab, text="对话")
        self.tabs.add(self.memory_tab, text="记忆")
        self.tabs.add(self.skills_tab, text="技能")
        self.tabs.add(self.approvals_tab, text="审批中心")
        self.tabs.add(self.mcp_tab, text="MCP")
        self.tabs.add(self.activity_tab, text="运行轨迹")
        self.tabs.add(self.model_tab, text="模型配置")
        self.tabs.add(self.capabilities_tab, text="能力中心")
        self.tabs.add(self.security_tab, text="安全与状态")

        self._build_chat_tab()
        self._build_memory_tab()
        self._build_skills_tab()
        self._build_approvals_tab()
        self._build_mcp_tab()
        self._build_activity_tab()
        self._build_model_tab()
        self._build_capabilities_tab()
        self._build_security_tab()

    def _build_chat_tab(self) -> None:
        container = ttk.Frame(self.chat_tab, style="Panel.TFrame", padding=14)
        container.pack(fill="both", expand=True)

        self.chat_text = tk.Text(
            container,
            wrap="word",
            state="disabled",
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            borderwidth=0,
            font=("Microsoft YaHei UI", 10),
            padx=14,
            pady=12,
        )
        scrollbar = ttk.Scrollbar(container, command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=scrollbar.set)
        self.chat_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.chat_text.tag_configure("user_name", foreground=ACCENT, font=("Microsoft YaHei UI", 9, "bold"), spacing1=14)
        self.chat_text.tag_configure("assistant_name", foreground=GOOD, font=("Microsoft YaHei UI", 9, "bold"), spacing1=14)
        self.chat_text.tag_configure("tool_name", foreground=WARN, font=("Microsoft YaHei UI", 9, "bold"), spacing1=10)
        self.chat_text.tag_configure("user_body", background=USER_BUBBLE, foreground=TEXT, lmargin1=12, lmargin2=12, rmargin=12, spacing3=10)
        self.chat_text.tag_configure("assistant_body", background=ASSISTANT_BUBBLE, foreground=TEXT, lmargin1=12, lmargin2=12, rmargin=12, spacing3=10)
        self.chat_text.tag_configure("tool_body", foreground=MUTED, lmargin1=12, lmargin2=12, rmargin=12, spacing3=8)
        self.chat_text.tag_configure("system", foreground=DANGER, spacing1=10, spacing3=10)

        # Persistent approval bar: it stays inside the main window, so approval
        # can never be hidden behind another window or pushed off-screen by DPI.
        self.approval_panel = tk.Frame(
            self.chat_tab,
            bg="#302817",
            highlightbackground=WARN,
            highlightcolor=WARN,
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        approval_copy = tk.Frame(self.approval_panel, bg="#302817")
        approval_copy.pack(side="left", fill="x", expand=True)
        self.approval_title_var = tk.StringVar(value="等待审批")
        self.approval_reason_var = tk.StringVar(value="")
        tk.Label(
            approval_copy,
            textvariable=self.approval_title_var,
            bg="#302817",
            fg="#ffe0a3",
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            approval_copy,
            textvariable=self.approval_reason_var,
            bg="#302817",
            fg=TEXT,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            justify="left",
            wraplength=680,
        ).pack(fill="x", pady=(3, 0))
        approval_actions = tk.Frame(self.approval_panel, bg="#302817")
        approval_actions.pack(side="right", padx=(14, 0))
        self.approval_details_button = tk.Button(
            approval_actions,
            text="查看参数",
            command=self._open_pending_approval_dialog,
            bg=PANEL_ALT,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat",
            padx=12,
            pady=7,
        )
        self.approval_details_button.pack(side="left", padx=(0, 7))
        self.approval_deny_button = tk.Button(
            approval_actions,
            text="拒绝",
            command=lambda: self._resolve_pending_approval(False),
            bg=DANGER,
            fg="#2a090c",
            activebackground="#ff9aa0",
            relief="flat",
            padx=14,
            pady=7,
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        self.approval_deny_button.pack(side="left", padx=(0, 7))
        self.approval_allow_button = tk.Button(
            approval_actions,
            text="允许执行",
            command=lambda: self._resolve_pending_approval(True),
            bg=ACCENT,
            fg="#08111d",
            activebackground=ACCENT_ACTIVE,
            relief="flat",
            padx=16,
            pady=7,
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        self.approval_allow_button.pack(side="left")
        self.approval_panel.pack(fill="x", padx=14, pady=(0, 10))
        for button in (self.approval_details_button, self.approval_deny_button, self.approval_allow_button):
            button.configure(state="disabled")
        self.approval_title_var.set("暂无待审批操作")
        self.approval_reason_var.set("需要写入、启动程序、调用 MCP 或访问网络时，会在这里等待你的决定。")

        self.composer = ttk.Frame(self.chat_tab, style="Alt.TFrame", padding=12)
        self.composer.pack(fill="x", padx=14, pady=(0, 14))
        self.input_text = tk.Text(
            self.composer,
            height=4,
            wrap="word",
            bg=PANEL_ALT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            borderwidth=0,
            font=("Microsoft YaHei UI", 10),
            padx=10,
            pady=8,
        )
        self.input_text.pack(side="left", fill="x", expand=True)
        self.input_text.bind("<Control-Return>", lambda _event: self._send())
        controls = ttk.Frame(self.composer, style="Alt.TFrame")
        controls.pack(side="right", padx=(10, 0), fill="y")
        self.send_button = ttk.Button(controls, text="发送", style="Accent.TButton", command=self._send)
        self.send_button.pack(fill="x")
        ttk.Label(controls, text="Ctrl + Enter", style="PanelMuted.TLabel").pack(pady=(8, 0))

    def _build_memory_tab(self) -> None:
        toolbar = ttk.Frame(self.memory_tab, style="Panel.TFrame", padding=12)
        toolbar.pack(fill="x")
        self.memory_query = tk.StringVar()
        entry = ttk.Entry(toolbar, textvariable=self.memory_query)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda _event: self._refresh_memories(force=True))
        ttk.Button(toolbar, text="搜索", style="Secondary.TButton", command=lambda: self._refresh_memories(force=True)).pack(side="left", padx=8)
        ttk.Button(toolbar, text="全部", style="Secondary.TButton", command=self._clear_memory_search).pack(side="left")

        columns = ("kind", "importance", "created_at", "content")
        self.memory_tree = ttk.Treeview(self.memory_tab, columns=columns, show="headings")
        self.memory_tree.heading("kind", text="类型")
        self.memory_tree.heading("importance", text="重要度")
        self.memory_tree.heading("created_at", text="创建时间")
        self.memory_tree.heading("content", text="内容")
        self.memory_tree.column("kind", width=90, anchor="center")
        self.memory_tree.column("importance", width=70, anchor="center")
        self.memory_tree.column("created_at", width=150)
        self.memory_tree.column("content", width=620)
        self.memory_tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _build_skills_tab(self) -> None:
        toolbar = ttk.Frame(self.skills_tab, style="Panel.TFrame", padding=12)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="这里只显示已经由你批准并安装的组合技能。", style="PanelMuted.TLabel").pack(side="left")
        ttk.Button(toolbar, text="刷新", style="Secondary.TButton", command=lambda: self._refresh_skills(force=True)).pack(side="right")
        columns = ("name", "risk", "description")
        self.skill_tree = ttk.Treeview(self.skills_tab, columns=columns, show="headings")
        self.skill_tree.heading("name", text="技能名")
        self.skill_tree.heading("risk", text="风险")
        self.skill_tree.heading("description", text="说明")
        self.skill_tree.column("name", width=210)
        self.skill_tree.column("risk", width=100, anchor="center")
        self.skill_tree.column("description", width=650)
        self.skill_tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _build_approvals_tab(self) -> None:
        wrap = ttk.Frame(self.approvals_tab, style="Panel.TFrame", padding=14)
        wrap.pack(fill="both", expand=True)
        top = ttk.Frame(wrap, style="Panel.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="审批中心", style="Header.TLabel").pack(side="left")
        ttk.Button(top, text="刷新", style="Secondary.TButton", command=lambda: self._refresh_approvals(force=True)).pack(side="right")
        ttk.Label(
            wrap,
            text="所有未处理审批都会保存在本机数据库。即使窗口被遮挡或重新启动，也可以在这里恢复处理。",
            style="PanelMuted.TLabel",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(8, 12))

        paned = ttk.Panedwindow(wrap, orient="horizontal")
        paned.pack(fill="both", expand=True)
        columns = ("tool", "session", "reason")
        self.approval_tree = ttk.Treeview(paned, columns=columns, show="headings")
        self.approval_tree.heading("tool", text="工具")
        self.approval_tree.heading("session", text="会话")
        self.approval_tree.heading("reason", text="原因")
        self.approval_tree.column("tool", width=240)
        self.approval_tree.column("session", width=220)
        self.approval_tree.column("reason", width=320)
        self.approval_tree.bind("<<TreeviewSelect>>", self._show_selected_approval)
        paned.add(self.approval_tree, weight=2)

        details_box = ttk.Frame(paned, style="Alt.TFrame", padding=12)
        paned.add(details_box, weight=3)
        ttk.Label(details_box, text="审批参数", style="Panel.TLabel").pack(anchor="w")
        self.approval_payload = tk.Text(
            details_box,
            wrap="word",
            bg=PANEL_ALT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )
        self.approval_payload.pack(fill="both", expand=True, pady=(8, 12))
        self.approval_payload.configure(state="disabled")
        actions = ttk.Frame(details_box, style="Alt.TFrame")
        actions.pack(fill="x")
        ttk.Button(actions, text="拒绝选中", style="Danger.TButton", command=lambda: self._resolve_selected_approval(False)).pack(side="right")
        ttk.Button(actions, text="允许选中", style="Accent.TButton", command=lambda: self._resolve_selected_approval(True)).pack(side="right", padx=(0, 8))
        ttk.Button(actions, text="切换到对应会话", style="Secondary.TButton", command=self._open_selected_approval_session).pack(side="left")

    def _build_mcp_tab(self) -> None:
        wrap = ttk.Frame(self.mcp_tab, style="Panel.TFrame", padding=14)
        wrap.pack(fill="both", expand=True)
        top = ttk.Frame(wrap, style="Panel.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="MCP 连接器", style="Header.TLabel").pack(side="left")
        ttk.Button(top, text="刷新状态", style="Secondary.TButton", command=lambda: self._refresh_mcp(force=True)).pack(side="right")
        self.mcp_status_var = tk.StringVar(value="正在读取 MCP 状态…")
        ttk.Label(
            wrap,
            textvariable=self.mcp_status_var,
            style="PanelMuted.TLabel",
            wraplength=920,
            justify="left",
        ).pack(anchor="w", pady=(8, 12))

        columns = ("enabled", "name", "transport", "endpoint")
        self.mcp_tree = ttk.Treeview(wrap, columns=columns, show="headings", height=9)
        self.mcp_tree.heading("enabled", text="启用")
        self.mcp_tree.heading("name", text="服务器")
        self.mcp_tree.heading("transport", text="传输")
        self.mcp_tree.heading("endpoint", text="命令 / 地址")
        self.mcp_tree.column("enabled", width=70, anchor="center")
        self.mcp_tree.column("name", width=200)
        self.mcp_tree.column("transport", width=100, anchor="center")
        self.mcp_tree.column("endpoint", width=620)
        self.mcp_tree.pack(fill="both", expand=True)

        actions = ttk.Frame(wrap, style="Panel.TFrame")
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="导入 MCP 配置…", style="Accent.TButton", command=self._import_mcp_config).pack(side="left")
        ttk.Button(actions, text="启用/停用选中", style="Secondary.TButton", command=self._toggle_selected_mcp).pack(side="left", padx=8)
        ttk.Button(actions, text="测试选中", style="Secondary.TButton", command=self._test_selected_mcp).pack(side="left")
        ttk.Button(actions, text="同步工具", style="Secondary.TButton", command=self._sync_mcp_tools).pack(side="left", padx=8)
        ttk.Button(actions, text="删除选中", style="Danger.TButton", command=self._remove_selected_mcp).pack(side="right")

        ttk.Label(
            wrap,
            text='MCP SDK 未安装时，在项目虚拟环境运行：python -m pip install -e ".[mcp]"。导入的服务器默认关闭；启用或调用工具都需要你的明确操作。当前仅桥接 MCP Tools，资源和 Prompts 暂未接入。',
            style="PanelMuted.TLabel",
            wraplength=940,
            justify="left",
        ).pack(anchor="w", pady=(12, 0))

    def _build_activity_tab(self) -> None:
        toolbar = ttk.Frame(self.activity_tab, style="Panel.TFrame", padding=12)
        toolbar.pack(fill="x")
        self.trace_var = tk.StringVar(value="暂无 trace")
        ttk.Label(toolbar, textvariable=self.trace_var, style="PanelMuted.TLabel").pack(side="left")
        ttk.Button(toolbar, text="刷新", style="Secondary.TButton", command=lambda: self._refresh_trace(force=True)).pack(side="right")

        paned = ttk.Panedwindow(self.activity_tab, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        columns = ("time", "event")
        self.trace_tree = ttk.Treeview(paned, columns=columns, show="headings")
        self.trace_tree.heading("time", text="时间")
        self.trace_tree.heading("event", text="事件")
        self.trace_tree.column("time", width=190)
        self.trace_tree.column("event", width=220)
        self.trace_tree.bind("<<TreeviewSelect>>", self._show_trace_payload)
        paned.add(self.trace_tree, weight=2)
        self.trace_payload = tk.Text(
            paned,
            wrap="word",
            bg=PANEL_ALT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Consolas", 10),
            padx=12,
            pady=12,
        )
        self.trace_payload.configure(state="disabled")
        paned.add(self.trace_payload, weight=3)


    def _build_model_tab(self) -> None:
        wrap = ttk.Frame(self.model_tab, style="Panel.TFrame", padding=22)
        wrap.pack(fill="both", expand=True)
        ttk.Label(wrap, text="DeepSeek 模型配置", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            wrap,
            text="配置保存在本机 .env。保存后会重建模型适配器，但不会清空会话、记忆或技能。",
            style="PanelMuted.TLabel",
            wraplength=820,
            justify="left",
        ).pack(anchor="w", pady=(8, 20))

        form = ttk.Frame(wrap, style="Panel.TFrame")
        form.pack(fill="x")
        self.model_api_key_var = tk.StringVar()
        self.model_base_url_var = tk.StringVar(value=DEEPSEEK_BASE_URL)
        self.model_name_var = tk.StringVar()
        self.model_show_key_var = tk.BooleanVar(value=False)
        self.model_status_var = tk.StringVar(value="尚未测试连接")

        ttk.Label(form, text="提供商", style="PanelMuted.TLabel").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Label(form, text="DeepSeek", style="Panel.TLabel").grid(row=0, column=1, sticky="w", pady=8)

        ttk.Label(form, text="API Key", style="PanelMuted.TLabel").grid(row=1, column=0, sticky="w", pady=8)
        self.model_key_entry = ttk.Entry(form, textvariable=self.model_api_key_var, show="●")
        self.model_key_entry.grid(row=1, column=1, sticky="ew", pady=8)
        ttk.Checkbutton(
            form,
            text="显示",
            variable=self.model_show_key_var,
            command=self._toggle_model_key,
        ).grid(row=1, column=2, padx=(10, 0))

        ttk.Label(form, text="API 地址", style="PanelMuted.TLabel").grid(row=2, column=0, sticky="w", pady=8)
        ttk.Entry(form, textvariable=self.model_base_url_var, state="readonly").grid(
            row=2, column=1, columnspan=2, sticky="ew", pady=8
        )

        ttk.Label(form, text="模型", style="PanelMuted.TLabel").grid(row=3, column=0, sticky="w", pady=8)
        ttk.Combobox(
            form,
            textvariable=self.model_name_var,
            values=DEEPSEEK_MODELS,
            state="normal",
        ).grid(row=3, column=1, columnspan=2, sticky="ew", pady=8)

        ttk.Label(form, text="连接状态", style="PanelMuted.TLabel").grid(row=4, column=0, sticky="w", pady=8)
        ttk.Label(form, textvariable=self.model_status_var, style="Panel.TLabel", wraplength=650).grid(
            row=4, column=1, columnspan=2, sticky="w", pady=8
        )
        form.columnconfigure(1, weight=1)

        actions = ttk.Frame(wrap, style="Panel.TFrame")
        actions.pack(fill="x", pady=(24, 0))
        self.model_save_button = ttk.Button(
            actions, text="保存并重载", style="Accent.TButton", command=self._save_model_configuration
        )
        self.model_save_button.pack(side="left")
        self.model_test_button = ttk.Button(
            actions, text="测试连接", style="Secondary.TButton", command=self._test_model_connection
        )
        self.model_test_button.pack(side="left", padx=8)
        ttk.Button(
            actions, text="恢复当前配置", style="Secondary.TButton", command=self._load_model_configuration
        ).pack(side="left")
        self._load_model_configuration()

    def _toggle_model_key(self) -> None:
        self.model_key_entry.configure(show="" if self.model_show_key_var.get() else "●")

    def _current_model_configuration(self) -> DeepSeekConfig:
        return DeepSeekConfig(
            api_key=self.model_api_key_var.get(),
            base_url=self.model_base_url_var.get(),
            model=self.model_name_var.get(),
        )

    def _load_model_configuration(self) -> None:
        store = EnvModelConfigStore(self.controller.runtime.settings.env_path)
        config = store.load()
        self.model_api_key_var.set(config.api_key)
        self.model_base_url_var.set(config.base_url)
        self.model_name_var.set(config.model)
        self.model_status_var.set(f"当前运行：{self.controller.runtime.settings.model}")

    def _save_model_configuration(self) -> None:
        if self.busy:
            return
        config = self._current_model_configuration()
        try:
            config.validate()
        except Exception as exc:
            messagebox.showerror("配置错误", str(exc), parent=self.root)
            return
        self._set_busy(True, "正在重载 DeepSeek 模型…")
        self._run_background("model_saved", lambda: self.controller.reconfigure_model(config))

    def _test_model_connection(self) -> None:
        if self.busy:
            return
        config = self._current_model_configuration()
        try:
            config.validate()
        except Exception as exc:
            messagebox.showerror("配置错误", str(exc), parent=self.root)
            return
        self.model_status_var.set("正在连接 DeepSeek…")
        self._set_busy(True, "正在测试 DeepSeek 连接…")
        self._run_background("model_test", lambda: self.controller.probe_model(config))


    def _build_capabilities_tab(self) -> None:
        wrap = ttk.Frame(self.capabilities_tab, style="Panel.TFrame", padding=18)
        wrap.pack(fill="both", expand=True)
        top = ttk.Frame(wrap, style="Panel.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="能力中心", style="Header.TLabel").pack(side="left")
        ttk.Button(top, text="刷新", style="Secondary.TButton", command=lambda: self._refresh_capabilities(force=True)).pack(side="right")
        ttk.Label(
            wrap,
            text="外部动作、写入和 MCP 调用仍需要本机审批。工作区导入由你通过系统文件选择器明确指定来源。",
            style="PanelMuted.TLabel",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(8, 14))

        workspace_box = ttk.LabelFrame(wrap, text="工作区", padding=10)
        workspace_box.pack(fill="x", pady=(0, 12))
        self.workspace_path_var = tk.StringVar(value=str(self.controller.workspace_path()))
        workspace_copy = ttk.Frame(workspace_box)
        workspace_copy.pack(side="left", fill="x", expand=True)
        ttk.Label(workspace_copy, textvariable=self.workspace_path_var, style="Panel.TLabel", wraplength=680).pack(anchor="w")
        ttk.Label(
            workspace_copy,
            text="Agent 只能读取和修改这个隔离目录。导入的文件默认复制到 workspace/imports，不会移动或删除原文件。",
            style="PanelMuted.TLabel",
            wraplength=680,
        ).pack(anchor="w", pady=(3, 0))
        workspace_actions = ttk.Frame(workspace_box)
        workspace_actions.pack(side="right", padx=(12, 0))
        ttk.Button(workspace_actions, text="打开工作区", style="Secondary.TButton", command=self._open_workspace).pack(side="left")
        ttk.Button(workspace_actions, text="导入文件…", style="Accent.TButton", command=self._import_workspace_files).pack(side="left", padx=8)
        ttk.Button(workspace_actions, text="导入文件夹…", style="Accent.TButton", command=self._import_workspace_folder).pack(side="left")

        app_box = ttk.LabelFrame(wrap, text="本地应用白名单", padding=10)
        app_box.pack(fill="both", expand=True, pady=(0, 12))
        app_columns = ("available", "name", "executable")
        self.app_tree = ttk.Treeview(app_box, columns=app_columns, show="headings", height=7)
        self.app_tree.heading("available", text="状态")
        self.app_tree.heading("name", text="应用")
        self.app_tree.heading("executable", text="可信路径")
        self.app_tree.column("available", width=72, anchor="center")
        self.app_tree.column("name", width=210)
        self.app_tree.column("executable", width=650)
        self.app_tree.pack(fill="both", expand=True)
        app_actions = ttk.Frame(app_box)
        app_actions.pack(fill="x", pady=(10, 0))
        ttk.Button(app_actions, text="重新扫描", style="Secondary.TButton", command=lambda: self._refresh_capabilities(force=True)).pack(side="left")
        ttk.Button(app_actions, text="添加常用程序…", style="Accent.TButton", command=self._add_custom_application).pack(side="left", padx=8)
        ttk.Button(app_actions, text="设置/更换路径…", style="Secondary.TButton", command=self._change_selected_app_path).pack(side="left")
        ttk.Button(app_actions, text="让 Agent 打开", style="Secondary.TButton", command=self._ask_agent_to_open_selected_app).pack(side="left", padx=8)
        ttk.Button(app_actions, text="移除自定义应用", style="Danger.TButton", command=self._remove_selected_custom_app).pack(side="right")

        columns = ("status", "name", "detail", "tools")
        self.capability_tree = ttk.Treeview(wrap, columns=columns, show="headings", height=7)
        self.capability_tree.heading("status", text="状态")
        self.capability_tree.heading("name", text="能力")
        self.capability_tree.heading("detail", text="说明")
        self.capability_tree.heading("tools", text="工具")
        self.capability_tree.column("status", width=72, anchor="center")
        self.capability_tree.column("name", width=170)
        self.capability_tree.column("detail", width=390)
        self.capability_tree.column("tools", width=420)
        self.capability_tree.pack(fill="both", expand=True)

        prompts = ttk.LabelFrame(wrap, text="快速示例", padding=10)
        prompts.pack(fill="x", pady=(14, 0))
        examples = [
            ("列出应用", "列出当前允许启动的应用。"),
            ("播放/暂停", "请切换当前音乐的播放或暂停。"),
            ("网页搜索", "搜索 Python pytest 入门资料，列出 5 个结果。"),
            ("整理文件", "预览 workspace 根目录按扩展名整理的方案，不要直接执行。"),
            ("检查项目", "检查 workspace 中 Python 项目的结构和语法错误。"),
            ("制定学习计划", "给我制定 30 天 Python 与 Agent 开发学习计划，每天 90 分钟，并保存。"),
        ]
        for index, (label, prompt) in enumerate(examples):
            ttk.Button(
                prompts,
                text=label,
                style="Secondary.TButton",
                command=lambda value=prompt: self._insert_prompt(value),
            ).grid(row=index // 3, column=index % 3, sticky="ew", padx=5, pady=5)
        for column in range(3):
            prompts.columnconfigure(column, weight=1)

        self.learning_summary_var = tk.StringVar(value="学习记录：尚未加载")
        ttk.Label(wrap, textvariable=self.learning_summary_var, style="PanelMuted.TLabel").pack(anchor="w", pady=(12, 0))

    def _insert_prompt(self, prompt: str) -> None:
        self.tabs.select(self.chat_tab)
        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", prompt)
        self.input_text.focus_set()

    def _build_security_tab(self) -> None:
        wrap = ttk.Frame(self.security_tab, style="Panel.TFrame", padding=22)
        wrap.pack(fill="both", expand=True)
        ttk.Label(wrap, text="本地安全边界", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            wrap,
            text="桌面版直接在当前本地用户进程中调用 Agent，不启动 Web 服务，也不监听任何 IP。高风险操作仍需本机审批。",
            style="PanelMuted.TLabel",
            wraplength=820,
            justify="left",
        ).pack(anchor="w", pady=(8, 20))
        self.security_grid = ttk.Frame(wrap, style="Panel.TFrame")
        self.security_grid.pack(fill="x", anchor="n")
        actions = ttk.Frame(wrap, style="Panel.TFrame")
        actions.pack(fill="x", pady=(22, 0))
        ttk.Button(actions, text="打开工作区", style="Secondary.TButton", command=self._open_workspace).pack(side="left")
        ttk.Button(actions, text="打开私有数据目录", style="Secondary.TButton", command=self._open_private).pack(side="left", padx=8)
        ttk.Button(actions, text="打开项目说明", style="Secondary.TButton", command=self._open_docs).pack(side="left")

    def _active_view_name(self) -> str:
        selected = self.tabs.select()
        mapping = {
            str(self.memory_tab): "memories",
            str(self.skills_tab): "skills",
            str(self.approvals_tab): "approvals",
            str(self.mcp_tab): "mcp",
            str(self.activity_tab): "trace",
            str(self.capabilities_tab): "capabilities",
            str(self.security_tab): "security",
        }
        return mapping.get(selected, "chat")

    def _on_tab_changed(self, _event: tk.Event | None = None) -> None:
        self._refresh_active_view()

    def _refresh_active_view(self) -> None:
        view = self._active_view_name()
        if view == "memories" and self.refresh_state.is_dirty(view):
            self._refresh_memories()
        elif view == "skills" and self.refresh_state.is_dirty(view):
            self._refresh_skills()
        elif view == "approvals" and self.refresh_state.is_dirty(view):
            self._refresh_approvals()
        elif view == "mcp" and self.refresh_state.is_dirty(view):
            self._refresh_mcp()
        elif view == "trace" and self.refresh_state.is_dirty(view):
            self._refresh_trace()
        elif view == "capabilities" and self.refresh_state.is_dirty(view):
            self._refresh_capabilities()
        elif view == "security" and self.refresh_state.is_dirty(view):
            self._refresh_security()

    def _new_session(self) -> None:
        if self.busy or self.pending_approval is not None:
            if self.pending_approval is not None:
                self.tabs.select(self.chat_tab)
                self.status_var.set("请先处理当前待审批操作")
            return
        self.controller.new_session()
        self.session_id_var.set(self.controller.session_id)
        self.refresh_state.reset_messages(self.controller.session_id)
        self._render_messages([], force=True)
        self.input_text.focus_set()
        self.status_var.set("新会话已创建")
        self.session_list.selection_clear(0, "end")

    def _on_session_selected(self, _event: tk.Event) -> None:
        if self.busy or self.pending_approval is not None:
            return
        selected = self.session_list.curselection()
        if not selected:
            return
        row = self.session_rows[selected[0]]
        self.controller.select_session(row["session_id"])
        self.session_id_var.set(self.controller.session_id)
        messages, hidden_count = self.controller.message_view()
        self._render_messages(messages, hidden_count=hidden_count, force=True)
        self.status_var.set("已载入会话")

    def _send(self) -> str:
        if self.busy or self.pending_approval is not None:
            if self.pending_approval is not None:
                self.status_var.set("请先点击允许执行或拒绝")
                self.tabs.select(self.chat_tab)
            return "break"
        text = self.input_text.get("1.0", "end").strip()
        if not text:
            return "break"
        self.input_text.delete("1.0", "end")
        self._append_pending_user(text)
        self._set_busy(True, "Bedrock 正在思考…")
        self._run_background("run", lambda: self.controller.send(text))
        return "break"

    def _run_background(self, kind: str, job: Callable[[], Any]) -> None:
        def worker() -> None:
            try:
                value = job()
                self.events.put((kind, value))
            except Exception as exc:
                self.events.put(("error", exc))

        thread = threading.Thread(target=worker, name=f"bedrock-{kind}", daemon=True)
        thread.start()

    def _poll_events(self) -> None:
        processed = 0
        while processed < 50:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            processed += 1
            if kind in {"run", "approval"}:
                self._handle_result(value)
            elif kind == "model_saved":
                self._set_busy(False, "DeepSeek 配置已生效")
                self.model_status_var.set(f"已重载：{value.get('模型', 'DeepSeek')}")
                self.refresh_state.mark_dirty("security", "capabilities")
                self._refresh_active_view()
                messagebox.showinfo("配置已保存", "DeepSeek 配置已保存并在当前桌面进程中生效。", parent=self.root)
            elif kind == "model_test":
                self._set_busy(False, "DeepSeek 连接正常")
                available = value.get("model_available", False)
                suffix = "模型可用" if available else "认证成功，但模型未出现在模型列表中"
                self.model_status_var.set(f"连接成功：{suffix}")
            elif kind == "workspace_imported":
                self._set_busy(False, "工作区导入完成")
                self.refresh_state.mark_dirty("capabilities", "security")
                targets = "\n".join(f"• {row['target']}" for row in value[:20])
                if len(value) > 20:
                    targets += f"\n…另有 {len(value) - 20} 项"
                messagebox.showinfo("已复制到工作区", targets or "导入完成", parent=self.root)
            elif kind in {"mcp_imported", "mcp_updated"}:
                self._set_busy(False, "MCP 配置已更新")
                self.refresh_state.mark_dirty("mcp", "capabilities", "security")
                self._refresh_mcp(force=True)
            elif kind == "mcp_test":
                self._set_busy(False, "MCP 服务器连接成功")
                tools = value.get("tools", [])
                names = ", ".join(str(row.get("name", "")) for row in tools[:12])
                messagebox.showinfo(
                    "MCP 测试成功",
                    f"发现 {value.get('tool_count', len(tools))} 个工具。\n{names}",
                    parent=self.root,
                )
                self.refresh_state.mark_dirty("mcp")
                self._refresh_mcp(force=True)
            elif kind == "error":
                self._set_busy(False, "运行失败")
                self._append_system(f"错误：{value}")
                messagebox.showerror("Bedrock 运行错误", str(value), parent=self.root)
        if self._closing:
            return
        delay = 75 if self.busy or not self.events.empty() else 350
        self.root.after(delay, self._poll_events)

    def _handle_result(self, result: RunResult) -> None:
        self.controller.select_session(result.session_id)
        self.session_id_var.set(result.session_id)
        messages, hidden_count = self.controller.message_view()
        self._render_messages(messages, hidden_count=hidden_count)
        self._refresh_sessions()
        self.refresh_state.mark_dirty("memories", "skills", "approvals", "mcp", "trace", "capabilities", "security")
        self._refresh_active_view()

        if result.status == "approval_required":
            self._set_busy(False, "等待你的审批")
            pending = result.pending_approval
            if pending is not None:
                self._present_approval(pending)
            return
        self._clear_pending_approval()
        self.refresh_state.mark_dirty("approvals")
        self._refresh_approvals(force=True)
        if result.status == "completed":
            self._set_busy(False, "就绪")
            return
        self._set_busy(False, "运行失败")
        self._append_system(result.error or "未知错误")

    def _present_approval(self, pending: PendingApproval) -> None:
        self.pending_approval = pending
        self.approval_title_var.set(f"等待审批 · {pending.tool_call.name}")
        self.approval_reason_var.set(pending.reason or "这项操作会对本机产生实际影响。")
        for button in (self.approval_details_button, self.approval_deny_button, self.approval_allow_button):
            button.configure(state="normal")
        self.tabs.select(self.chat_tab)
        self.send_button.configure(state="disabled")
        self.session_list.configure(state="disabled")
        self.status_var.set("等待你的审批：请点击允许执行或拒绝，也可进入审批中心")
        self.refresh_state.mark_dirty("approvals")
        self._refresh_approvals()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        try:
            self.root.attributes("-topmost", True)
            self.root.after(700, lambda: self.root.attributes("-topmost", False))
        except tk.TclError:
            pass
        try:
            self.root.bell()
        except tk.TclError:
            pass

    def _clear_pending_approval(self) -> None:
        self.pending_approval = None
        self.approval_title_var.set("暂无待审批操作")
        self.approval_reason_var.set("需要写入、启动程序、调用 MCP 或访问网络时，会在这里等待你的决定。")
        for button in (self.approval_details_button, self.approval_deny_button, self.approval_allow_button):
            button.configure(state="disabled")
        if self.approval_dialog is not None and self.approval_dialog.winfo_exists():
            self.approval_dialog.destroy()
        self.approval_dialog = None

    def _resolve_pending_approval(self, approved: bool) -> None:
        pending = self.pending_approval
        if pending is None:
            return
        approval_id = pending.approval_id
        self._clear_pending_approval()
        self._set_busy(True, "正在处理审批结果…")
        self._run_background(
            "approval",
            lambda: self.controller.resolve_approval(approval_id, approved),
        )

    def _open_pending_approval_dialog(self) -> None:
        pending = self.pending_approval
        if pending is None:
            messagebox.showinfo("暂无待审批操作", "当前没有需要确认的操作。", parent=self.root)
            return
        if self.approval_dialog is not None and self.approval_dialog.winfo_exists():
            self.approval_dialog.lift()
            self.approval_dialog.focus_force()
            return

        dialog = tk.Toplevel(self.root)
        self.approval_dialog = dialog
        dialog.title("Bedrock 本地操作审批")
        dialog.geometry(
            centered_geometry(720, 560, dialog.winfo_screenwidth(), dialog.winfo_screenheight())
        )
        dialog.minsize(520, 360)
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)

        header = tk.Frame(dialog, bg=BG, padx=20, pady=16)
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(
            header,
            text="Bedrock 请求执行一项有副作用的操作",
            bg=BG,
            fg=TEXT,
            font=("Microsoft YaHei UI", 14, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            header,
            text=f"工具：{pending.tool_call.name}\n原因：{pending.reason}",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            justify="left",
            wraplength=650,
        ).pack(fill="x", pady=(8, 0))

        details_frame = tk.Frame(dialog, bg=PANEL, padx=18, pady=12)
        details_frame.grid(row=1, column=0, sticky="nsew", padx=20)
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(1, weight=1)
        tk.Label(
            details_frame,
            text="工具参数",
            bg=PANEL,
            fg=TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))
        details = tk.Text(
            details_frame,
            bg=PANEL_ALT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Consolas", 10),
            padx=10,
            pady=10,
            wrap="word",
            height=10,
        )
        detail_scrollbar = ttk.Scrollbar(details_frame, command=details.yview)
        details.configure(yscrollcommand=detail_scrollbar.set)
        details.grid(row=1, column=0, sticky="nsew")
        detail_scrollbar.grid(row=1, column=1, sticky="ns")
        details.insert("1.0", json.dumps(pending.tool_call.arguments, ensure_ascii=False, indent=2))
        details.configure(state="disabled")

        footer = tk.Frame(dialog, bg=BG, padx=20, pady=16)
        footer.grid(row=2, column=0, sticky="ew")
        tk.Label(
            footer,
            text="关闭这个详情窗口不会自动拒绝；你仍可在主窗口的黄色审批栏操作。",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            justify="left",
        ).pack(side="left", fill="x", expand=True)
        tk.Button(
            footer,
            text="拒绝",
            command=lambda: self._resolve_pending_approval(False),
            bg=DANGER,
            fg="#2a090c",
            activebackground="#ff9aa0",
            relief="flat",
            padx=16,
            pady=8,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(side="right")
        tk.Button(
            footer,
            text="允许执行",
            command=lambda: self._resolve_pending_approval(True),
            bg=ACCENT,
            fg="#08111d",
            activebackground=ACCENT_ACTIVE,
            relief="flat",
            padx=18,
            pady=8,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(side="right", padx=(0, 10))

        def close_details() -> None:
            if dialog.winfo_exists():
                dialog.destroy()
            self.approval_dialog = None

        dialog.protocol("WM_DELETE_WINDOW", close_details)
        dialog.update_idletasks()
        dialog.lift()
        dialog.focus_force()
        try:
            dialog.attributes("-topmost", True)
            dialog.after(700, lambda: dialog.attributes("-topmost", False))
        except tk.TclError:
            pass

    @staticmethod
    def _compact_tool_arguments(name: str, arguments: dict[str, Any], *, max_chars: int = 720) -> str:
        if name == "create_study_plan":
            topics = arguments.get("topics", [])
            preview = {
                "title": arguments.get("title"),
                "days": arguments.get("days"),
                "daily_minutes": arguments.get("daily_minutes"),
                "start_date": arguments.get("start_date"),
                "topics_count": len(topics) if isinstance(topics, list) else "?",
                "topics_preview": topics[:4] if isinstance(topics, list) else topics,
            }
            return json.dumps(preview, ensure_ascii=False)
        rendered = json.dumps(arguments, ensure_ascii=False, default=str)
        if len(rendered) <= max_chars:
            return rendered
        return rendered[:max_chars] + f"…（已截断 {len(rendered) - max_chars} 字符；完整参数见审批中心或运行轨迹）"

    @staticmethod
    def _compact_tool_result(content: str | None, *, max_chars: int = 2400) -> str:
        value = content or ""
        if len(value) <= max_chars:
            return value
        return value[:max_chars] + f"…（已截断 {len(value) - max_chars} 字符；完整结果保存在本地数据库和轨迹中）"

    def _insert_message(self, message: Message) -> None:
        if message.role is Role.USER:
            self.chat_text.insert("end", "你\n", "user_name")
            self.chat_text.insert("end", (message.content or "") + "\n", "user_body")
        elif message.role is Role.ASSISTANT:
            if message.content:
                self.chat_text.insert("end", "Bedrock\n", "assistant_name")
                self.chat_text.insert("end", message.content + "\n", "assistant_body")
            for call in message.tool_calls:
                self.chat_text.insert("end", f"请求工具 · {call.name}\n", "tool_name")
                self.chat_text.insert(
                    "end",
                    self._compact_tool_arguments(call.name, call.arguments) + "\n",
                    "tool_body",
                )
        elif message.role is Role.TOOL:
            self.chat_text.insert("end", f"工具结果 · {message.name or 'unknown'}\n", "tool_name")
            self.chat_text.insert("end", self._compact_tool_result(message.content) + "\n", "tool_body")

    def _render_messages(
        self,
        messages: list[Message],
        *,
        hidden_count: int = 0,
        force: bool = False,
    ) -> None:
        plan = self.refresh_state.plan_messages(
            self.controller.session_id,
            messages,
            hidden_count=hidden_count,
            force=force,
        )
        if plan.mode == "none":
            return

        self.chat_text.configure(state="normal")
        if plan.mode == "full":
            self.chat_text.delete("1.0", "end")
            if hidden_count:
                self.chat_text.insert(
                    "end",
                    f"为保持界面流畅，仅显示最近 {len(messages)} 条消息；更早的 {hidden_count} 条仍保存在本地数据库。\n\n",
                    "system",
                )
            if not messages:
                self.chat_text.insert("end", "Bedrock\n", "assistant_name")
                self.chat_text.insert(
                    "end",
                    "这是一个本地桌面 Agent。你可以直接描述任务；需要写入、永久记忆或安装技能时，我会要求审批。\n",
                    "assistant_body",
                )
            render_rows = messages
        else:
            render_rows = messages[plan.start_index :]

        for message in render_rows:
            self._insert_message(message)
        self.chat_text.configure(state="disabled")
        self.chat_text.see("end")

    def _append_pending_user(self, text: str) -> None:
        message = Message(Role.USER, text)
        self.chat_text.configure(state="normal")
        self._insert_message(message)
        self.chat_text.configure(state="disabled")
        self.chat_text.see("end")
        self.refresh_state.append_pending_message(self.controller.session_id, message)

    def _append_system(self, text: str) -> None:
        self.chat_text.configure(state="normal")
        self.chat_text.insert("end", f"\n{text}\n", "system")
        self.chat_text.configure(state="disabled")
        self.chat_text.see("end")

    def _set_busy(self, busy: bool, label: str) -> None:
        self.busy = busy
        self.status_var.set(label)
        locked = busy or self.pending_approval is not None
        self.send_button.configure(state="disabled" if locked else "normal")
        self.session_list.configure(state="disabled" if locked else "normal")

    def _refresh_all(self) -> None:
        self.session_id_var.set(self.controller.session_id)
        self.refresh_state.reset_messages(self.controller.session_id)
        self._render_messages([], force=True)
        self._refresh_sessions(force=True)
        self.refresh_state.mark_dirty("memories", "skills", "approvals", "mcp", "trace", "capabilities", "security")
        self._refresh_approvals(force=True)
        self._refresh_active_view()

    def _refresh_sessions(self, *, force: bool = False) -> None:
        current = self.controller.session_id
        rows = self.controller.sessions()
        if not self.refresh_state.changed(
            "sessions", {"current": current, "rows": rows}, force=force
        ):
            return
        self.session_rows = rows
        self.session_list.delete(0, "end")
        selected_index = None
        for index, row in enumerate(self.session_rows):
            title = row["title"].replace("\n", " ")
            self.session_list.insert("end", f"{title[:30]}\n  {row['message_count']} 条消息")
            if row["session_id"] == current:
                selected_index = index
        if selected_index is not None:
            self.session_list.selection_set(selected_index)

    def _clear_memory_search(self) -> None:
        self.memory_query.set("")
        self._refresh_memories(force=True)

    def _refresh_memories(self, *, force: bool = False) -> None:
        query = self.memory_query.get()
        try:
            rows = self.controller.memories(query)
        except Exception as exc:
            self.status_var.set(f"读取记忆失败：{exc}")
            return
        if not self.refresh_state.changed(
            "memories", {"query": query, "rows": rows}, force=force
        ):
            return
        for item in self.memory_tree.get_children():
            self.memory_tree.delete(item)
        for record in rows:
            content = str(record.get("content", "")).replace("\n", " ")
            self.memory_tree.insert(
                "",
                "end",
                values=(record.get("kind"), record.get("importance"), record.get("created_at"), content[:260]),
            )

    def _refresh_skills(self, *, force: bool = False) -> None:
        try:
            rows = self.controller.skills()
        except Exception as exc:
            self.status_var.set(f"读取技能失败：{exc}")
            return
        if not self.refresh_state.changed("skills", rows, force=force):
            return
        for item in self.skill_tree.get_children():
            self.skill_tree.delete(item)
        for skill in rows:
            self.skill_tree.insert(
                "",
                "end",
                values=(skill.get("name"), skill.get("risk"), skill.get("description")),
            )

    def _refresh_approvals(self, *, force: bool = False) -> None:
        try:
            rows = self.controller.pending_approvals()
        except Exception as exc:
            self.status_var.set(f"读取审批失败：{exc}")
            return
        if not self.refresh_state.changed("approvals", rows, force=force):
            return
        self.approval_rows = rows
        self.tabs.tab(self.approvals_tab, text=f"审批中心 ({len(rows)})" if rows else "审批中心")
        for item in self.approval_tree.get_children():
            self.approval_tree.delete(item)
        for index, row in enumerate(rows):
            self.approval_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(row.get("tool"), str(row.get("session_id", ""))[:18], row.get("reason")),
            )
        if rows:
            current_id = self.pending_approval.approval_id if self.pending_approval else None
            selected_index = next(
                (index for index, row in enumerate(rows) if row.get("approval_id") == current_id),
                0,
            )
            self.approval_tree.selection_set(str(selected_index))
            self.approval_tree.focus(str(selected_index))
            if self.pending_approval is None:
                try:
                    pending = self.controller.pending_approval(str(rows[selected_index]["approval_id"]))
                    self._present_approval(pending)
                except Exception:
                    pass
            self._show_selected_approval()
        else:
            self.approval_payload.configure(state="normal")
            self.approval_payload.delete("1.0", "end")
            self.approval_payload.insert("1.0", "暂无待审批操作。")
            self.approval_payload.configure(state="disabled")

    def _selected_approval_row(self) -> dict[str, Any] | None:
        selected = self.approval_tree.selection()
        if not selected:
            return None
        index = int(selected[0])
        if not 0 <= index < len(self.approval_rows):
            return None
        return self.approval_rows[index]

    def _show_selected_approval(self, _event: tk.Event | None = None) -> None:
        row = self._selected_approval_row()
        if row is None:
            return
        payload = {
            "approval_id": row.get("approval_id"),
            "session_id": row.get("session_id"),
            "tool": row.get("tool"),
            "reason": row.get("reason"),
            "arguments": row.get("arguments"),
        }
        self.approval_payload.configure(state="normal")
        self.approval_payload.delete("1.0", "end")
        self.approval_payload.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))
        self.approval_payload.configure(state="disabled")

    def _resolve_selected_approval(self, approved: bool) -> None:
        row = self._selected_approval_row()
        if row is None or self.busy:
            return
        try:
            pending = self.controller.pending_approval(str(row["approval_id"]))
        except Exception as exc:
            messagebox.showerror("审批读取失败", str(exc), parent=self.root)
            self._refresh_approvals(force=True)
            return
        self.pending_approval = pending
        self._resolve_pending_approval(approved)

    def _open_selected_approval_session(self) -> None:
        row = self._selected_approval_row()
        if row is None:
            return
        self.controller.select_session(str(row["session_id"]))
        self.session_id_var.set(self.controller.session_id)
        messages, hidden_count = self.controller.message_view()
        self._render_messages(messages, hidden_count=hidden_count, force=True)
        try:
            self.pending_approval = self.controller.pending_approval(str(row["approval_id"]))
            self._present_approval(self.pending_approval)
        except Exception:
            pass
        self.tabs.select(self.chat_tab)

    def _refresh_mcp(self, *, force: bool = False) -> None:
        try:
            payload = self.controller.mcp_status()
        except Exception as exc:
            self.mcp_status_var.set(f"读取 MCP 状态失败：{exc}")
            return
        if not self.refresh_state.changed("mcp", payload, force=force):
            return
        self.mcp_rows = list(payload.get("servers", []))
        sdk = "已安装" if payload.get("sdk_available") else "未安装"
        self.mcp_status_var.set(
            f"官方 MCP Python SDK：{sdk} · 已配置 {len(self.mcp_rows)} 个服务器 · "
            f"已注册 {len(payload.get('registered_tools', []))} 个 MCP 工具 · 配置：{payload.get('config_path')}"
        )
        for item in self.mcp_tree.get_children():
            self.mcp_tree.delete(item)
        for index, row in enumerate(self.mcp_rows):
            self.mcp_tree.insert(
                "",
                "end",
                iid=str(index),
                values=("是" if row.get("enabled") else "否", row.get("name"), row.get("transport"), row.get("endpoint")),
            )

    def _selected_mcp_row(self) -> dict[str, Any] | None:
        selected = self.mcp_tree.selection()
        if not selected:
            return None
        index = int(selected[0])
        return self.mcp_rows[index] if 0 <= index < len(self.mcp_rows) else None

    def _import_mcp_config(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="导入 MCP 配置 JSON",
            filetypes=(("JSON 配置", "*.json"), ("所有文件", "*.*")),
        )
        if not selected:
            return
        if not messagebox.askyesno(
            "导入 MCP 服务器",
            "MCP 服务器可以启动本地进程或连接远程服务。导入后默认保持关闭，只有你手动启用才会运行。继续吗？",
            parent=self.root,
        ):
            return
        self._set_busy(True, "正在导入 MCP 配置…")
        self._run_background("mcp_imported", lambda: self.controller.import_mcp_config(Path(selected)))

    def _toggle_selected_mcp(self) -> None:
        row = self._selected_mcp_row()
        if row is None or self.busy:
            return
        enabled = not bool(row.get("enabled"))
        if enabled and not messagebox.askyesno(
            "启用 MCP 服务器",
            f"准备启用：{row.get('name')}\n\n启用时会启动本地命令或连接远程服务并读取工具清单。以后每次 MCP 工具调用仍会单独审批。继续吗？",
            parent=self.root,
        ):
            return
        self._set_busy(True, "正在更新 MCP 服务器…")
        self._run_background(
            "mcp_updated",
            lambda: self.controller.set_mcp_enabled(str(row["id"]), enabled),
        )

    def _test_selected_mcp(self) -> None:
        row = self._selected_mcp_row()
        if row is None or self.busy:
            return
        if not messagebox.askyesno(
            "测试 MCP 连接",
            f"测试会实际启动或连接 {row.get('name')}，但不会调用其业务工具。继续吗？",
            parent=self.root,
        ):
            return
        self._set_busy(True, "正在测试 MCP 服务器…")
        self._run_background("mcp_test", lambda: self.controller.test_mcp_server(str(row["id"])))

    def _sync_mcp_tools(self) -> None:
        if self.busy:
            return
        self._set_busy(True, "正在同步 MCP 工具…")
        self._run_background("mcp_updated", self.controller.sync_mcp_tools)

    def _remove_selected_mcp(self) -> None:
        row = self._selected_mcp_row()
        if row is None or self.busy:
            return
        if not messagebox.askyesno("删除 MCP 服务器", f"确定删除 {row.get('name')} 的本地配置吗？", parent=self.root):
            return
        self._set_busy(True, "正在删除 MCP 服务器…")
        self._run_background("mcp_updated", lambda: self.controller.remove_mcp_server(str(row["id"])))

    def _refresh_trace(self, *, force: bool = False) -> None:
        rows = self.controller.trace_records()
        trace_id = self.controller.last_trace_id
        if not self.refresh_state.changed(
            "trace", {"trace_id": trace_id, "rows": rows}, force=force
        ):
            return
        self.trace_rows = rows
        self.trace_var.set(f"trace_id: {trace_id or '暂无'}")
        for item in self.trace_tree.get_children():
            self.trace_tree.delete(item)
        for index, record in enumerate(self.trace_rows):
            timestamp = str(record.get("timestamp", ""))
            self.trace_tree.insert("", "end", iid=str(index), values=(timestamp[11:19] or timestamp, record.get("event", "")))
        self.trace_payload.configure(state="normal")
        self.trace_payload.delete("1.0", "end")
        self.trace_payload.configure(state="disabled")

    def _show_trace_payload(self, _event: tk.Event) -> None:
        selected = self.trace_tree.selection()
        if not selected:
            return
        record = self.trace_rows[int(selected[0])]
        self.trace_payload.configure(state="normal")
        self.trace_payload.delete("1.0", "end")
        self.trace_payload.insert("1.0", json.dumps(record, ensure_ascii=False, indent=2))
        self.trace_payload.configure(state="disabled")


    def _import_workspace_files(self) -> None:
        selected = filedialog.askopenfilenames(parent=self.root, title="选择要复制到 Bedrock 工作区的文件")
        if not selected or self.busy:
            return
        if not messagebox.askyesno(
            "导入到工作区",
            f"将 {len(selected)} 个文件复制到：\n{self.controller.workspace_path() / 'imports'}\n\n原文件不会被移动或删除。继续吗？",
            parent=self.root,
        ):
            return
        self._set_busy(True, "正在复制文件到工作区…")
        self._run_background(
            "workspace_imported",
            lambda: self.controller.import_workspace_paths([Path(item) for item in selected]),
        )

    def _import_workspace_folder(self) -> None:
        selected = filedialog.askdirectory(parent=self.root, title="选择要复制到 Bedrock 工作区的文件夹")
        if not selected or self.busy:
            return
        source = Path(selected)
        if not messagebox.askyesno(
            "导入项目文件夹",
            f"把整个文件夹复制到：\n{self.controller.workspace_path() / 'imports'}\n\n符号链接和 Windows 重解析点会被拒绝，原文件夹不会被修改。继续吗？",
            parent=self.root,
        ):
            return
        self._set_busy(True, "正在复制文件夹到工作区…")
        self._run_background(
            "workspace_imported",
            lambda: self.controller.import_workspace_paths([source]),
        )

    def _selected_app_row(self) -> dict[str, Any] | None:
        selected = self.app_tree.selection()
        if not selected:
            return None
        index = int(selected[0])
        return self.app_rows[index] if 0 <= index < len(self.app_rows) else None

    @staticmethod
    def _choose_application_file(root: tk.Tk, title: str) -> str:
        return filedialog.askopenfilename(
            parent=root,
            title=title,
            filetypes=(
                ("Windows 应用或快捷方式", ("*.exe", "*.lnk")),
                ("Windows 程序", "*.exe"),
                ("开始菜单快捷方式", "*.lnk"),
                ("所有文件", "*.*"),
            ),
        )

    def _add_custom_application(self) -> None:
        selected = self._choose_application_file(self.root, "选择可信的常用程序或开始菜单快捷方式")
        if not selected:
            return
        path = Path(selected)
        name = simpledialog.askstring(
            "应用名称",
            "输入你平时会对 Bedrock 说的应用名称：",
            initialvalue=path.stem,
            parent=self.root,
        )
        if not name:
            return
        aliases_text = simpledialog.askstring(
            "应用别名（可选）",
            "多个别名用逗号分隔，例如：微信,wechat：",
            initialvalue="",
            parent=self.root,
        ) or ""
        aliases = [item.strip() for item in aliases_text.replace("，", ",").split(",") if item.strip()]
        if not messagebox.askyesno(
            "加入应用白名单",
            f"名称：{name}\n路径：{path}\n\n加入后模型只能用名称选择它，不能自行更换路径；每次启动仍需你审批。继续吗？",
            parent=self.root,
        ):
            return
        try:
            self.controller.add_allowed_app(name, path, aliases)
        except Exception as exc:
            messagebox.showerror("添加应用失败", str(exc), parent=self.root)
            return
        self._refresh_capabilities(force=True)

    def _change_selected_app_path(self) -> None:
        row = self._selected_app_row()
        if row is None:
            return
        selected = self._choose_application_file(self.root, f"为 {row.get('name')} 选择可信程序")
        if not selected:
            return
        try:
            self.controller.configure_allowed_app(str(row["id"]), Path(selected))
        except Exception as exc:
            messagebox.showerror("保存应用路径失败", str(exc), parent=self.root)
            return
        self._refresh_capabilities(force=True)

    def _remove_selected_custom_app(self) -> None:
        row = self._selected_app_row()
        if row is None:
            return
        if not str(row.get("id", "")).startswith("custom_"):
            messagebox.showinfo("不能移除内置条目", "内置应用可以更换可信路径，但不能从列表中删除。", parent=self.root)
            return
        if not messagebox.askyesno("移除应用", f"从本地白名单移除 {row.get('name')}？", parent=self.root):
            return
        try:
            self.controller.remove_allowed_app(str(row["id"]))
        except Exception as exc:
            messagebox.showerror("移除应用失败", str(exc), parent=self.root)
            return
        self._refresh_capabilities(force=True)

    def _ask_agent_to_open_selected_app(self) -> None:
        row = self._selected_app_row()
        if row is None:
            return
        self._insert_prompt(f"请打开{row.get('name')}。")

    def _refresh_capabilities(self, *, force: bool = False) -> None:
        if not hasattr(self, "capability_tree"):
            return
        try:
            apps = self.controller.allowed_apps(force_refresh=force)
            rows = self.controller.capability_status(force_refresh=False)
            dashboard = self.controller.learning_dashboard(days=30)
        except Exception as exc:
            self.learning_summary_var.set(f"能力状态读取失败：{exc}")
            return
        payload = {"rows": rows, "apps": apps, "dashboard": dashboard}
        if not self.refresh_state.changed("capabilities", payload, force=force):
            return
        self.workspace_path_var.set(str(self.controller.workspace_path()))
        self.app_rows = list(apps)
        for item in self.app_tree.get_children():
            self.app_tree.delete(item)
        for index, row in enumerate(self.app_rows):
            self.app_tree.insert(
                "",
                "end",
                iid=str(index),
                values=("可用" if row.get("available") else "未配置", row.get("name"), row.get("executable") or "—"),
            )
        for item in self.capability_tree.get_children():
            self.capability_tree.delete(item)
        for row in rows:
            self.capability_tree.insert(
                "",
                "end",
                values=(
                    "可用" if row.get("ready") else "需配置",
                    row.get("name", ""),
                    row.get("detail", ""),
                    ", ".join(row.get("tools", [])),
                ),
            )
        self.learning_summary_var.set(
            f"近30天学习：{dashboard['sessions']} 次 · {dashboard['minutes']} 分钟 · "
            f"待复习 {dashboard['due_reviews']} 项"
        )

    def _refresh_security(self, *, force: bool = False) -> None:
        summary = self.controller.security_summary()
        if not self.refresh_state.changed("security", summary, force=force):
            return
        for widget in self.security_grid.winfo_children():
            widget.destroy()
        for row, (key, value) in enumerate(summary.items()):
            ttk.Label(self.security_grid, text=key, style="PanelMuted.TLabel").grid(row=row, column=0, sticky="nw", padx=(0, 20), pady=7)
            ttk.Label(self.security_grid, text=value, style="Panel.TLabel", wraplength=700, justify="left").grid(row=row, column=1, sticky="nw", pady=7)
        self.security_grid.columnconfigure(1, weight=1)

    def _open_workspace(self) -> None:
        self.controller.open_path(self.controller.runtime.settings.workspace)

    def _open_private(self) -> None:
        self.controller.open_path(self.controller.runtime.settings.data_dir)

    def _open_docs(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        docs = project_root / "DESKTOP.md"
        if docs.exists():
            self.controller.open_path(docs.parent)
        else:
            webbrowser.open("https://example.invalid")

    def _on_close(self) -> None:
        if self.pending_approval is not None:
            if not messagebox.askyesno(
                "退出 Bedrock",
                "当前仍有一项操作等待审批。退出不会执行该操作，确定退出吗？",
                parent=self.root,
            ):
                self.tabs.select(self.chat_tab)
                return
        elif self.busy and not messagebox.askyesno(
            "退出 Bedrock", "Agent 仍在处理任务，确定退出吗？", parent=self.root
        ):
            return
        self._closing = True
        try:
            self.controller.close()
        finally:
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        settings = Settings.from_env()
        config_store = EnvModelConfigStore(settings.env_path)
        if not settings.api_key:
            print("Bedrock 正在打开 DeepSeek 首次配置窗口……")
            saved = ModelConfigDialog(root, config_store, required=True).wait()
            if not saved:
                root.destroy()
                return
            settings = Settings.from_env(settings.env_path)
        runtime = build_runtime(settings)
        controller = DesktopController(runtime)
        root.deiconify()
        root.lift()
        try:
            root.attributes("-topmost", True)
            root.after(600, lambda: root.attributes("-topmost", False))
        except tk.TclError:
            pass
        BedrockDesktop(root, controller)
        root.after_idle(root.focus_force)
    except Exception as exc:
        root.withdraw()
        messagebox.showerror(
            "Bedrock 无法启动",
            f"启动失败：{exc}\n\n请检查 DeepSeek 配置和本地目录权限。",
            parent=root,
        )
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
