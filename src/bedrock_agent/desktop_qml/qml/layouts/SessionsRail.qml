import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

GlassCard {
    id: root
    property var vm
    property bool showNav: false
    implicitWidth: 276
    corner: bedrock.currentTheme === "wechat" ? 0 : Number(bedrock.themeData.corner || 14)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Text { text: "会话"; color: bedrock.themeData.text_primary; font.pixelSize: 16; font.weight: Font.DemiBold; Layout.fillWidth: true }
            ActionButton { text: "+ 新建"; primary: true; onClicked: root.vm.newSession() }
        }
        TextField {
            Layout.fillWidth: true
            placeholderText: "搜索会话（预留）"
            color: bedrock.themeData.text_primary
            placeholderTextColor: bedrock.themeData.text_muted
            background: Rectangle { radius: 8; color: bedrock.themeData.input_bg; border.width: 1; border.color: bedrock.themeData.border }
        }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true
            model: root.vm.sessionsModel
            clip: true; spacing: 5; reuseItems: true; cacheBuffer: 500
            delegate: Rectangle {
                required property string session_id
                required property string title
                required property string updated_at
                required property int message_count
                width: ListView.view.width
                height: 64
                radius: Math.max(6, Number(bedrock.themeData.corner || 10) - 6)
                color: session_id === root.vm.currentSession ? bedrock.themeData.accent_soft : (hover.hovered ? bedrock.themeData.surface_alt : "transparent")
                border.width: session_id === root.vm.currentSession ? 1 : 0
                border.color: bedrock.themeData.border_strong
                HoverHandler { id: hover }
                TapHandler { onTapped: root.vm.selectSession(session_id) }
                Column {
                    anchors.left: parent.left; anchors.right: deleteButton.left; anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: 11; anchors.rightMargin: 8; spacing: 4
                    Text { width: parent.width; text: title || "新会话"; color: bedrock.themeData.text_primary; font.pixelSize: 12; elide: Text.ElideRight }
                    Text { width: parent.width; text: message_count + " 条消息 · " + (updated_at || ""); color: bedrock.themeData.text_muted; font.pixelSize: 9; elide: Text.ElideRight }
                }
                Button {
                    id: deleteButton
                    anchors.right: parent.right; anchors.rightMargin: 7; anchors.verticalCenter: parent.verticalCenter
                    width: 30; height: 30; flat: true; text: "×"
                    visible: hover.hovered || session_id === root.vm.currentSession
                    contentItem: Text { text: deleteButton.text; color: deleteButton.hovered ? bedrock.themeData.danger : bedrock.themeData.text_muted; font.pixelSize: 18; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    background: Rectangle { radius: 7; color: deleteButton.hovered ? bedrock.themeData.surface_alt : "transparent" }
                    onClicked: root.vm.requestDeleteSession(session_id, title)
                    ToolTip.visible: hovered; ToolTip.text: "删除会话"
                }
            }
            Text { anchors.centerIn: parent; visible: parent.count === 0; text: "还没有保存的会话"; color: bedrock.themeData.text_muted; font.pixelSize: 11 }
        }
    }
}
