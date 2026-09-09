import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    property var vm
    spacing: 14
    SectionTitle { Layout.fillWidth: true; title: "运行轨迹"; subtitle: "最近一次任务的模型、工具与错误事件"; actionText: "刷新"; onAction: vm.refreshTraces() }
    GlassCard {
        Layout.fillWidth: true; Layout.fillHeight: true
        ListView {
            anchors.fill: parent; anchors.margins: 12; model: vm.tracesModel; spacing: 2; clip: true; reuseItems: true
            delegate: Rectangle {
                required property string title
                required property string detail
                required property string time
                required property string level
                width: ListView.view.width; implicitHeight: detailText.implicitHeight + 34; radius: 8; color: level === "error" ? bedrock.themeData.surface_alt : (index % 2 ? bedrock.themeData.surface_strong : "transparent")
                RowLayout { anchors.fill: parent; anchors.margins: 10; spacing: 10
                    Text { text: time || "·"; color: bedrock.themeData.text_muted; font.pixelSize: 9; Layout.preferredWidth: 64 }
                    Text { text: title; color: level === "error" ? bedrock.themeData.danger : bedrock.themeData.accent; font.pixelSize: 11; font.weight: Font.DemiBold; Layout.preferredWidth: 150 }
                    Text { id: detailText; Layout.fillWidth: true; text: detail; color: bedrock.themeData.text_secondary; font.family: "Consolas"; font.pixelSize: 10; wrapMode: Text.WrapAnywhere }
                }
            }
        }
    }
}
