import QtQuick
import QtQuick.Controls
import "."

// The console button: one height, small radius, quiet by default. `tint` gives a filled,
// consequential button (traverse, end, terminate); `danger` is a tint that says so.
Button {
    id: root
    property color tint: "transparent"
    property bool danger: false
    readonly property color fill: danger ? Theme.danger : tint
    readonly property bool filled: fill.a > 0

    implicitHeight: Theme.controlHeight
    leftPadding: Theme.space3; rightPadding: Theme.space3
    font.pixelSize: Theme.fontBody
    font.bold: filled
    opacity: enabled ? 1 : 0.45

    contentItem: Label {
        text: root.text
        color: root.filled || root.hovered ? Theme.text : Theme.textDim
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: Theme.radius
        color: root.filled ? Theme.wash(root.fill, root.down ? 0.45 : (root.hovered ? 0.34 : 0.26))
                           : (root.down ? Theme.overlay : (root.hovered ? Theme.surfaceHigh : Theme.surface))
        border.width: 1
        border.color: root.filled ? Theme.wash(root.fill, 0.7) : Theme.border
        Behavior on color { ColorAnimation { duration: Theme.durationFast } }
    }
}
