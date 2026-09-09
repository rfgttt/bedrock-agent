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
        anchors.fill: parent; anchors.margins: 10; spacing: 8
        HeaderBar { Layout.fillWidth: true; Layout.preferredHeight: 44; vm: root.vm; subtitle: "AGENT WORKBENCH · TOOLS · CONTEXT"; onHelpRequested: root.helpRequested(); onThemeRequested: root.themeRequested() }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
            ColumnLayout {
                Layout.preferredWidth: 266; Layout.fillHeight: true; spacing: 8
                NavigationRail { Layout.fillWidth: true; Layout.preferredHeight: 330; vm: root.vm; compact: false; showUser: false }
                SessionsRail { Layout.fillWidth: true; Layout.fillHeight: true; vm: root.vm }
            }
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 8; color: bedrock.themeData.surface_strong; border.width: 1; border.color: bedrock.themeData.border
                PageHost { anchors.fill: parent; anchors.margins: 18; vm: root.vm }
            }
            AgentRail { Layout.preferredWidth: 270; Layout.fillHeight: true; vm: root.vm }
        }
    }
}
