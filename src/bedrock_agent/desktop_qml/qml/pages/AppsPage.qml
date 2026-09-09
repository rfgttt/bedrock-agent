import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    id: root
    property var vm
    spacing: 14
    SectionTitle { Layout.fillWidth: true; title: "应用白名单"; subtitle: "模型只能请求启动这里明确允许的程序"; actionText: "刷新发现"; onAction: vm.refreshApps() }
    RowLayout { ActionButton { text: "添加应用…"; primary: true; onClicked: vm.addApplication() } Item { Layout.fillWidth: true } Text { text: "启动前仍需审批"; color: bedrock.themeData.text_muted; font.pixelSize: 11 } }
    GridView {
        Layout.fillWidth: true; Layout.fillHeight: true
        cellWidth: 330; cellHeight: 150; model: vm.appsModel; clip: true
        delegate: GlassCard {
            required property string name
            required property string key
            required property string path
            required property string status
            required property string source
            width: 316; height: 136; highlighted: status === "可用"
            ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 7
                RowLayout { Layout.fillWidth: true; Text { text: name; color: bedrock.themeData.text_primary; font.pixelSize: 16; font.weight: Font.DemiBold; Layout.fillWidth: true; elide: Text.ElideRight } Text { text: status; color: status === "可用" ? bedrock.themeData.accent : bedrock.themeData.warning; font.pixelSize: 10 } }
                Text { Layout.fillWidth: true; text: path || "尚未发现安装路径"; color: bedrock.themeData.text_secondary; font.pixelSize: 10; elide: Text.ElideMiddle }
                Text { text: source; color: bedrock.themeData.text_muted; font.pixelSize: 9 }
                RowLayout { Layout.fillWidth: true; ActionButton { text: "测试启动"; enabled: status === "可用"; onClicked: vm.requestLaunchApplication(name) } Item { Layout.fillWidth: true } ActionButton { text: "移除"; danger: true; onClicked: vm.removeApplication(key) } }
            }
        }
    }
}
