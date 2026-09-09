import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property var taskModel
    property int visibleCardLimit: 7
    property int transitionDuration: 420
    property bool wrapNavigation: true
    readonly property int taskCount: taskModel ? taskModel.count : 0
    readonly property var activeTask: taskCount > 0 ? taskModel.get(prism.currentIndex) : null

    signal openSession(string sessionId)

    function movePrevious() {
        if (taskCount <= 1)
            return
        if (wrapNavigation)
            prism.decrementCurrentIndex()
        else
            prism.currentIndex = Math.max(0, prism.currentIndex - 1)
    }

    function moveNext() {
        if (taskCount <= 1)
            return
        if (wrapNavigation)
            prism.incrementCurrentIndex()
        else
            prism.currentIndex = Math.min(taskCount - 1, prism.currentIndex + 1)
    }

    function moveTo(index) {
        if (index < 0 || index >= taskCount || index === prism.currentIndex)
            return
        prism.currentIndex = index
    }

    clip: true
    focus: true

    Rectangle {
        anchors.fill: parent
        radius: 16
        color: "#090e0b"
        border.width: 1
        border.color: "#1f3328"

        gradient: Gradient {
            GradientStop { position: 0.0; color: "#101a14" }
            GradientStop { position: 0.5; color: "#080d0a" }
            GradientStop { position: 1.0; color: "#050806" }
        }
    }

    Canvas {
        id: grid
        anchors.fill: parent
        opacity: 0.12

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.strokeStyle = bedrock.themeData.accent
            ctx.lineWidth = 0.55
            var horizon = height * 0.62
            for (var x = -width; x < width * 2; x += 42) {
                ctx.beginPath()
                ctx.moveTo(width / 2, horizon)
                ctx.lineTo(x, height)
                ctx.stroke()
            }
            for (var y = horizon; y < height; y += 24) {
                ctx.beginPath()
                ctx.moveTo(0, y)
                ctx.lineTo(width, y)
                ctx.stroke()
            }
        }

        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }

    Rectangle {
        id: centerGlow
        width: Math.min(540, parent.width * 0.58)
        height: Math.min(280, parent.height * 0.72)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: 6
        radius: 34
        color: "#183d28"
        opacity: taskCount > 0 ? 0.28 : 0.0
        scale: 0.93

        Behavior on opacity {
            NumberAnimation { duration: 180 }
        }
    }

    Rectangle {
        width: parent.width * 0.66
        height: 1
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: 128
        color: bedrock.themeData.accent
        opacity: 0.22
    }

    PathView {
        id: prism
        anchors.fill: parent
        anchors.leftMargin: 54
        anchors.rightMargin: 54
        anchors.topMargin: 10
        anchors.bottomMargin: 46

        model: root.taskModel
        interactive: root.taskCount > 1
        pathItemCount: Math.min(root.taskCount, root.visibleCardLimit)
        preferredHighlightBegin: 0.5
        preferredHighlightEnd: 0.5
        highlightRangeMode: PathView.StrictlyEnforceRange
        snapMode: PathView.SnapToItem
        highlightMoveDuration: root.transitionDuration
        flickDeceleration: 2200

        path: Path {
            startX: 70
            startY: prism.height * 0.57

            PathAttribute { name: "cardScale"; value: 0.63 }
            PathAttribute { name: "cardOpacity"; value: 0.18 }
            PathAttribute { name: "cardAngle"; value: -64 }
            PathAttribute { name: "cardLift"; value: 18 }
            PathAttribute { name: "cardDepth"; value: 0 }

            PathCubic {
                x: prism.width * 0.5
                y: prism.height * 0.49
                control1X: prism.width * 0.16
                control1Y: prism.height * 0.48
                control2X: prism.width * 0.36
                control2Y: prism.height * 0.43
            }

            PathAttribute { name: "cardScale"; value: 1.0 }
            PathAttribute { name: "cardOpacity"; value: 1.0 }
            PathAttribute { name: "cardAngle"; value: 0 }
            PathAttribute { name: "cardLift"; value: 0 }
            PathAttribute { name: "cardDepth"; value: 100 }

            PathCubic {
                x: prism.width - 70
                y: prism.height * 0.57
                control1X: prism.width * 0.64
                control1Y: prism.height * 0.43
                control2X: prism.width * 0.84
                control2Y: prism.height * 0.48
            }

            PathAttribute { name: "cardScale"; value: 0.63 }
            PathAttribute { name: "cardOpacity"; value: 0.18 }
            PathAttribute { name: "cardAngle"; value: 64 }
            PathAttribute { name: "cardLift"; value: 18 }
            PathAttribute { name: "cardDepth"; value: 0 }
        }

        delegate: Item {
            id: cardHost

            required property int index
            required property string title
            required property string subtitle
            required property string state
            required property int progress
            required property string accent
            required property string session_id

            readonly property bool isCurrent: PathView.isCurrentItem

            width: Math.min(500, prism.width * 0.56)
            height: Math.min(248, prism.height * 0.72)
            scale: PathView.cardScale
            opacity: PathView.cardOpacity
            z: PathView.cardDepth
            transform: [
                Translate {
                    y: cardHost.PathView.cardLift
                },
                Rotation {
                    origin.x: cardHost.width / 2
                    origin.y: cardHost.height / 2
                    axis.x: 0
                    axis.y: 1
                    axis.z: 0
                    angle: cardHost.PathView.cardAngle
                }
            ]

            Rectangle {
                anchors.fill: parent
                anchors.leftMargin: cardHost.isCurrent ? 18 : 8
                anchors.rightMargin: cardHost.isCurrent ? -18 : -8
                anchors.topMargin: 12
                anchors.bottomMargin: -12
                radius: 24
                color: cardHost.accent === "green" ? "#133322" : bedrock.themeData.surface_strong
                border.width: 1
                border.color: cardHost.isCurrent ? "#36dd7f" : "#27352d"
                opacity: cardHost.isCurrent ? 0.26 : 0.14
            }

            Rectangle {
                id: card
                anchors.fill: parent
                radius: 22
                border.width: cardHost.isCurrent ? 1.5 : 1
                border.color: cardHost.isCurrent ? bedrock.themeData.accent : "#33443a"

                gradient: Gradient {
                    GradientStop {
                        position: 0.0
                        color: cardHost.isCurrent ? "#203a2a" : "#17211a"
                    }
                    GradientStop { position: 0.44; color: bedrock.themeData.surface_strong }
                    GradientStop { position: 1.0; color: "#080c0a" }
                }

                Rectangle {
                    width: parent.width * 0.58
                    height: 2
                    radius: 1
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: cardHost.isCurrent ? bedrock.themeData.accent : bedrock.themeData.text_muted
                    opacity: cardHost.isCurrent ? 0.8 : 0.24
                }

                Rectangle {
                    width: 5
                    height: parent.height - 42
                    radius: 3
                    anchors.left: parent.left
                    anchors.leftMargin: 13
                    anchors.verticalCenter: parent.verticalCenter
                    color: cardHost.accent === "green" ? bedrock.themeData.accent : bedrock.themeData.text_muted
                    opacity: cardHost.isCurrent ? 0.95 : 0.35
                }

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    cursorShape: Qt.PointingHandCursor
                    propagateComposedEvents: true
                    z: 0

                    onClicked: {
                        root.forceActiveFocus()
                        if (cardHost.isCurrent)
                            mouse.accepted = false
                        else
                            root.moveTo(cardHost.index)
                    }

                    onDoubleClicked: {
                        if (cardHost.session_id)
                            root.openSession(cardHost.session_id)
                    }
                }

                ColumnLayout {
                    anchors.fill: parent
                    z: 1
                    anchors.leftMargin: 32
                    anchors.rightMargin: 24
                    anchors.topMargin: 22
                    anchors.bottomMargin: 20
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true

                        Rectangle {
                            width: 9
                            height: 9
                            radius: 5
                            color: cardHost.state === "等待审批" ? bedrock.themeData.warning : bedrock.themeData.accent
                        }

                        Text {
                            text: cardHost.state
                            color: cardHost.state === "等待审批" ? bedrock.themeData.warning : bedrock.themeData.accent
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: String(cardHost.index + 1).padStart(2, "0") + " / " + String(root.taskCount).padStart(2, "0")
                            color: bedrock.themeData.text_muted
                            font.pixelSize: 10
                            font.letterSpacing: 1.2
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: cardHost.title
                        color: bedrock.themeData.text_primary
                        font.pixelSize: cardHost.isCurrent ? 22 : 18
                        font.weight: Font.DemiBold
                        wrapMode: Text.Wrap
                        maximumLineCount: 3
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: cardHost.subtitle
                        color: bedrock.themeData.text_secondary
                        font.pixelSize: 12
                    }

                    Item { Layout.fillHeight: true }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "任务进度"; color: bedrock.themeData.text_muted; font.pixelSize: 10 }
                                Item { Layout.fillWidth: true }
                                Text { text: String(cardHost.progress) + "%"; color: cardHost.isCurrent ? bedrock.themeData.accent : "#8c9892"; font.pixelSize: 11 }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 5
                                radius: 3
                                color: "#253129"

                                Rectangle {
                                    width: parent.width * Math.max(0, Math.min(1, cardHost.progress / 100))
                                    height: parent.height
                                    radius: 3
                                    color: cardHost.isCurrent ? bedrock.themeData.accent : bedrock.themeData.text_muted

                                    Behavior on width {
                                        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
                                    }
                                }
                            }
                        }

                        ActionButton {
                            visible: cardHost.isCurrent
                            text: "打开会话"
                            primary: true
                            onClicked: root.openSession(cardHost.session_id)
                        }
                    }
                }
            }
        }

        onCountChanged: {
            if (count === 0)
                currentIndex = 0
            else if (currentIndex >= count)
                currentIndex = count - 1
        }
    }

    WheelHandler {
        id: wheelNavigation
        target: null
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad

        onWheel: function(event) {
            var delta = Math.abs(event.angleDelta.x) > Math.abs(event.angleDelta.y)
                    ? event.angleDelta.x : event.angleDelta.y
            if (delta < 0)
                root.moveNext()
            else if (delta > 0)
                root.movePrevious()
            event.accepted = true
        }
    }

    Keys.onLeftPressed: function(event) {
        root.movePrevious()
        event.accepted = true
    }

    Keys.onRightPressed: function(event) {
        root.moveNext()
        event.accepted = true
    }

    RowLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        anchors.bottomMargin: 8
        spacing: 10

        ActionButton {
            text: "‹"
            enabled: root.taskCount > 1
            onClicked: root.movePrevious()
        }

        Text {
            Layout.fillWidth: true
            text: root.taskCount > 1
                    ? "拖动卡片 · 滚轮切换 · ← → 翻页"
                    : (root.taskCount === 1 ? "当前只有 1 个任务会话" : "开始会话后，任务会进入棱镜")
            color: bedrock.themeData.text_muted
            font.pixelSize: 10
            horizontalAlignment: Text.AlignHCenter
        }

        Row {
            visible: root.taskCount > 1
            spacing: 6

            Repeater {
                model: Math.min(root.taskCount, 9)

                Rectangle {
                    required property int index
                    width: prism.currentIndex === index ? 22 : 6
                    height: 6
                    radius: 3
                    color: prism.currentIndex === index ? bedrock.themeData.accent : "#34423a"

                    Behavior on width {
                        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.moveTo(parent.index)
                    }
                }
            }
        }

        ActionButton {
            text: "›"
            enabled: root.taskCount > 1
            onClicked: root.moveNext()
        }
    }

    Text {
        anchors.centerIn: parent
        visible: root.taskCount === 0
        text: "开始一个会话后，任务卡会出现在这里"
        color: bedrock.themeData.text_muted
        font.pixelSize: 12
    }
}
