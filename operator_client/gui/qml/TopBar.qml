import QtQuick
import "."

// Minimal chrome on the frame: history, the command palette, the indicators, the window buttons.
// Where you are is said by the body's breadcrumb, not here.
//
// THE WINDOW IS FRAMELESS, so this bar IS the title bar: its empty space drags the window, a double
// click on it maximises, and the three buttons on the right are the only ones there are.
Item {
    id: root

    property var indicators: []
    property bool maximised: false
    signal paletteClicked()
    signal minimizeClicked()
    signal maximizeClicked()
    signal closeClicked()
    signal dragStarted()

    implicitHeight: Theme.topBarHeight

    // declared first, so it sits BENEATH the palette, the indicators and the buttons: they take
    // their own clicks and what is left over is the bar itself, which moves the window
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton
        onPressed: root.dragStarted()
        onDoubleClicked: root.maximizeClicked()
    }

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 6
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        IconBtn { iconName: "back"; color: Qt.rgba(1, 1, 1, 0.75) }
        IconBtn { iconName: "fwd"; color: Qt.rgba(1, 1, 1, 0.75) }
    }

    // the command palette: one box for going anywhere, doing anything, finding a file
    Rectangle {
        id: palette
        anchors.centerIn: parent
        width: 420
        height: 30
        radius: Theme.radiusSm
        color: Qt.rgba(1, 1, 1, palArea.containsMouse ? 0.14 : 0.10)
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.12)
        Behavior on color { ColorAnimation { duration: Theme.durFast } }

        Row {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 9

            Icon {
                name: "search"
                color: Qt.rgba(1, 1, 1, 0.68)
                size: 15
                anchors.verticalCenter: parent.verticalCenter
            }
            Txt {
                text: "Go to, do, find"
                color: Qt.rgba(1, 1, 1, 0.68)
                font.pixelSize: Theme.fBody
                width: parent.width - 130
                anchors.verticalCenter: parent.verticalCenter
            }
            Txt {
                text: "Ctrl K"
                color: Qt.rgba(1, 1, 1, 0.5)
                monospace: true
                font.pixelSize: Theme.fSmall
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        MouseArea {
            id: palArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.paletteClicked()
        }
    }

    // indicators: lit until addressed, always in the chrome so they survive every page change
    Row {
        anchors.right: windowButtons.left
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6

        Repeater {
            model: root.indicators
            delegate: Rectangle {
                required property var modelData
                readonly property string tone: modelData.kind === "task_completed" ? "ok"
                    : (modelData.kind === "unaddressed_ping" || modelData.kind === "offer") ? "warn"
                    : modelData.kind === "session" ? "accent" : "danger"

                height: 26
                width: content.implicitWidth + 22
                radius: Theme.pill
                color: Qt.rgba(1, 1, 1, 0.10)
                border.width: 1
                border.color: Qt.rgba(1, 1, 1, 0.22)

                Row {
                    id: content
                    anchors.centerIn: parent
                    spacing: 7
                    Rectangle {
                        width: 7
                        height: 7
                        radius: 4
                        color: Theme.tone(parent.parent.tone)
                        anchors.verticalCenter: parent.verticalCenter
                        SequentialAnimation on opacity {
                            running: true
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.35; duration: 1400; easing.type: Easing.InOutQuad }
                            NumberAnimation { to: 1.0; duration: 1400; easing.type: Easing.InOutQuad }
                        }
                    }
                    Txt {
                        text: modelData.text
                        color: "#ffffff"
                        font.pixelSize: Theme.fMeta
                        font.weight: Font.Medium
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }
    }

    Row {
        id: windowButtons
        anchors.right: parent.right
        anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        spacing: 0
        IconBtn { objectName: "winMinimize"; iconName: "min"; glyph: 15
                  color: Qt.rgba(1, 1, 1, 0.75); onClicked: root.minimizeClicked() }
        IconBtn { objectName: "winMaximize"; iconName: root.maximised ? "restore" : "max"; glyph: 13
                  color: Qt.rgba(1, 1, 1, 0.75); onClicked: root.maximizeClicked() }
        IconBtn { objectName: "winClose"; iconName: "close"; glyph: 15
                  color: Qt.rgba(1, 1, 1, 0.75); onClicked: root.closeClicked() }
    }
}
