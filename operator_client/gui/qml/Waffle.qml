import QtQuick
import QtQuick.Controls
import "."

// One square per client PC, coloured by where it is in the rollout. The fleet, countable by eye.
Flow {
    id: root

    property var cells: []                 // [{ tone, label }] -- label is the tooltip
    property int cellSize: 30
    property int gap: 8

    spacing: gap

    Repeater {
        model: root.cells
        delegate: Rectangle {
            required property var modelData
            width: root.cellSize
            height: root.cellSize
            radius: 6
            color: modelData.tone === "quiet" ? Theme.line2 : Theme.tone(modelData.tone)
            opacity: modelData.tone === "quiet" ? 0.5 : 1

            ToolTip.visible: area.containsMouse && modelData.label !== ""
            ToolTip.text: modelData.label || ""
            MouseArea { id: area; anchors.fill: parent; hoverEnabled: true }
        }
    }
}
