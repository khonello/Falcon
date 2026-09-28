import QtQuick
import QtQuick.Controls
import "."

// The one text field, on the kit's own tokens: recessed into the panel, a hairline that brightens on
// focus. The Material style floats its placeholder above the text once there is some; here the
// placeholder is a plain hint inside the field that simply goes away when something is written.
TextField {
    id: root
    implicitHeight: 36
    font.pixelSize: Theme.fBody
    color: Theme.ink
    placeholderTextColor: "transparent"
    leftPadding: Theme.s3; rightPadding: Theme.s3
    selectByMouse: true
    background: Rectangle {
        radius: Theme.radiusSm
        color: root.enabled ? Theme.ground : Theme.pane
        border.width: 1
        border.color: root.activeFocus ? Theme.accent : Theme.line
        Behavior on border.color { ColorAnimation { duration: Theme.durFast } }
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
        color: Theme.faint
    }
}
