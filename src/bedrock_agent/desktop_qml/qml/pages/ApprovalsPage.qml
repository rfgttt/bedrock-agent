import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    id: root
    property var vm
    spacing: 14
    SectionTitle { Layout.fillWidth: true; title: "审批中心"; subtitle: "所有写入、外部应用和 MCP 调用都必须由你决定"; actionText: "刷新"; onAction: vm.refreshApprovals() }
    ListView {
        Layout.fillWidth: true; Layout.fillHeight: true
        model: vm.approvalsModel
        spacing: 12; clip: true; reuseItems: true
        delegate: GlassCard {
            required property string approval_id
            required property string session_id
            required property string tool
            required property string reason
            required property string arguments
            required property string risk
            width: ListView.view.width
            implicitHeight: approvalBody.implicitHeight + 34
            highlighted: true
            ColumnLayout {
                id: approvalBody
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 17
                spacing: 10
                RowLayout { Layout.fillWidth: true; Text { text: tool; color: bedrock.themeData.accent; font.pixelSize: 17; font.weight: Font.DemiBold; Layout.fillWidth: true } Text { text: risk; color: bedrock.themeData.warning; font.pixelSize: 11 } }
                Text { Layout.fillWidth: true; text: reason; color: bedrock.themeData.text_primary; font.pixelSize: 12; wrapMode: Text.Wrap }
                TextArea { Layout.fillWidth: true; implicitHeight: Math.min(160, contentHeight + 20); text: arguments; readOnly: true; color: bedrock.themeData.text_secondary; font.family: "Consolas"; font.pixelSize: 11; wrapMode: TextArea.WrapAnywhere; background: Rectangle { radius: 10; color: bedrock.themeData.surface_strong; border.width: 1; border.color: bedrock.themeData.border } }
                RowLayout { Layout.fillWidth: true; ActionButton { text: "打开会话"; enabled: !vm.busy; onClicked: vm.selectSession(session_id) } Item { Layout.fillWidth: true } ActionButton { text: "拒绝"; danger: true; enabled: !vm.busy; onClicked: vm.resolveApproval(approval_id, false) } ActionButton { text: "允许执行"; primary: true; enabled: !vm.busy; onClicked: vm.resolveApproval(approval_id, true) } }
            }
        }
        Text { anchors.centerIn: parent; visible: parent.count === 0; text: "当前没有等待审批的任务"; color: bedrock.themeData.text_muted; font.pixelSize: 14 }
    }
}
