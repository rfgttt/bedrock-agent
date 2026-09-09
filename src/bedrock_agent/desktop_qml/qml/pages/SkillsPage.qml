import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    property var vm
    spacing: 14
    SectionTitle { Layout.fillWidth: true; title: "Skills"; subtitle: "把已有工具组合成可复用工作流"; actionText: "刷新"; onAction: vm.refreshSkills() }
    GridView {
        Layout.fillWidth: true; Layout.fillHeight: true; cellWidth: 340; cellHeight: 170; model: vm.skillsModel; clip: true
        delegate: GlassCard {
            required property string name
            required property string description
            required property string risk
            required property string status
            required property int steps
            width: 326; height: 154; highlighted: status === "active"
            ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 8
                RowLayout { Layout.fillWidth: true; Text { text: name; color: bedrock.themeData.text_primary; font.pixelSize: 16; font.weight: Font.DemiBold; Layout.fillWidth: true; elide: Text.ElideRight } Text { text: risk; color: risk === "high" ? bedrock.themeData.danger : bedrock.themeData.warning; font.pixelSize: 10 } }
                Text { Layout.fillWidth: true; Layout.fillHeight: true; text: description; color: bedrock.themeData.text_secondary; font.pixelSize: 11; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight }
                Text { text: steps + " 个步骤 · " + status; color: bedrock.themeData.accent; font.pixelSize: 10 }
            }
        }
        Text { anchors.centerIn: parent; visible: parent.count === 0; text: "还没有安装 Skill · 在帮助中心尝试“学习组合 Skill”"; color: bedrock.themeData.text_muted }
    }
}
