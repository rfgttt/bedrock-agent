from pathlib import Path


def test_qml_desktop_assets_are_packaged_and_modular() -> None:
    root = Path(__file__).parents[1] / "src" / "bedrock_agent" / "desktop_qml" / "qml"
    expected = {
        "Main.qml",
        "components/GlassCard.qml",
        "components/NavButton.qml",
        "components/ChatMessage.qml",
        "components/TaskPrism.qml",
        "pages/DashboardPage.qml",
        "pages/ChatPage.qml",
        "pages/ApprovalsPage.qml",
        "pages/WorkspacePage.qml",
        "pages/AppsPage.qml",
        "pages/McpPage.qml",
        "layouts/CelShell.qml",
        "layouts/GlassShell.qml",
        "layouts/WechatShell.qml",
        "layouts/CodexShell.qml",
        "layouts/SessionsRail.qml",
    }
    assert all((root / item).is_file() for item in expected)
    main = (root / "Main.qml").read_text(encoding="utf-8")
    assert "帮助与预设 Skills" in main
    assert "Loader" in main  # current page only; hidden pages are not kept alive
    assert "Agent 状态" not in main or "agentPanel" in main


def test_qml_child_objects_do_not_use_javascript_semicolon_separator() -> None:
    """QML child objects are declarations, not JavaScript statements.

    Qt 6.11 rejects ``Text { ... }; Text { ... }`` with
    ``Unexpected token ';'``. Keep this guard even though the real QML
    engine smoke test remains the source of truth on Windows.
    """
    import re

    root = Path(__file__).parents[1] / "src" / "bedrock_agent" / "desktop_qml" / "qml"
    invalid = re.compile(r"}\s*;\s*(?:[A-Z][A-Za-z0-9_]*|axis)\s*{")
    failures: list[str] = []
    for qml_file in root.rglob("*.qml"):
        text = qml_file.read_text(encoding="utf-8")
        if invalid.search(text):
            failures.append(str(qml_file.relative_to(root)))
    assert failures == []


def test_task_prism_is_interactive_bounded_and_not_a_static_repeater() -> None:
    root = Path(__file__).parents[1] / "src" / "bedrock_agent" / "desktop_qml" / "qml"
    prism = (root / "components" / "TaskPrism.qml").read_text(encoding="utf-8")
    dashboard = (root / "pages" / "DashboardPage.qml").read_text(encoding="utf-8")

    assert "PathView" in prism
    assert "PathView.SnapToItem" in prism
    assert "WheelHandler" in prism
    assert "Keys.onLeftPressed" in prism
    assert "Keys.onRightPressed" in prism
    assert "pathItemCount: Math.min(root.taskCount, root.visibleCardLimit)" in prism
    assert "visibleCardLimit: 7" in prism
    assert "Rotation" in prism and "cardAngle" in prism
    assert "TaskPrism" in dashboard
    assert "Repeater {\n                            model: Math.min(vm.tasksModel.count" not in dashboard


def test_chat_delegate_uses_unambiguous_message_role_and_layout() -> None:
    root = Path(__file__).parents[1] / "src" / "bedrock_agent" / "desktop_qml" / "qml"
    chat_page = (root / "pages" / "ChatPage.qml").read_text(encoding="utf-8")
    chat_message = (root / "components" / "ChatMessage.qml").read_text(encoding="utf-8")

    assert "required property string message_text" in chat_page
    assert "messageText: message_text" in chat_page
    assert "property string messageText" in chat_message
    assert "visibleText" in chat_message
    assert "ColumnLayout" in chat_message
    assert "property string body" not in chat_message


def test_buttons_keep_text_contrast_without_white_hover_fill() -> None:
    root = Path(__file__).parents[1] / "src" / "bedrock_agent" / "desktop_qml" / "qml" / "components"
    action = (root / "ActionButton.qml").read_text(encoding="utf-8")
    section = (root / "SectionTitle.qml").read_text(encoding="utf-8")

    assert 'root.primary ? bedrock.themeData.accent : "transparent"' in action
    assert "root.hovered ? bedrock.themeData.accent" in action
    assert "Behavior on color" not in action
    assert "ActionButton" in section


def test_theme_shells_and_delete_conversation_controls_exist() -> None:
    root = Path(__file__).parents[1] / "src" / "bedrock_agent" / "desktop_qml" / "qml"
    main = (root / "Main.qml").read_text(encoding="utf-8")
    chat = (root / "pages" / "ChatPage.qml").read_text(encoding="utf-8")
    sessions = (root / "layouts" / "SessionsRail.qml").read_text(encoding="utf-8")

    for theme_id in ("cel", "glass", "wechat", "codex"):
        assert theme_id in main
    assert "themeOptionsModel" in main
    assert "confirmDeleteSession" in main
    assert "删除当前会话" in chat
    assert "requestDeleteSession" in sessions
