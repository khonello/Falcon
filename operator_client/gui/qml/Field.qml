import QtQuick
import QtQuick.Controls.Basic
import "."

// One text field. The placeholder is a plain hint inside it, and it goes when something is written.
TextField {
    id: root
    property string iconName: ""

    implicitHeight: Theme.control
    leftPadding: (iconName === "" ? Theme.s3 : Theme.s5 + Theme.s2)
    rightPadding: Theme.s3
    font.family: Theme.sans
    font.pixelSize: Theme.fBody
    color: Theme.ink
    selectByMouse: true
    placeholderTextColor: Theme.quiet

    background: Rectangle {
        radius: Theme.radius
        color: root.enabled ? Theme.surface : Theme.fill
        border.width: 1
        border.color: root.activeFocus ? Theme.primary : root.hovered ? Theme.primaryHover : Theme.border
        Behavior on border.color { ColorAnimation { duration: Theme.durFast } }
    }
    Icon {
        visible: root.iconName !== ""
        name: root.iconName
        size: 15
        color: Theme.quiet
        anchors.left: parent.left
        anchors.leftMargin: Theme.s3
        anchors.verticalCenter: parent.verticalCenter
    }
}
