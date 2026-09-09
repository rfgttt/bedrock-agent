import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    property color surface: bedrock.themeData.surface
    property color edge: bedrock.themeData.border
    property real corner: Number(bedrock.themeData.corner || 14)
    property bool highlighted: false
    property bool hoverable: false
    property bool glassy: bedrock.currentTheme === "glass"
    signal clicked()

    radius: corner
    color: surface
    border.width: highlighted ? 1.5 : 1
    border.color: highlighted ? bedrock.themeData.accent : edge
    opacity: enabled ? Number(bedrock.themeData.panel_opacity || 1.0) : 0.55

    gradient: Gradient {
        GradientStop { position: 0.0; color: root.highlighted ? bedrock.themeData.accent_soft : bedrock.themeData.surface_alt }
        GradientStop { position: 0.55; color: root.surface }
        GradientStop { position: 1.0; color: bedrock.themeData.surface_strong }
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, root.radius - 1)
        color: "transparent"
        border.width: root.glassy ? 1 : 0
        border.color: root.highlighted ? bedrock.themeData.border_strong : bedrock.themeData.border
        opacity: root.glassy ? 0.55 : 0
    }

    Rectangle {
        width: parent.width * 0.48
        height: 1
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        color: root.highlighted ? bedrock.themeData.accent : bedrock.themeData.border_strong
        opacity: root.glassy ? 0.42 : 0.12
    }

    HoverHandler {
        enabled: root.hoverable
        cursorShape: Qt.PointingHandCursor
        onHoveredChanged: root.scale = hovered ? 1.006 : 1.0
    }

    Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
}
