from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from bedrock_agent.config import DEEPSEEK_BASE_URL, DEEPSEEK_MODELS
from bedrock_agent.model_config import DeepSeekConfig, EnvModelConfigStore


class ModelConfigDialog:
    def __init__(
        self,
        parent: tk.Misc,
        store: EnvModelConfigStore,
        *,
        required: bool = False,
    ) -> None:
        self.store = store
        self.required = required
        self.saved = False
        current = store.load()

        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.window.title("DeepSeek 模型配置")
        self.window.geometry("620x390")
        self.window.minsize(560, 350)
        # A transient window can remain hidden on Windows when its parent is withdrawn.
        # Only attach it to a visible parent, then explicitly surface it below.
        if parent.winfo_viewable():
            self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self._cancel)

        frame = ttk.Frame(self.window, padding=22)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="DeepSeek 模型配置", font=("Microsoft YaHei UI", 16, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        ttk.Label(
            frame,
            text="密钥只保存在本机 .env 文件中。桌面 Agent 不会开放网络端口。",
            wraplength=540,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 22))

        self.api_key_var = tk.StringVar(value=current.api_key)
        self.base_url_var = tk.StringVar(value=current.base_url or DEEPSEEK_BASE_URL)
        self.model_var = tk.StringVar(value=current.model)
        self.show_key_var = tk.BooleanVar(value=False)

        ttk.Label(frame, text="API Key").grid(row=2, column=0, sticky="w", pady=7)
        self.key_entry = ttk.Entry(frame, textvariable=self.api_key_var, show="●")
        self.key_entry.grid(row=2, column=1, sticky="ew", pady=7)
        ttk.Checkbutton(frame, text="显示", variable=self.show_key_var, command=self._toggle_key).grid(
            row=2, column=2, padx=(10, 0)
        )

        ttk.Label(frame, text="API 地址").grid(row=3, column=0, sticky="w", pady=7)
        base_entry = ttk.Entry(frame, textvariable=self.base_url_var, state="readonly")
        base_entry.grid(row=3, column=1, columnspan=2, sticky="ew", pady=7)

        ttk.Label(frame, text="模型").grid(row=4, column=0, sticky="w", pady=7)
        model_box = ttk.Combobox(frame, textvariable=self.model_var, values=DEEPSEEK_MODELS, state="normal")
        model_box.grid(row=4, column=1, columnspan=2, sticky="ew", pady=7)

        ttk.Label(
            frame,
            text="默认使用 deepseek-v4-flash；需要更强能力时可选择 deepseek-v4-pro。",
            wraplength=540,
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 20))

        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=3, sticky="e")
        if not required:
            ttk.Button(buttons, text="取消", command=self._cancel).pack(side="right")
        ttk.Button(buttons, text="保存", command=self._save).pack(side="right", padx=(0, 10))

        frame.columnconfigure(1, weight=1)
        self._show_in_foreground()

    def _show_in_foreground(self) -> None:
        """Center the first-run dialog and make it visible above the console window."""
        self.window.update_idletasks()
        width = max(self.window.winfo_reqwidth(), 620)
        height = max(self.window.winfo_reqheight(), 390)
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.deiconify()
        self.window.lift()
        try:
            self.window.attributes("-topmost", True)
            self.window.after(600, lambda: self.window.attributes("-topmost", False))
        except tk.TclError:
            pass
        self.window.grab_set()
        self.window.after_idle(self.key_entry.focus_force)

    def _toggle_key(self) -> None:
        self.key_entry.configure(show="" if self.show_key_var.get() else "●")

    def _save(self) -> None:
        config = DeepSeekConfig(
            api_key=self.api_key_var.get(),
            base_url=self.base_url_var.get(),
            model=self.model_var.get(),
        )
        try:
            self.store.save(config)
        except Exception as exc:
            messagebox.showerror("配置未保存", str(exc), parent=self.window)
            return
        self.saved = True
        self.window.grab_release()
        self.window.destroy()

    def _cancel(self) -> None:
        if self.required:
            messagebox.showwarning("需要模型配置", "首次启动必须先填写 DeepSeek API Key。", parent=self.window)
            return
        self.window.grab_release()
        self.window.destroy()

    def wait(self) -> bool:
        self.window.wait_window()
        return self.saved
