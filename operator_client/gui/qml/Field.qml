import QtQuick
import QtQuick.Controls
import "."

// The console text field: one control height, recessed, hairline border that brightens on focus.
TextField {
    id: root
    implicitHeight: Theme.controlHeight
    font.pixelSize: Theme.fontBody
    color: Theme.text
    placeholderTextColor: Theme.textFaint
    leftPadding: Theme.space2; rightPadding: Theme.space2
    selectByMouse: true
    background: Rectangle {
        radius: Theme.radius
        color: root.enabled ? Theme.canvas : Theme.surface
        border.width: 1
        border.color: root.activeFocus ? Theme.accent : Theme.border
        Behavior on border.color { ColorAnimation { duration: Theme.durationFast } }
    }
}
