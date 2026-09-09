import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    property var vm
    spacing: 16
    SectionTitle { Layout.fillWidth: true; title: "设置与安全"; subtitle: "本地进程内运行，不开放网络端口" }
    GlassCard {
        Layout.fillWidth: true; implicitHeight: 260
        GridLayout { anchors.fill: parent; anchors.margins: 20; columns: 2; rowSpacing: 16; columnSpacing: 18
            Text { text: "工作区"; color: bedrock.themeData.text_secondary } Text { text: vm.workspacePath; color: bedrock.themeData.text_primary; Layout.fillWidth: true; elide: Text.ElideMiddle }
            Text { text: "模型"; color: bedrock.themeData.text_secondary } Text { text: "DeepSeek"; color: bedrock.themeData.accent }
            Text { text: "当前主题"; color: bedrock.themeData.text_secondary } RowLayout { Text { text: bedrock.themeData.label; color: bedrock.themeData.text_primary; font.weight: Font.DemiBold } ActionButton { text: "切换下一个"; onClicked: vm.cycleTheme() } }
            Text { text: "桌面模式"; color: bedrock.themeData.text_secondary } Text { text: "QML 进程内调用 · 无开放端口"; color: bedrock.themeData.text_primary }
            Text { text: "权限"; color: bedrock.themeData.text_secondary } Text { text: "外部操作必须审批"; color: bedrock.themeData.warning }
        }
    }
    GlassCard {
        Layout.fillWidth: true; Layout.fillHeight: true
        ColumnLayout { anchors.fill: parent; anchors.margins: 20; spacing: 12
            Text { text: "性能策略"; color: bedrock.themeData.text_primary; font.pixelSize: 17; font.weight: Font.DemiBold }
            Text { text: "• 主题切换只更新当前表现层，不重载会话和后端数据\n• 页面按需加载，未打开的页面不查询数据\n• 列表使用虚拟化与复用，数据无变化时不重绘\n• 对话只追加新消息，历史窗口有上限\n• 模型与文件操作在后台线程运行\n• 动画只在交互时运行，不启用持续粒子或实时模糊"; color: bedrock.themeData.text_secondary; font.pixelSize: 12; lineHeight: 1.55; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Item { Layout.fillHeight: true }
            RowLayout { ActionButton { text: "配置 DeepSeek"; primary: true; onClicked: vm.editModelConfiguration() } ActionButton { text: "测试连接"; onClicked: vm.testModelConnection() } ActionButton { text: "打开工作区"; onClicked: vm.openWorkspace() } Item { Layout.fillWidth: true } }
        }
    }
}
