import QtQuick
import "."

// A SWITCH: on or off, and it takes effect the moment it moves. Anything that needs confirming is a
// button and a Confirm, not this.
Item {
    id: root
    property bool on: false
    property bool busy: false
    signal toggled(bool on)

    implicitWidth: 40
    implicitHeight: 22
    opacity: enabled ? 1 : 0.45

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: root.on ? Theme.primary : Theme.quiet
        Behavior on color { ColorAnimation { duration: Theme.durFast } }

        Rectangle {
            width: 18
            height: 18
            radius: 9
            y: 2
            x: root.on ? parent.width - width - 2 : 2
            color: Theme.surface
            Behavior on x { NumberAnimation { duration: Theme.durFast; easing.type: Easing.OutCubic } }
        }
    }
    MouseArea {
        anchors.fill: parent
        enabled: root.enabled && !root.busy
        cursorShape: Qt.PointingHandCursor
        onClicked: { root.on = !root.on; root.toggled(root.on) }
    }
}
