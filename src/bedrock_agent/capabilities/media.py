from __future__ import annotations

import ctypes
import sys
import time
from typing import Any, Callable

from bedrock_agent.tools.base import RiskLevel, Tool


_MEDIA_KEYS = {
    "play_pause": 0xB3,
    "next": 0xB0,
    "previous": 0xB1,
    "volume_up": 0xAF,
    "volume_down": 0xAE,
    "mute": 0xAD,
    "stop": 0xB2,
}


class WindowsMediaController:
    def __init__(
        self,
        *,
        key_sender: Callable[[int], None] | None = None,
        platform_name: str | None = None,
    ) -> None:
        self.platform_name = platform_name or sys.platform
        self._key_sender = key_sender or self._send_windows_key

    @staticmethod
    def _send_windows_key(key_code: int) -> None:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        key_up = 0x0002
        user32.keybd_event(key_code, 0, 0, 0)
        user32.keybd_event(key_code, 0, key_up, 0)

    def control(self, action: str, repeat: int = 1) -> dict[str, Any]:
        if not self.platform_name.startswith("win"):
            raise OSError("System media control currently supports Windows only")
        if action not in _MEDIA_KEYS:
            raise ValueError(f"Unsupported media action: {action}")
        if isinstance(repeat, bool) or not 1 <= repeat <= 10:
            raise ValueError("repeat must be an integer between 1 and 10")
        for index in range(repeat):
            self._key_sender(_MEDIA_KEYS[action])
            if index + 1 < repeat:
                time.sleep(0.04)
        return {"action": action, "repeat": repeat, "sent": True}


def build_media_tools(controller: WindowsMediaController) -> list[Tool]:
    return [
        Tool(
            name="control_system_media",
            description=(
                "Control the current Windows media session using a system media key. "
                "Actions: play_pause, next, previous, volume_up, volume_down, mute, stop. "
                "Requires local approval."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "repeat": {"type": "integer"},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
            handler=lambda arguments: controller.control(
                arguments["action"], arguments.get("repeat", 1)
            ),
            risk=RiskLevel.EXTERNAL,
        )
    ]
