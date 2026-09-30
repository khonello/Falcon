import QtQuick
import "."

// A TOOLTIP. What a truncated cell says in full, or why a control is off. Never anything a person
// needs -- if it only exists on hover, it is not in the interface.
Item {
    id: root
    property string text: ""
    property Item over: parent            // what has to be hovered
    property int side: Qt.AlignTop

    visible: text !== "" && hov.hovered
    z: 200
    width: 0
    height: 0

    HoverHandler { id: hov; target: root.over }

    Rectangle {
        x: -width / 2 + (root.over ? root.over.width / 2 : 0)
        y: root.side === Qt.AlignTop ? -height - 6 : (root.over ? root.over.height + 6 : 0)
        width: label.implicitWidth + 2 * Theme.s2
        height: 24
        radius: Theme.radiusSm
        color: Theme.ink
        opacity: root.visible ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.durFast } }

        Txt {
            id: label
            anchors.centerIn: parent
            text: root.text
            color: Theme.onDark
            font.pixelSize: 11
        }
    }
}
