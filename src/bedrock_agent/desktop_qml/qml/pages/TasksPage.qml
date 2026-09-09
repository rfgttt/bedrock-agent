import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    property var vm
    spacing: 14
    SectionTitle { Layout.fillWidth: true; title: "任务管理"; subtitle: "最近会话、执行状态与任务上下文"; actionText: "刷新"; onAction: vm.refreshDashboard() }
    ListView {
        Layout.fillWidth: true; Layout.fillHeight: true; model: vm.tasksModel; spacing: 10; clip: true; reuseItems: true
        delegate: GlassCard {
            required property string title
            required property string subtitle
            required property string state
            required property int progress
            required property string session_id
            width: ListView.view.width; height: 102; highlighted: state === "等待审批"
            RowLayout { anchors.fill: parent; anchors.margins: 16; spacing: 14
                Rectangle { width: 44; height: 44; radius: 14; color: bedrock.themeData.accent_soft; Text { anchors.centerIn: parent; text: state === "等待审批" ? "!" : "✓"; color: state === "等待审批" ? bedrock.themeData.warning : bedrock.themeData.accent; font.pixelSize: 18 } }
                ColumnLayout { Layout.fillWidth: true; Text { text: title; color: bedrock.themeData.text_primary; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true } Text { text: subtitle + " · " + state; color: bedrock.themeData.text_secondary; font.pixelSize: 10 } Rectangle { Layout.fillWidth: true; height: 4; radius: 2; color: bedrock.themeData.surface_alt; Rectangle { width: parent.width * progress / 100; height: parent.height; radius: 2; color: bedrock.themeData.accent } } }
                ActionButton { text: "打开"; onClicked: vm.selectSession(session_id) }
            }
        }
    }
}
