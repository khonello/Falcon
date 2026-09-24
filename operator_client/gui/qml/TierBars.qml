import QtQuick
import "."

// Violations by tier: few enough to be a bar chart, serious enough to name each tier even when
// its count is zero. A zero keeps its row, quietened -- it is a result, not an absence.
Item {
    id: root

    property var rows: []                  // [{ label, count }]
    // optional, keyed by the tier's label: the file that broke the rule, named on the line it
    // broke. The cell has no room for it; opened, the line has the whole width.
    property var notes: ({})
    property int labelWidth: 108
    property int barHeight: 16
    property int rowGap: 26
    // a count of one is one unit wide, not a full-width bar: these numbers are small on purpose
    readonly property real unit: {
        var m = 1
        for (var i = 0; i < rows.length; i++) m = Math.max(m, rows[i].count)
        return Math.min(120, Math.max(24, (width - labelWidth - 46) / m))
    }

    implicitHeight: rows.length * rowGap

    Column {
        width: parent.width
        spacing: root.rowGap - root.barHeight

        Repeater {
            model: root.rows
            delegate: Item {
                id: line
                required property var modelData
                width: root.width
                height: root.barHeight

                Txt {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: line.modelData.label
                    color: Theme.dim
                    monospace: true
                    font.pixelSize: Theme.fBody
                }
                Rectangle {
                    id: bar
                    x: root.labelWidth
                    width: Math.max(6, line.modelData.count * root.unit)
                    height: parent.height
                    radius: 4
                    color: line.modelData.count > 0 ? Theme.danger : Theme.line2
                    opacity: line.modelData.count > 0 ? 1 : 0.35
                }
                Txt {
                    id: n
                    anchors.left: bar.right
                    anchors.leftMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: String(line.modelData.count)
                    color: Theme.faint
                    monospace: true
                    font.pixelSize: Theme.fMeta
                }
                Txt {
                    anchors.left: n.right
                    anchors.leftMargin: 20
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.notes[line.modelData.label] || ""
                    visible: text !== ""
                    font.pixelSize: Theme.fBody
                    elide: Text.ElideRight
                }
            }
        }
    }
}
