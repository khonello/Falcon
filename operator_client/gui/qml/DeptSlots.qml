import QtQuick
import QtQuick.Controls
import "."

// One department's client PCs, drawn against the largest department rather than on their own.
// Every slot the biggest department has is drawn; the ones this department does not fill stay
// faded. Its size and its state then read at the same time, and departments stay comparable
// without a second chart.
Flow {
    id: root

    property var hosts: []                  // [{ hostname, state }] -- state is a tone name
    property int biggest: hosts.length
    property int gap: 8
    property int maxSlot: 54
    readonly property int count: Math.max(biggest, hosts.length)
    // one row, always: the comparison is the point and a wrapped row does not read as a scale
    readonly property int slotSize: Math.max(22, Math.min(maxSlot,
        Math.floor((width - (count - 1) * gap) / Math.max(1, count))))

    spacing: gap

    Repeater {
        model: Math.max(root.biggest, root.hosts.length)
        delegate: Rectangle {
            required property int index
            readonly property bool filled: index < root.hosts.length
            readonly property var host: filled ? root.hosts[index] : null

            width: root.slotSize
            height: root.slotSize
            radius: Math.round(root.slotSize * 0.24)
            color: filled ? Theme.tone(host.state) : Theme.line
            opacity: filled ? 0.92 : 0.45

            Txt {
                anchors.centerIn: parent
                visible: parent.filled
                text: parent.filled ? String(parent.host.hostname).split("-").pop() : ""
                color: Theme.chartBg
                monospace: true
                font.pixelSize: Theme.fRow
                font.weight: Font.Medium
            }

            ToolTip.visible: area.containsMouse && filled
            ToolTip.text: filled ? host.hostname : ""
            MouseArea { id: area; anchors.fill: parent; hoverEnabled: parent.filled }
        }
    }
}
