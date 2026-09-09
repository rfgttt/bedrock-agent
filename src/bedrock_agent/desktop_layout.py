from __future__ import annotations


def centered_geometry(
    requested_width: int,
    requested_height: int,
    screen_width: int,
    screen_height: int,
    *,
    margin: int = 48,
) -> str:
    """Return a centered Tk geometry string that always fits on screen."""

    available_width = max(320, screen_width - margin * 2)
    available_height = max(260, screen_height - margin * 2)
    width = min(max(320, requested_width), available_width)
    height = min(max(260, requested_height), available_height)
    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)
    return f"{width}x{height}+{x}+{y}"
