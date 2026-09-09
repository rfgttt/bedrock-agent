import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "layouts"

ApplicationWindow {
    id: window
    width: 1540
    height: 940
    minimumWidth: 1120
    minimumHeight: 720
    visible: true
    title: "Bedrock Agent v0.6.0 · " + bedrock.themeData.label
    color: bedrock.themeData.bg

    property string toastTitle: ""
    property string toastText: ""
    property string deleteSessionId: ""
    property string deleteSessionTitle: ""

    function shellComponent(themeId) {
        if (themeId === "cel") return celShell
        if (themeId === "wechat") return wechatShell
        if (themeId === "codex") return codexShell
        return glassShell
    }

    Loader {
        id: shellLoader
        anchors.fill: parent
        sourceComponent: window.shellComponent(bedrock.currentTheme)
        onLoaded: if (item) item.vm = bedrock
    }

    Component { id: celShell; CelShell { onHelpRequested: helpPopup.open(); onThemeRequested: themePopup.open() } }
    Component { id: glassShell; GlassShell { onHelpRequested: helpPopup.open(); onThemeRequested: themePopup.open() } }
    Component { id: wechatShell; WechatShell { onHelpRequested: helpPopup.open(); onThemeRequested: themePopup.open() } }
    Component { id: codexShell; CodexShell { onHelpRequested: helpPopup.open(); onThemeRequested: themePopup.open() } }

    Popup {
        id: themePopup
        anchors.centerIn: Overlay.overlay
        width: Math.min(window.width - 80, 940)
        height: Math.min(window.height - 100, 610)
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: GlassCard { corner: 24; highlighted: true }
        contentItem: ColumnLayout {
            spacing: 16
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout { Layout.fillWidth: true; Text { text: "主题中心"; color: bedrock.themeData.text_primary; font.pixelSize: 24; font.weight: Font.DemiBold } Text { text: "切换只更新表现层，不重载会话、模型、记忆或工作区数据。"; color: bedrock.themeData.text_secondary; font.pixelSize: 11 } }
                ActionButton { text: "关闭"; onClicked: themePopup.close() }
            }
            GridView {
                Layout.fillWidth: true; Layout.fillHeight: true
                cellWidth: 430; cellHeight: 235; model: bedrock.themeOptionsModel; clip: true
                delegate: GlassCard {
                    required property string theme_id
                    required property string label
                    required property string description
                    required property string layout
                    required property bool dark
                    required property string accent
                    required property string surface
                    required property string bg
                    width: 414; height: 216; hoverable: true; highlighted: theme_id === bedrock.currentTheme
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 16; spacing: 10
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 102; radius: 14; color: bg; border.width: 1; border.color: accent
                            Row {
                                anchors.fill: parent; anchors.margins: 10; spacing: 7
                                Rectangle { width: 62; height: parent.height; radius: 8; color: surface; opacity: 0.92 }
                                Column { width: parent.width - 80; spacing: 7; Rectangle { width: parent.width; height: 18; radius: 7; color: surface; opacity: 0.94 } Row { spacing: 7; Repeater { model: 3; Rectangle { width: 62; height: 50; radius: 8; color: index === 1 ? accent : surface; opacity: index === 1 ? 0.75 : 0.94 } } } }
                            }
                        }
                        RowLayout { Layout.fillWidth: true; Text { text: label; color: bedrock.themeData.text_primary; font.pixelSize: 17; font.weight: Font.DemiBold; Layout.fillWidth: true } Text { text: theme_id === bedrock.currentTheme ? "正在使用" : layout; color: theme_id === bedrock.currentTheme ? bedrock.themeData.success : bedrock.themeData.text_muted; font.pixelSize: 10 } }
                        Text { Layout.fillWidth: true; text: description; color: bedrock.themeData.text_secondary; font.pixelSize: 11; wrapMode: Text.Wrap }
                        Item { Layout.fillHeight: true }
                        ActionButton { Layout.alignment: Qt.AlignRight; text: theme_id === bedrock.currentTheme ? "已应用" : "应用主题"; primary: theme_id !== bedrock.currentTheme; enabled: theme_id !== bedrock.currentTheme; onClicked: { bedrock.setTheme(theme_id); themePopup.close() } }
                    }
                }
            }
        }
    }

    Popup {
        id: helpPopup
        anchors.centerIn: Overlay.overlay
        width: Math.min(window.width - 100, 1040)
        height: Math.min(window.height - 80, 740)
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: GlassCard { corner: 24; highlighted: true }
        contentItem: ColumnLayout {
            spacing: 14
            RowLayout { Layout.fillWidth: true; Text { text: "帮助与预设 Skills"; color: bedrock.themeData.text_primary; font.pixelSize: 22; font.weight: Font.DemiBold; Layout.fillWidth: true } ActionButton { text: "关闭"; onClicked: helpPopup.close() } }
            Text { Layout.fillWidth: true; text: "点击“填入对话”查看提示词，或直接测试。直接测试也不会绕过审批。"; color: bedrock.themeData.text_secondary; font.pixelSize: 11; wrapMode: Text.Wrap }
            GridView {
                Layout.fillWidth: true; Layout.fillHeight: true
                cellWidth: 320; cellHeight: 205; model: bedrock.helpModel; clip: true
                delegate: GlassCard {
                    required property int index
                    required property string title
                    required property string description
                    required property string category
                    required property string risk
                    required property bool needs_approval
                    required property string requirement
                    width: 306; height: 190; hoverable: true
                    ColumnLayout { anchors.fill: parent; anchors.margins: 15; spacing: 7
                        RowLayout { Layout.fillWidth: true; Text { text: category; color: bedrock.themeData.accent; font.pixelSize: 9 } Item { Layout.fillWidth: true } Text { text: risk + (needs_approval ? " · 需审批" : ""); color: needs_approval ? bedrock.themeData.warning : bedrock.themeData.text_muted; font.pixelSize: 9 } }
                        Text { text: title; color: bedrock.themeData.text_primary; font.pixelSize: 16; font.weight: Font.DemiBold }
                        Text { Layout.fillWidth: true; Layout.fillHeight: true; text: description; color: bedrock.themeData.text_secondary; font.pixelSize: 11; wrapMode: Text.Wrap }
                        Text { Layout.fillWidth: true; text: requirement; color: bedrock.themeData.text_muted; font.pixelSize: 9; elide: Text.ElideRight }
                        RowLayout { Layout.fillWidth: true; ActionButton { text: "填入对话"; onClicked: { bedrock.usePreset(index, false); helpPopup.close() } } Item { Layout.fillWidth: true } ActionButton { text: "直接测试"; primary: true; onClicked: { bedrock.usePreset(index, true); helpPopup.close() } } }
                    }
                }
            }
        }
    }

    Popup {
        id: deletePopup
        anchors.centerIn: Overlay.overlay
        width: 470
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape
        background: GlassCard { corner: 20; highlighted: true }
        contentItem: ColumnLayout {
            spacing: 14
            Text { text: "删除会话？"; color: bedrock.themeData.text_primary; font.pixelSize: 21; font.weight: Font.DemiBold }
            Text { Layout.fillWidth: true; text: "将删除会话“" + window.deleteSessionTitle + "”及其消息和待审批项。长期记忆、Skills、工作区文件和其他会话不会被删除。"; color: bedrock.themeData.text_secondary; font.pixelSize: 12; wrapMode: Text.Wrap }
            Rectangle { Layout.fillWidth: true; height: 1; color: bedrock.themeData.border }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } ActionButton { text: "取消"; onClicked: deletePopup.close() } ActionButton { text: "确认删除"; danger: true; onClicked: { var id = window.deleteSessionId; deletePopup.close(); bedrock.confirmDeleteSession(id) } } }
        }
    }

    Rectangle {
        id: toast
        width: 360
        implicitHeight: toastColumn.implicitHeight + 26
        radius: 16
        color: bedrock.themeData.surface_strong
        border.width: 1
        border.color: bedrock.themeData.border_strong
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 24
        visible: opacity > 0
        opacity: 0
        z: 1000
        Column { id: toastColumn; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 13; spacing: 4; Text { text: window.toastTitle; color: bedrock.themeData.accent; font.pixelSize: 12; font.weight: Font.DemiBold } Text { width: parent.width; text: window.toastText; color: bedrock.themeData.text_primary; font.pixelSize: 11; wrapMode: Text.Wrap } }
        Behavior on opacity { NumberAnimation { duration: 150 } }
        Timer { id: toastTimer; interval: 3600; onTriggered: toast.opacity = 0 }
    }

    Connections {
        target: bedrock
        function onNotification(title, text) {
            window.toastTitle = title
            window.toastText = text
            toast.opacity = 1
            toastTimer.restart()
        }
        function onDeleteSessionRequested(sessionId, title) {
            window.deleteSessionId = sessionId
            window.deleteSessionTitle = title
            deletePopup.open()
        }
    }
}
