import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Flickable {
    id: root
    property var vm
    contentWidth: width
    contentHeight: content.implicitHeight + 40
    clip: true
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

    ColumnLayout {
        id: content
        width: root.width
        spacing: 18
        SectionTitle {
            Layout.fillWidth: true
            title: "任务总览"
            subtitle: "任务、审批、学习与能力状态集中展示"
            actionText: "刷新"
            onAction: vm.refreshDashboard()
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width > 980 ? 4 : 2
            rowSpacing: 12; columnSpacing: 12
            StatCard { Layout.fillWidth: true; label: "会话"; value: String(vm.dashboard.sessions || 0); detail: "最近任务上下文"; symbol: "▣" }
            StatCard { Layout.fillWidth: true; label: "待审批"; value: String(vm.dashboard.approvals || 0); detail: vm.dashboard.approvals > 0 ? "需要你的决定" : "暂无阻塞"; symbol: "◇"; accent: vm.dashboard.approvals > 0 ? bedrock.themeData.warning : bedrock.themeData.accent }
            StatCard { Layout.fillWidth: true; label: "已装技能"; value: String(vm.dashboard.skills || 0); detail: "可复用工作流"; symbol: "✦" }
            StatCard { Layout.fillWidth: true; label: "可用应用"; value: String(vm.dashboard.apps || 0); detail: "受控白名单"; symbol: "◉" }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 420
            spacing: 14

            GlassCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 640
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12
                    SectionTitle { Layout.fillWidth: true; title: "任务棱镜"; subtitle: "拖动、滚轮或方向键切换 3D 任务卡" }
                    TaskPrism {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        taskModel: vm.tasksModel
                        onOpenSession: function(sessionId) { vm.selectSession(sessionId) }
                    }
                }
            }

            ColumnLayout {
                Layout.preferredWidth: 310
                Layout.fillHeight: true
                spacing: 14
                GlassCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 18; spacing: 12
                        SectionTitle { Layout.fillWidth: true; title: "学习进度"; subtitle: "最近 30 天" }
                        Text { text: String(vm.dashboard.learningMinutes || 0); color: bedrock.themeData.text_primary; font.pixelSize: 42; font.weight: Font.DemiBold }
                        Text { text: "分钟累计学习"; color: bedrock.themeData.text_secondary; font.pixelSize: 12 }
                        Rectangle { Layout.fillWidth: true; height: 8; radius: 4; color: bedrock.themeData.surface_alt; Rectangle { width: Math.min(parent.width, parent.width * ((vm.dashboard.learningMinutes || 0) / 900)); height: parent.height; radius: 4; color: bedrock.themeData.accent } }
                        Item { Layout.fillHeight: true }
                        ActionButton { Layout.fillWidth: true; text: "打开学习管理"; onClicked: vm.openPage("learning") }
                    }
                }
                GlassCard {
                    Layout.fillWidth: true
                    implicitHeight: 124
                    highlighted: vm.dashboard.approvals > 0
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 18
                        ColumnLayout { Layout.fillWidth: true; Text { text: "审批队列"; color: bedrock.themeData.text_secondary; font.pixelSize: 11 } Text { text: String(vm.dashboard.approvals || 0); color: bedrock.themeData.text_primary; font.pixelSize: 30 } }
                        ActionButton { text: "查看"; primary: vm.dashboard.approvals > 0; onClicked: vm.openPage("approvals") }
                    }
                }
            }
        }
    }
}
