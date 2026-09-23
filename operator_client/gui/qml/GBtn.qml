import QtQuick
import QtQuick.Controls
import "."

// A ghost button: no fill until you touch it. Everything that is not the primary action.
AbstractButton {
    id: root
    property string iconName: ""
    property bool small: false

    implicitWidth: row.implicitWidth + (small ? 18 : 24)
    implicitHeight: small ? 28 : 34
    opacity: enabled ? 1 : 0.45
    hoverEnabled: true

    background: Rectangle {
        radius: Theme.radiusSm
        color: root.pressed ? Theme.line : root.hovered ? Theme.ground : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.durFast } }
    }
    contentItem: Row {
        id: row
        anchors.centerIn: parent
        spacing: 7
        Icon {
            name: root.iconName
            visible: root.iconName !== ""
            color: Theme.dim
            size: 15
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            text: root.text
            color: Theme.dim
            font.pixelSize: root.small ? Theme.fMeta : Theme.fBody
            font.weight: Font.Medium
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
