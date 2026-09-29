import QtQuick
import QtQuick.Controls.Basic
import "."

// Several lines of plain words -- a task description, an assistance message, a note on a report.
TextArea {
    id: root
    implicitHeight: 88
    padding: Theme.s2 + 2
    font.family: Theme.sans
    font.pixelSize: Theme.fBody
    color: Theme.ink
    selectByMouse: true
    wrapMode: TextArea.Wrap
    placeholderTextColor: Theme.quiet

    background: Rectangle {
        radius: Theme.radius
        color: root.enabled ? Theme.surface : Theme.fill
        border.width: 1
        border.color: root.activeFocus ? Theme.primary : root.hovered ? Theme.primaryHover : Theme.border
        Behavior on border.color { ColorAnimation { duration: Theme.durFast } }
    }
}
