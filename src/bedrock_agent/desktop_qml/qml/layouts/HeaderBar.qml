import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

RowLayout {
    id: root
    property var vm
    property string subtitle: "LOCAL · PERMISSION AWARE · DEEPSEEK"
    signal helpRequested()
    signal themeRequested()
    spacing: 14

    Rectangle {
        Layout.preferredWidth: 40; Layout.preferredHeight: 40
        radius: bedrock.currentTheme === "wechat" ? 6 : 13
        color: bedrock.themeData.accent
        Text { anchors.centerIn: parent; text: "B"; color: bedrock.themeData.accent_text; font.pixelSize: 20; font.weight: Font.Black }
    }
    ColumnLayout {
        spacing: 0
        Text { text: "BEDROCK AGENT"; color: bedrock.themeData.text_primary; font.pixelSize: 17; font.weight: Font.Bold; font.letterSpacing: bedrock.currentTheme === "codex" ? 0.2 : 1.2 }
        Text { text: root.subtitle; color: bedrock.themeData.text_muted; font.pixelSize: 8; font.letterSpacing: 1.3 }
    }
    Item { Layout.fillWidth: true }
    Rectangle { width: 8; height: 8; radius: 4; color: root.vm.busy ? bedrock.themeData.warning : bedrock.themeData.success }
    Text { text: root.vm.statusText; color: root.vm.busy ? bedrock.themeData.warning : bedrock.themeData.success; font.pixelSize: 11 }
    ActionButton { text: "主题 · " + bedrock.themeData.label; onClicked: root.themeRequested() }
    ActionButton { text: "？ 帮助与技能"; primary: true; onClicked: root.helpRequested() }
}
