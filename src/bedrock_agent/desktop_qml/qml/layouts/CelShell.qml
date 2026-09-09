import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    property var vm
    signal helpRequested()
    signal themeRequested()

    Rectangle { anchors.fill: parent; color: bedrock.themeData.bg }
    Rectangle { width: 520; height: 520; radius: 260; color: "#dcecff"; opacity: 0.82; anchors.right: parent.right; anchors.top: parent.top; anchors.rightMargin: -180; anchors.topMargin: -250 }
    Rectangle { width: 400; height: 300; radius: 150; color: "#fff0e9"; opacity: 0.75; anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.leftMargin: -170; anchors.bottomMargin: -150 }
    Text { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.rightMargin: 36; anchors.bottomMargin: 22; text: "✦"; color: "#b8d8f5"; font.pixelSize: 160; opacity: 0.28 }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 14; spacing: 12
        HeaderBar { Layout.fillWidth: true; Layout.preferredHeight: 48; vm: root.vm; subtitle: "CEL-SHADED · CALM COMPANION"; onHelpRequested: root.helpRequested(); onThemeRequested: root.themeRequested() }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            NavigationRail { Layout.preferredWidth: 202; Layout.fillHeight: true; vm: root.vm }
            GlassCard { Layout.fillWidth: true; Layout.fillHeight: true; corner: 22; PageHost { anchors.fill: parent; anchors.margins: 20; vm: root.vm } }
            GlassCard {
                Layout.preferredWidth: 238; Layout.fillHeight: true; corner: 22
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 12
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 180; radius: 24; color: "#e5f3ff"; border.width: 1; border.color: "#bcd6ed"
                        Text { anchors.centerIn: parent; text: "B"; color: "#6aaee6"; font.pixelSize: 72; font.weight: Font.Black }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 20; text: "今天也一起完成任务吧"; color: bedrock.themeData.text_secondary; font.pixelSize: 11 }
                    }
                    Text { text: "当前任务"; color: bedrock.themeData.text_primary; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Text { Layout.fillWidth: true; text: root.vm.agentPanel.step || "等待你的指令"; color: bedrock.themeData.text_secondary; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 8 }
                    GlassCard { Layout.fillWidth: true; implicitHeight: 86; highlighted: root.vm.agentPanel.state === "等待审批"; ColumnLayout { anchors.fill: parent; anchors.margins: 12; Text { text: root.vm.agentPanel.state; color: bedrock.themeData.accent; font.pixelSize: 12 } Text { text: root.vm.agentPanel.tool || "暂无工具"; color: bedrock.themeData.text_primary; font.pixelSize: 13; elide: Text.ElideRight; Layout.fillWidth: true } } }
                    Item { Layout.fillHeight: true }
                    ActionButton { Layout.fillWidth: true; text: "打开审批中心"; primary: root.vm.dashboard.approvals > 0; onClicked: root.vm.openPage("approvals") }
                }
            }
        }
    }
}
