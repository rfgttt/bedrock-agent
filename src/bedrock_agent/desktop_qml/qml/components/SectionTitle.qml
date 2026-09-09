import QtQuick
import QtQuick.Layouts

RowLayout {
    id: root
    property string title: "标题"
    property string subtitle: ""
    property string actionText: ""
    signal action()
    spacing: 12

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 3
        Text { text: root.title; color: bedrock.themeData.text_primary; font.pixelSize: 20; font.weight: Font.DemiBold }
        Text { text: root.subtitle; color: bedrock.themeData.text_secondary; font.pixelSize: 11; visible: text.length > 0 }
    }

    ActionButton {
        visible: root.actionText.length > 0
        text: root.actionText
        onClicked: root.action()
    }
}
