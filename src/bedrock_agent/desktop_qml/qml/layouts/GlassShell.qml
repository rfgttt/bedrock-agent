import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root
    property var vm
    signal helpRequested()
    signal themeRequested()

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#05141c" }
            GradientStop { position: 0.42; color: bedrock.themeData.bg }
            GradientStop { position: 1.0; color: "#09051b" }
        }
    }
    Rectangle { width: parent.width * 0.7; height: parent.height * 0.35; radius: height / 2; anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; anchors.topMargin: -height * 0.45; color: "#123d56"; opacity: 0.38; rotation: -8 }
    Rectangle { width: parent.width * 0.45; height: parent.height * 0.55; radius: width / 2; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.rightMargin: -width * 0.45; anchors.bottomMargin: -height * 0.25; color: "#2a1450"; opacity: 0.32 }
    Canvas {
        anchors.fill: parent; opacity: 0.10
        onPaint: {
            var ctx = getContext("2d"); ctx.reset(); ctx.strokeStyle = bedrock.themeData.accent; ctx.lineWidth = 0.55
            for (var x=0; x<width; x+=52) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,height); ctx.stroke() }
            for (var y=0; y<height; y+=52) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(width,y); ctx.stroke() }
        }
        onWidthChanged: requestPaint(); onHeightChanged: requestPaint()
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 14; spacing: 12
        HeaderBar { Layout.fillWidth: true; Layout.preferredHeight: 48; vm: root.vm; subtitle: "GLASS WORKSPACE · LOCAL AGENT"; onHelpRequested: root.helpRequested(); onThemeRequested: root.themeRequested() }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            NavigationRail { Layout.preferredWidth: 214; Layout.fillHeight: true; vm: root.vm }
            GlassCard { Layout.fillWidth: true; Layout.fillHeight: true; corner: 22; PageHost { anchors.fill: parent; anchors.margins: 18; vm: root.vm } }
            AgentRail { Layout.preferredWidth: 286; Layout.fillHeight: true; vm: root.vm }
        }
    }
}
