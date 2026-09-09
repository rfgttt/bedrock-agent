import QtQuick
import QtQuick.Controls

Item {
    id: root
    property var vm

    function pageSource(page) {
        var map = {
            "dashboard": "../pages/DashboardPage.qml",
            "chat": "../pages/ChatPage.qml",
            "tasks": "../pages/TasksPage.qml",
            "approvals": "../pages/ApprovalsPage.qml",
            "workspace": "../pages/WorkspacePage.qml",
            "apps": "../pages/AppsPage.qml",
            "learning": "../pages/LearningPage.qml",
            "skills": "../pages/SkillsPage.qml",
            "mcp": "../pages/McpPage.qml",
            "memory": "../pages/MemoryPage.qml",
            "traces": "../pages/TracePage.qml",
            "settings": "../pages/SettingsPage.qml"
        }
        return map[page] || map.dashboard
    }

    Loader {
        id: pageLoader
        anchors.fill: parent
        source: root.pageSource(root.vm.currentPage)
        asynchronous: true
        onLoaded: if (item) item.vm = root.vm
    }
    BusyIndicator {
        anchors.centerIn: parent
        running: pageLoader.status === Loader.Loading
        visible: running
    }
}
