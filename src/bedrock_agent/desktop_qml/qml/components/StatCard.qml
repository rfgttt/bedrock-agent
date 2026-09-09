import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

GlassCard {
    id: root
    property string label: "状态"
    property string value: "0"
    property string detail: ""
    property string symbol: "◈"
    property color accent: bedrock.themeData.accent
    implicitHeight: 118

    RowLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5
            Text { text: root.label; color: bedrock.themeData.text_secondary; font.pixelSize: 12 }
            Text { text: root.value; color: bedrock.themeData.text_primary; font.pixelSize: 29; font.weight: Font.DemiBold }
            Text { text: root.detail; color: root.accent; font.pixelSize: 11 }
        }
        Rectangle {
            width: 44; height: 44; radius: Math.max(10, Number(bedrock.themeData.corner || 14) - 5)
            color: bedrock.themeData.accent_soft
            border.width: 1; border.color: bedrock.themeData.border_strong
            Text { anchors.centerIn: parent; text: root.symbol; color: root.accent; font.pixelSize: 21 }
        }
    }
}
