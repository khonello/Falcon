import QtQuick
import QtQuick.Controls.Basic
import "."

// One text field. The placeholder is a plain hint inside it, and it goes when something is written.
TextField {
    id: root
    property string iconName: ""

    implicitHeight: Theme.control
    leftPadding: (iconName === "" ? 10 : Theme.s5 + Theme.s2)
    rightPadding: 10
    topPadding: 0
    bottomPadding: 0
    verticalAlignment: TextInput.AlignVCenter
    selectionColor: Theme.alpha(Theme.accent, 0.3)
    font.family: Theme.sans
    font.pixelSize: Theme.fBody
    color: Theme.text
    selectByMouse: true
    placeholderTextColor: Theme.text4

    background: Rectangle {
        radius: Theme.radiusSm
        color: root.enabled ? Theme.surface : Theme.surface2
        border.width: 1
        border.color: root.activeFocus || root.hovered ? Theme.accent : Theme.borderStrong
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
