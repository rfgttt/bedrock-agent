import QtQuick
import QtQuick.Controls

Button {
    id: root
    property bool primary: false
    property bool danger: false

    implicitHeight: 38
    leftPadding: 16
    rightPadding: 16
    hoverEnabled: true
    opacity: root.enabled ? (root.down ? 0.78 : 1.0) : 0.44

    contentItem: Text {
        text: root.text
        color: root.danger
               ? (bedrock.themeData.dark ? "#ffd8dc" : bedrock.themeData.danger)
               : (root.primary ? bedrock.themeData.accent_text : bedrock.themeData.text_primary)
        font.pixelSize: 12
        font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: Math.max(7, Number(bedrock.themeData.corner || 12) - 6)
        color: root.danger
               ? (root.hovered ? Qt.lighter(bedrock.themeData.danger, 1.08) : bedrock.themeData.danger)
               : (root.primary ? bedrock.themeData.accent : "transparent")
        border.width: root.primary ? 0 : 1
        border.color: root.danger
                      ? bedrock.themeData.danger
                      : (root.hovered ? bedrock.themeData.accent : bedrock.themeData.border)
    }
}
