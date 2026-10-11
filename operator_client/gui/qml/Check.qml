import QtQuick
import "."

// A CHECKBOX. Also the header one, which is three-state: none, some, all.
Item {
    id: root
    property bool checked: false
    property bool partial: false          // some of the rows, not all
    property bool controlled: false       // the owner sets `checked` from its data; a click only asks
    opacity: enabled ? 1 : 0.5
    property string text: ""
    signal toggled(bool checked)

    implicitWidth: 16 + (text !== "" ? Theme.s2 + label.implicitWidth : 0)
    implicitHeight: Math.max(16, label.implicitHeight)

    Rectangle {
        id: box
        width: 16
        height: 16
        anchors.verticalCenter: parent.verticalCenter
        radius: Theme.radiusSm
        color: root.checked || root.partial ? Theme.primary : Theme.surface
        border.width: 1
        border.color: root.checked || root.partial ? Theme.primary
                      : hov.containsMouse ? Theme.primary : Theme.border
        Behavior on color { ColorAnimation { duration: Theme.durFast } }

        Icon {
            anchors.centerIn: parent
            visible: root.checked && !root.partial
            name: "check"
            size: 12
            color: Theme.inverse
        }
        Rectangle {
            anchors.centerIn: parent
            visible: root.partial
            width: 8
            height: 2
            color: Theme.inverse
        }
    }
    Txt {
        id: label
        anchors.left: box.right
        anchors.leftMargin: Theme.s2
        anchors.verticalCenter: parent.verticalCenter
        text: root.text
        visible: root.text !== ""
        font.pixelSize: Theme.fBody
    }
    MouseArea {
        id: hov
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: { var v = !root.checked; if (!root.controlled) { root.checked = v; root.partial = false } root.toggled(v) }
    }
}
