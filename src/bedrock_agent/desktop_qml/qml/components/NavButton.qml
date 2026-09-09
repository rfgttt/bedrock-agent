import QtQuick
import QtQuick.Controls

Button {
    id: root
    property string iconText: "◈"
    property bool selected: false
    property bool compact: false

    implicitHeight: compact ? 40 : 44
    padding: 0
    flat: true

    background: Rectangle {
        radius: Math.max(7, Number(bedrock.themeData.corner || 12) - 5)
        color: root.selected ? bedrock.themeData.accent_soft : (root.hovered ? bedrock.themeData.surface_alt : "transparent")
        border.width: root.selected ? 1 : 0
        border.color: root.selected ? bedrock.themeData.border_strong : "transparent"
        Rectangle {
            width: 3
            height: 22
            radius: 2
            anchors.left: parent.left
            anchors.leftMargin: 1
            anchors.verticalCenter: parent.verticalCenter
            color: bedrock.themeData.accent
            visible: root.selected && !root.compact
        }
    }

    contentItem: Row {
        spacing: root.compact ? 0 : 11
        leftPadding: root.compact ? 0 : 13
        Text {
            width: root.compact ? root.width : 22
            anchors.verticalCenter: parent.verticalCenter
            text: root.iconText
            color: root.selected ? bedrock.themeData.accent : bedrock.themeData.text_muted
            font.pixelSize: root.compact ? 15 : 16
            horizontalAlignment: Text.AlignHCenter
        }
        Text {
            visible: !root.compact
            anchors.verticalCenter: parent.verticalCenter
            text: root.text
            color: root.selected ? bedrock.themeData.text_primary : bedrock.themeData.text_secondary
            font.pixelSize: 13
            font.weight: root.selected ? Font.DemiBold : Font.Normal
        }
    }
    ToolTip.visible: root.compact && root.hovered
    ToolTip.text: root.text
}
