import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    property var vm
    spacing: 14
    SectionTitle { Layout.fillWidth: true; title: "MCP 连接"; subtitle: "外部工具默认禁用，每次调用仍需审批"; actionText: "刷新"; onAction: vm.refreshMcp() }
    RowLayout { ActionButton { text: "导入配置"; primary: true; onClicked: vm.importMcpConfig() } ActionButton { text: "同步工具"; onClicked: vm.syncMcp() } Item { Layout.fillWidth: true } }
    ListView {
        Layout.fillWidth: true; Layout.fillHeight: true; model: vm.mcpModel; spacing: 10; clip: true; reuseItems: true
        delegate: GlassCard {
            required property string name
            required property string server_id
            required property string transport
            required property bool server_enabled
            required property string status
            required property int tools
            required property string error
            width: ListView.view.width; height: 106; highlighted: server_enabled
            RowLayout { anchors.fill: parent; anchors.margins: 16; spacing: 14
                Rectangle { width: 46; height: 46; radius: 15; color: bedrock.themeData.accent_soft; border.width: 1; border.color: bedrock.themeData.border_strong; Text { anchors.centerIn: parent; text: "M"; color: bedrock.themeData.accent; font.pixelSize: 19; font.weight: Font.Bold } }
                ColumnLayout { Layout.fillWidth: true; Text { text: name; color: bedrock.themeData.text_primary; font.pixelSize: 15; font.weight: Font.DemiBold } Text { text: transport + " · " + tools + " 个工具"; color: bedrock.themeData.text_secondary; font.pixelSize: 10 } Text { text: error; visible: error.length > 0; color: bedrock.themeData.danger; font.pixelSize: 10 } }
                Text { text: status; color: server_enabled ? bedrock.themeData.accent : bedrock.themeData.text_secondary; font.pixelSize: 11 }
            }
        }
        Text { anchors.centerIn: parent; visible: parent.count === 0; text: "尚未导入 MCP 服务器配置"; color: bedrock.themeData.text_muted }
    }
}
