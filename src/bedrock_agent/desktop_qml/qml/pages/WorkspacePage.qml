import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    id: root
    property var vm
    spacing: 14
    SectionTitle { Layout.fillWidth: true; title: "工作区"; subtitle: vm.workspacePath; actionText: "刷新"; onAction: vm.refreshWorkspace() }
    RowLayout {
        Layout.fillWidth: true
        ActionButton { text: "打开工作区"; primary: true; onClicked: vm.openWorkspace() }
        ActionButton { text: "导入文件"; onClicked: vm.importFiles() }
        ActionButton { text: "导入文件夹"; onClicked: vm.importFolder() }
        Item { Layout.fillWidth: true }
        Text { text: "最多显示 500 项"; color: bedrock.themeData.text_muted; font.pixelSize: 10 }
    }
    GlassCard {
        Layout.fillWidth: true; Layout.fillHeight: true
        ListView {
            anchors.fill: parent; anchors.margins: 10; model: vm.workspaceModel; clip: true; spacing: 2; reuseItems: true
            delegate: Rectangle {
                required property string name
                required property string path
                required property string kind
                required property string size
                width: ListView.view.width; height: 42; radius: 8
                color: mouse.containsMouse ? bedrock.themeData.surface_alt : "transparent"
                RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; Text { text: kind === "文件夹" ? "▣" : "·"; color: kind === "文件夹" ? bedrock.themeData.accent : bedrock.themeData.text_muted; font.pixelSize: 15 } Text { text: path; color: bedrock.themeData.text_primary; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideMiddle } Text { text: size; color: bedrock.themeData.text_muted; font.pixelSize: 10 } }
                MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true }
            }
            Text { anchors.centerIn: parent; visible: parent.count === 0; text: "工作区为空 · 点击“导入文件夹”导入项目"; color: bedrock.themeData.text_muted }
        }
    }
}
