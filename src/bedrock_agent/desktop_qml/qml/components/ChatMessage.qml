import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property string role: "assistant"
    property string title: "Bedrock"
    property string messageText: ""
    property string payload: ""
    property string accent: "green"
    property bool expanded: false

    readonly property color accentColor: accent === "blue" ? "#4e91dc" : accent === "amber" ? bedrock.themeData.warning : accent === "red" ? bedrock.themeData.danger : accent === "muted" ? bedrock.themeData.text_muted : bedrock.themeData.accent
    readonly property color bubbleColor: role === "user" ? bedrock.themeData.user_bubble : role === "assistant" ? bedrock.themeData.assistant_bubble : role === "tool_request" ? bedrock.themeData.tool_bubble : bedrock.themeData.surface_alt
    readonly property string visibleText: messageText && messageText.trim().length > 0
            ? messageText
            : "（这条消息没有可显示的文本）"

    implicitHeight: messageLayout.implicitHeight + 10

    ColumnLayout {
        id: messageLayout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: root.role === "user" ? (bedrock.currentTheme === "wechat" ? 130 : 90) : 0
        anchors.rightMargin: root.role === "user" ? 0 : (bedrock.currentTheme === "wechat" ? 120 : 40)
        spacing: 6

        Text {
            text: root.title
            color: root.accentColor
            font.pixelSize: 11
            font.weight: Font.DemiBold
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: contentLayout.implicitHeight + 24
            radius: Math.max(7, Number(bedrock.themeData.corner || 12) - 7)
            color: root.bubbleColor
            border.width: bedrock.currentTheme === "wechat" && root.role === "user" ? 0 : 1
            border.color: bedrock.themeData.border

            ColumnLayout {
                id: contentLayout
                anchors.fill: parent
                anchors.margins: 12
                spacing: 9

                Text {
                    Layout.fillWidth: true
                    text: root.visibleText
                    color: root.messageText && root.messageText.trim().length > 0 ? bedrock.themeData.text_primary : bedrock.themeData.text_muted
                    font.pixelSize: 13
                    wrapMode: Text.Wrap
                    textFormat: Text.PlainText
                }

                Text {
                    Layout.fillWidth: true
                    visible: root.expanded && root.payload.length > root.messageText.length
                    text: root.payload
                    color: bedrock.themeData.text_secondary
                    font.family: "Consolas"
                    font.pixelSize: 11
                    wrapMode: Text.WrapAnywhere
                }

                Text {
                    visible: root.payload.length > root.messageText.length
                    text: root.expanded ? "收起完整参数" : "点击查看完整参数"
                    color: bedrock.themeData.text_muted
                    font.pixelSize: 9
                }
            }

            MouseArea {
                anchors.fill: parent
                enabled: root.payload.length > root.messageText.length
                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: root.expanded = !root.expanded
            }
        }
    }
}
