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
    ColumnLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 56; color: bedrock.themeData.surface; border.width: 0
            HeaderBar { anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14; vm: root.vm; subtitle: "聊天优先 · 熟悉直接"; onHelpRequested: root.helpRequested(); onThemeRequested: root.themeRequested() }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: bedrock.themeData.border }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
            NavigationRail { Layout.preferredWidth: 64; Layout.fillHeight: true; vm: root.vm; compact: true; showUser: false }
            SessionsRail { Layout.preferredWidth: 286; Layout.fillHeight: true; vm: root.vm }
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; color: bedrock.themeData.surface_alt
                PageHost { anchors.fill: parent; anchors.margins: 20; vm: root.vm }
            }
        }
    }
}
