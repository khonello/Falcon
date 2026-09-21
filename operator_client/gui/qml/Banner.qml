import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// A full-width notice for something with consequences: the Super User is inside your view, your
// PC is blocked, the link is gone. Never a status-line message that scrolls past. Carries its own
// actions (End / Extend / Claim) so the answer is one click away from the warning.
Rectangle {
    id: root
    property string text: ""
    property color tint: Theme.danger
    readonly property bool shown: text !== ""
    default property alias actions: actionRow.data

    implicitHeight: shown ? 40 : 0
    visible: shown
    color: Theme.wash(tint, 0.22)
    clip: true
    Behavior on implicitHeight { NumberAnimation { duration: Theme.durationBase; easing.type: Theme.easing } }

    Rectangle { anchors.top: parent.top; width: parent.width; height: 2; color: root.tint }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space4; anchors.rightMargin: Theme.space3
        spacing: Theme.space3
        Rectangle {
            width: 8; height: 8; radius: 4; color: root.tint
            SequentialAnimation on opacity {
                running: root.shown; loops: Animation.Infinite
                NumberAnimation { to: 0.3; duration: 700 }
                NumberAnimation { to: 1; duration: 700 }
            }
        }
        Label {
            text: root.text
            color: Theme.text
            font.pixelSize: Theme.fontMedium
            font.bold: true
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
        RowLayout { id: actionRow; spacing: Theme.space2 }
    }
}
