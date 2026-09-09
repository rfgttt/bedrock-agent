import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

GlassCard {
    id: root
    property var vm
    implicitWidth: 286

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            Rectangle { width: 44; height: 44; radius: 15; color: bedrock.themeData.accent_soft; border.width: 1; border.color: bedrock.themeData.border_strong; Text { anchors.centerIn: parent; text: "AI"; color: bedrock.themeData.accent; font.pixelSize: 15; font.weight: Font.Bold } }
            ColumnLayout { Layout.fillWidth: true; Text { text: bedrock.currentTheme === "codex" ? "Agent status" : "智能伴随"; color: bedrock.themeData.text_primary; font.pixelSize: 15; font.weight: Font.DemiBold } Text { text: root.vm.agentPanel.state || "待命"; color: root.vm.agentPanel.state === "失败" ? bedrock.themeData.danger : bedrock.themeData.success; font.pixelSize: 10 } }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: bedrock.themeData.border }
        ColumnLayout { Layout.fillWidth: true; spacing: 8
            Text { text: "当前步骤"; color: bedrock.themeData.text_muted; font.pixelSize: 9; font.letterSpacing: 1 }
            Text { Layout.fillWidth: true; text: root.vm.agentPanel.step || "等待你的指令"; color: bedrock.themeData.text_primary; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 6; elide: Text.ElideRight }
        }
        GlassCard {
            Layout.fillWidth: true; implicitHeight: 96; highlighted: root.vm.agentPanel.state === "等待审批"
            ColumnLayout { anchors.fill: parent; anchors.margins: 13; spacing: 6
                Text { text: "正在使用"; color: bedrock.themeData.text_muted; font.pixelSize: 9 }
                Text { text: root.vm.agentPanel.tool || "—"; color: bedrock.themeData.text_primary; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                RowLayout { Layout.fillWidth: true; Text { text: "风险"; color: bedrock.themeData.text_muted; font.pixelSize: 9 } Item { Layout.fillWidth: true } Text { text: root.vm.agentPanel.risk || "安全"; color: (root.vm.agentPanel.risk === "错误" || root.vm.agentPanel.risk === "需要确认") ? bedrock.themeData.warning : bedrock.themeData.success; font.pixelSize: 10 } }
            }
        }
        GlassCard {
            Layout.fillWidth: true; implicitHeight: 116
            ColumnLayout { anchors.fill: parent; anchors.margins: 13; spacing: 8
                Text { text: "安全边界"; color: bedrock.themeData.text_primary; font.pixelSize: 13; font.weight: Font.DemiBold }
                Text { text: "● 本机进程内\n● 工作区隔离\n● 外部操作需审批"; color: bedrock.themeData.text_secondary; font.pixelSize: 10; lineHeight: 1.45 }
            }
        }
        Item { Layout.fillHeight: true }
        ActionButton { Layout.fillWidth: true; text: root.vm.dashboard.approvals > 0 ? "处理 " + root.vm.dashboard.approvals + " 个审批" : "打开审批中心"; primary: root.vm.dashboard.approvals > 0; onClicked: root.vm.openPage("approvals") }
        Text { Layout.fillWidth: true; text: "Trace · " + (root.vm.agentPanel.trace || "—"); color: bedrock.themeData.text_muted; font.pixelSize: 8; elide: Text.ElideMiddle }
    }
}
