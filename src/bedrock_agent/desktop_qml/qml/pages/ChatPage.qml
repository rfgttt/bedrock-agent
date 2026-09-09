import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    id: root
    property var vm
    spacing: 12

    RowLayout {
        Layout.fillWidth: true
        ColumnLayout { Layout.fillWidth: true; spacing: 3; Text { text: bedrock.currentTheme === "wechat" ? "聊天" : "Agent 对话"; color: bedrock.themeData.text_primary; font.pixelSize: 20; font.weight: Font.DemiBold } Text { text: "Ctrl + Enter 发送 · 工具参数默认折叠"; color: bedrock.themeData.text_secondary; font.pixelSize: 11 } }
        ActionButton { text: "删除当前会话"; danger: true; enabled: !vm.busy; onClicked: vm.requestDeleteSession(vm.currentSession, "当前会话") }
        ActionButton { text: "新会话"; primary: true; enabled: !vm.busy; onClicked: vm.newSession() }
    }

    GlassCard {
        Layout.fillWidth: true
        Layout.fillHeight: true
        ListView {
            id: chatList
            anchors.fill: parent
            anchors.margins: 14
            clip: true
            spacing: bedrock.currentTheme === "wechat" ? 10 : 6
            model: vm.messagesModel
            cacheBuffer: 800
            reuseItems: true
            delegate: ChatMessage {
                required property string role
                required property string title
                required property string message_text
                required property string payload
                required property string accent
                messageText: message_text
                width: chatList.width
            }
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            Connections { target: vm; function onRequestScrollToEnd() { Qt.callLater(function() { chatList.positionViewAtEnd() }) } }
            Text { anchors.centerIn: parent; visible: chatList.count === 0; text: "输入一个目标，Bedrock 会规划、调用工具并等待你的审批"; color: bedrock.themeData.text_muted; font.pixelSize: 13 }
        }
    }

    GlassCard {
        Layout.fillWidth: true
        implicitHeight: bedrock.currentTheme === "wechat" ? 146 : 132
        RowLayout {
            anchors.fill: parent; anchors.margins: 14; spacing: 12
            TextArea {
                id: editor
                Layout.fillWidth: true; Layout.fillHeight: true
                text: vm.draftText
                onTextChanged: if (activeFocus) vm.draftText = text
                placeholderText: "例如：打开 VS Code，或者检查 workspace 中的 Python 项目…"
                wrapMode: TextArea.Wrap
                color: bedrock.themeData.text_primary; placeholderTextColor: bedrock.themeData.text_muted
                background: Rectangle { radius: Math.max(7, Number(bedrock.themeData.corner || 12) - 5); color: bedrock.themeData.input_bg; border.width: 1; border.color: editor.activeFocus ? bedrock.themeData.accent : bedrock.themeData.border }
                Keys.onPressed: function(event) {
                    if ((event.modifiers & Qt.ControlModifier) && (event.key === Qt.Key_Return || event.key === Qt.Key_Enter)) {
                        vm.sendMessage(editor.text); event.accepted = true
                    }
                }
            }
            ColumnLayout {
                Layout.preferredWidth: 126
                ActionButton { Layout.fillWidth: true; text: vm.busy ? "运行中…" : "发送"; primary: true; enabled: !vm.busy && editor.text.trim().length > 0; onClicked: vm.sendMessage(editor.text) }
                Text { text: "Ctrl + Enter"; color: bedrock.themeData.text_muted; font.pixelSize: 10; Layout.alignment: Qt.AlignHCenter }
                Item { Layout.fillHeight: true }
            }
        }
    }
}
