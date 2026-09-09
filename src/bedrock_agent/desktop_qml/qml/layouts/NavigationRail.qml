import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

GlassCard {
    id: root
    property var vm
    property bool compact: false
    property bool showUser: true
    implicitWidth: compact ? 66 : 214
    corner: bedrock.currentTheme === "wechat" ? 0 : Number(bedrock.themeData.corner || 16)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.compact ? 7 : 12
        spacing: 7
        Repeater {
            model: [
                ["dashboard", "任务总览", "◈"], ["chat", "Agent 对话", "◇"], ["tasks", "任务管理", "▣"],
                ["approvals", "审批中心", "!"], ["workspace", "工作区", "▤"], ["apps", "应用管理", "◉"],
                ["learning", "学习管理", "△"], ["skills", "Skills", "✦"], ["mcp", "MCP", "M"],
                ["memory", "长期记忆", "◎"], ["traces", "运行轨迹", "⌁"], ["settings", "设置", "⚙"]
            ]
            NavButton {
                required property var modelData
                Layout.fillWidth: true
                text: modelData[1]
                iconText: modelData[2]
                compact: root.compact
                selected: root.vm.currentPage === modelData[0]
                onClicked: root.vm.openPage(modelData[0])
            }
        }
        Item { Layout.fillHeight: true }
        Rectangle { Layout.fillWidth: true; height: 1; color: bedrock.themeData.border; visible: root.showUser }
        RowLayout {
            Layout.fillWidth: true; spacing: 10; visible: root.showUser && !root.compact
            Rectangle { width: 34; height: 34; radius: 11; color: bedrock.themeData.accent_soft; border.width: 1; border.color: bedrock.themeData.border_strong; Text { anchors.centerIn: parent; text: "BR"; color: bedrock.themeData.accent; font.pixelSize: 10; font.weight: Font.Bold } }
            ColumnLayout { Layout.fillWidth: true; spacing: 1; Text { text: "本地用户"; color: bedrock.themeData.text_primary; font.pixelSize: 11 } Text { text: "沙箱已启用"; color: bedrock.themeData.success; font.pixelSize: 9 } }
        }
    }
}
