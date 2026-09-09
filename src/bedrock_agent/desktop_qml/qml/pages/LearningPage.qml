import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

ColumnLayout {
    property var vm
    spacing: 16
    SectionTitle { Layout.fillWidth: true; title: "学习管理"; subtitle: "计划、记录、复习与 Agent 开发路线" }
    GridLayout {
        Layout.fillWidth: true; columns: 2; rowSpacing: 14; columnSpacing: 14
        StatCard { Layout.fillWidth: true; label: "近 30 天学习"; value: String(vm.dashboard.learningMinutes || 0) + " 分钟"; detail: "持续积累"; symbol: "△" }
        StatCard { Layout.fillWidth: true; label: "完成记录"; value: String(vm.dashboard.learningCompleted || 0); detail: "学习会话"; symbol: "✓" }
    }
    GlassCard {
        Layout.fillWidth: true; Layout.fillHeight: true
        ColumnLayout { anchors.fill: parent; anchors.margins: 20; spacing: 14
            Text { text: "快速开始"; color: bedrock.themeData.text_primary; font.pixelSize: 18; font.weight: Font.DemiBold }
            Text { text: "通过帮助中心的预设技能创建学习计划或记录进度。所有保存操作仍会进入审批中心。"; color: bedrock.themeData.text_secondary; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
            RowLayout { ActionButton { text: "创建 7 天计划"; primary: true; onClicked: vm.sendMessage("给我制定 7 天 Python 与 Agent 开发学习计划，每天 90 分钟，并保存。") } ActionButton { text: "记录今天学习"; onClicked: vm.sendMessage("记录今天学习 Python 60 分钟，自信度 3，并安排下次复习。") } Item { Layout.fillWidth: true } }
            Item { Layout.fillHeight: true }
        }
    }
}
