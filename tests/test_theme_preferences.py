from __future__ import annotations

import json
from pathlib import Path

import pytest

from bedrock_agent.desktop_qml.ui_theme import DEFAULT_THEME, THEMES, ThemePreferenceStore, theme_rows


def test_four_theme_profiles_are_complete_and_distinct() -> None:
    assert set(THEMES) == {"cel", "glass", "wechat", "codex"}
    assert {row["layout"] for row in theme_rows()} == {"cel", "glass", "wechat", "codex"}
    for theme_id, theme in THEMES.items():
        assert theme["theme_id"] == theme_id
        for key in (
            "label", "description", "bg", "surface", "surface_alt", "surface_strong",
            "border", "text_primary", "text_secondary", "accent", "input_bg",
        ):
            assert theme[key]


def test_theme_preference_store_round_trips_and_rejects_unknown_theme(tmp_path: Path) -> None:
    store = ThemePreferenceStore(tmp_path / "private" / "ui_preferences.json")
    assert store.load() == DEFAULT_THEME

    store.save("wechat")

    assert store.load() == "wechat"
    assert json.loads(store.path.read_text(encoding="utf-8"))["theme"] == "wechat"
    with pytest.raises(ValueError):
        store.save("unknown")
