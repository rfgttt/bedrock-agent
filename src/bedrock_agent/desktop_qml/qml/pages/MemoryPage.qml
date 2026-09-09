import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    property var vm
    spacing: 14
    SectionTitle { Layout.fillWidth: true; title: "长期记忆"; subtitle: "你批准保存的偏好、经验与知识"; actionText: "刷新"; onAction: vm.refreshMemories() }
    ListView {
        Layout.fillWidth: true; Layout.fillHeight: true; model: vm.memoriesModel; spacing: 9; clip: true; reuseItems: true
        delegate: GlassCard {
            required property string kind
            required property string content
            required property string tags
            required property int importance
            required property string created_at
            width: ListView.view.width; implicitHeight: body.implicitHeight + 28
            RowLayout { id: body; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14; spacing: 12
                Rectangle { width: 42; height: 42; radius: 14; color: bedrock.themeData.accent_soft; Text { anchors.centerIn: parent; text: String(importance); color: bedrock.themeData.accent; font.pixelSize: 16 } }
                ColumnLayout { Layout.fillWidth: true; Text { text: kind + (tags ? " · " + tags : ""); color: bedrock.themeData.text_secondary; font.pixelSize: 10 } Text { Layout.fillWidth: true; text: content; color: bedrock.themeData.text_primary; font.pixelSize: 12; wrapMode: Text.Wrap } Text { text: created_at; color: bedrock.themeData.text_muted; font.pixelSize: 9 } }
            }
        }
    }
}
