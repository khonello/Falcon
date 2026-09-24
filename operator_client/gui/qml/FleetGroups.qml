import QtQuick
import QtQuick.Controls
import "."

// The whole fleet, one square per client PC, grouped by the department that owns it.
//
// The plain Waffle is right in a small cell, where the fleet is a quantity. Opened, the fleet is a
// set of machines you have to be able to name -- and hostname numbers repeat across departments
// (OPS-01, FIN-01, LOG-01), so an ungrouped row of squares reads as nonsense. Grouping puts every
// number under the name that disambiguates it, and the groups' widths say how big each department
// is, without a second chart.
Row {
    id: root

    property var groups: []                 // [{ name, cells: [{ tone, name, label }] }]
    property int gap: 10
    property int groupGap: 30
    property int maxPerRow: 7
    property int maxSize: 62

    readonly property int columns: {
        var n = 0
        for (var i = 0; i < groups.length; i++)
            n += Math.min(maxPerRow, Math.max(1, groups[i].cells.length))
        return Math.max(1, n)
    }
    // every group is laid out at the same square size, so the squares stay comparable across
    // departments; the size is whatever fits the width once the gaps are paid for
    readonly property int size: Math.max(22, Math.min(maxSize,
        Math.floor((width - (groups.length - 1) * groupGap - (columns - groups.length) * gap) / columns)))

    spacing: groupGap

    Repeater {
        model: root.groups
        delegate: Column {
            required property var modelData
            readonly property int cols: Math.min(root.maxPerRow, Math.max(1, modelData.cells.length))

            spacing: 10
            width: cols * (root.size + root.gap) - root.gap

            Flow {
                width: parent.width
                spacing: root.gap

                Repeater {
                    model: modelData.cells
                    delegate: Rectangle {
                        required property var modelData
                        width: root.size
                        height: root.size
                        radius: Math.round(root.size * 0.22)
                        color: modelData.tone === "quiet" ? Theme.line2 : Theme.tone(modelData.tone)
                        opacity: modelData.tone === "quiet" ? 0.5 : 0.92

                        Txt {
                            anchors.centerIn: parent
                            visible: root.size >= 34
                            text: modelData.name ? String(modelData.name).split("-").pop() : ""
                            color: Theme.chartBg
                            monospace: true
                            font.pixelSize: Theme.fRow
                            font.weight: Font.Medium
                        }

                        ToolTip.visible: area.containsMouse && !!modelData.label
                        ToolTip.text: modelData.label || ""
                        MouseArea { id: area; anchors.fill: parent; hoverEnabled: true }
                    }
                }
            }

            Txt {
                width: parent.width
                text: modelData.name
                color: Theme.faint
                font.pixelSize: Theme.fMeta
                elide: Text.ElideRight
            }
        }
    }
}
