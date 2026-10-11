import QtQuick
import "."

// A thin bar that fills: v of max, in colour c, with an optional mark (a target) across it.
Item {
    id: root
    property real v: 0
    property real max: 100
    property color c: Theme.ser6
    property var mark: null
    property int thickness: 6
    implicitWidth: 90
    implicitHeight: thickness

    Rectangle {
        anchors.fill: parent
        radius: root.thickness / 2
        color: Theme.surface3
        Rectangle {
            width: parent.width * Math.max(0, Math.min(1, root.max > 0 ? root.v / root.max : 0))
            height: parent.height
            radius: parent.radius
            color: root.c
        }
        Rectangle {
            visible: root.mark !== null
            x: root.mark !== null ? parent.width * Math.min(1, root.mark / root.max) : 0
            y: -3
            width: 1.5
            height: parent.height + 6
            color: Theme.text3
        }
    }
}
