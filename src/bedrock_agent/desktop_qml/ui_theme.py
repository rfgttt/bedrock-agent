from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


THEMES: dict[str, dict[str, Any]] = {
    "cel": {
        "theme_id": "cel",
        "label": "二次元赛璐璐",
        "description": "清新、柔和、低装饰的陪伴型工作台",
        "layout": "cel",
        "dark": False,
        "bg": "#eef6ff",
        "bg_alt": "#fff8f4",
        "surface": "#f8fbff",
        "surface_alt": "#edf5ff",
        "surface_strong": "#ffffff",
        "border": "#c9d9ea",
        "border_strong": "#91b9dc",
        "text_primary": "#294662",
        "text_secondary": "#55718b",
        "text_muted": "#8399ac",
        "accent": "#69aef8",
        "accent_soft": "#d8ebff",
        "accent_text": "#173b5c",
        "danger": "#e96678",
        "warning": "#e9a44d",
        "success": "#56bca0",
        "user_bubble": "#d9ecff",
        "assistant_bubble": "#ffffff",
        "tool_bubble": "#fff4d8",
        "input_bg": "#ffffff",
        "shadow": "#203b5260",
        "corner": 18,
        "panel_opacity": 0.96,
    },
    "glass": {
        "theme_id": "glass",
        "label": "科技玻璃",
        "description": "深空渐变、磨砂玻璃与青紫流光",
        "layout": "glass",
        "dark": True,
        "bg": "#050913",
        "bg_alt": "#071c25",
        "surface": "#0b1720",
        "surface_alt": "#102632",
        "surface_strong": "#0d1d27",
        "border": "#2b6371",
        "border_strong": "#42d8c8",
        "text_primary": "#edfaff",
        "text_secondary": "#a9c7cf",
        "text_muted": "#6f929b",
        "accent": "#43f0c0",
        "accent_soft": "#123f42",
        "accent_text": "#031a18",
        "danger": "#ff6f8c",
        "warning": "#ffd06a",
        "success": "#43f0a2",
        "user_bubble": "#14354e",
        "assistant_bubble": "#0f2c2d",
        "tool_bubble": "#352b17",
        "input_bg": "#09141d",
        "shadow": "#00000090",
        "corner": 19,
        "panel_opacity": 0.84,
    },
    "wechat": {
        "theme_id": "wechat",
        "label": "微信简洁",
        "description": "会话优先、熟悉直接的三栏聊天体验",
        "layout": "wechat",
        "dark": False,
        "bg": "#f3f3f3",
        "bg_alt": "#ededed",
        "surface": "#ffffff",
        "surface_alt": "#f7f7f7",
        "surface_strong": "#ffffff",
        "border": "#dedede",
        "border_strong": "#bfc7c2",
        "text_primary": "#1f1f1f",
        "text_secondary": "#606060",
        "text_muted": "#999999",
        "accent": "#07c160",
        "accent_soft": "#dff6e9",
        "accent_text": "#ffffff",
        "danger": "#e64340",
        "warning": "#e2a133",
        "success": "#07c160",
        "user_bubble": "#95ec69",
        "assistant_bubble": "#ffffff",
        "tool_bubble": "#fff7d9",
        "input_bg": "#ffffff",
        "shadow": "#00000028",
        "corner": 8,
        "panel_opacity": 1.0,
    },
    "codex": {
        "theme_id": "codex",
        "label": "Codex 工作台",
        "description": "克制的开发者 Agent 控制台与任务上下文",
        "layout": "codex",
        "dark": True,
        "bg": "#0c0d0e",
        "bg_alt": "#111315",
        "surface": "#131517",
        "surface_alt": "#181b1e",
        "surface_strong": "#101214",
        "border": "#2a2e32",
        "border_strong": "#495158",
        "text_primary": "#f1f3f4",
        "text_secondary": "#a8adb2",
        "text_muted": "#686e74",
        "accent": "#66d49b",
        "accent_soft": "#183126",
        "accent_text": "#07150e",
        "danger": "#ff6b75",
        "warning": "#d8b269",
        "success": "#66d49b",
        "user_bubble": "#1c242a",
        "assistant_bubble": "#151a18",
        "tool_bubble": "#272316",
        "input_bg": "#101214",
        "shadow": "#00000080",
        "corner": 10,
        "panel_opacity": 1.0,
    },
}

DEFAULT_THEME = "glass"


def theme_rows() -> list[dict[str, Any]]:
    return [dict(THEMES[key]) for key in ("cel", "glass", "wechat", "codex")]


@dataclass(slots=True)
class ThemePreferenceStore:
    path: Path

    def load(self) -> str:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return DEFAULT_THEME
        selected = str(payload.get("theme") or DEFAULT_THEME)
        return selected if selected in THEMES else DEFAULT_THEME

    def save(self, theme_id: str) -> None:
        if theme_id not in THEMES:
            raise ValueError(f"Unknown theme: {theme_id}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps({"theme": theme_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
