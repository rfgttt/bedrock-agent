from bedrock_agent.desktop_qml.help_catalog import help_presets


def test_help_catalog_has_actionable_safe_presets() -> None:
    rows = help_presets()
    assert len(rows) >= 12
    assert len({row["preset_id"] for row in rows}) == len(rows)
    assert all(row["title"] and row["prompt"] and row["category"] for row in rows)
    assert any(row["preset_id"] == "open_app" and row["needs_approval"] for row in rows)
    assert any(row["preset_id"] == "syntax" and not row["needs_approval"] for row in rows)
