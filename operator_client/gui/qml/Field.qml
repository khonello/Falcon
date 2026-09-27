import QtQuick
import QtQuick.Controls
import "."

// The console text field: one control height, recessed, hairline border that brightens on focus.
// The Material style floats its placeholder above the text once there is some; here the placeholder is a
// plain hint inside the field that simply goes away when something is written.
TextField {
    id: root
    implicitHeight: Theme.controlHeight
    font.pixelSize: Theme.fontBody
    color: Theme.text
    placeholderTextColor: "transparent"
    leftPadding: Theme.space2; rightPadding: Theme.space2
    selectByMouse: true
    background: Rectangle {
        radius: Theme.radius
        color: root.enabled ? Theme.canvas : Theme.surface
        border.width: 1
        border.color: root.activeFocus ? Theme.accent : Theme.border
        Behavior on border.color { ColorAnimation { duration: Theme.durationFast } }
    }
    Text {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: root.leftPadding
        anchors.rightMargin: root.rightPadding
        anchors.verticalCenter: parent.verticalCenter
        visible: root.text === "" && root.preeditText === ""
        text: root.placeholderText
        elide: Text.ElideRight
        font: root.font
        color: Theme.textFaint
    }
}
