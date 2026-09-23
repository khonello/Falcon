import QtQuick
import QtQuick.Shapes
import "."

// Cross-department assistance: who helped whom today, and how often. Thickness is the count; the
// colour is the department that gave the help. Nothing here is gated -- it is oversight, not a lever.
Item {
    id: root

    property var nodes: []                 // [{ id, name }] in department order
    property var links: []                 // [{ from, to, count }] -- from/to are node indexes
    readonly property real baseY: height - 34

    function nodeX(i) { return nodes.length > 1 ? (width * (i + 1)) / (nodes.length + 1) : width / 2 }

    Repeater {
        model: root.links
        delegate: Shape {
            id: arc
            required property var modelData
            anchors.fill: parent
            antialiasing: true
            layer.enabled: true
            layer.samples: 4

            readonly property real ax: Math.min(root.nodeX(modelData.from), root.nodeX(modelData.to))
            readonly property real bx: Math.max(root.nodeX(modelData.from), root.nodeX(modelData.to))
            readonly property real r: Math.max(8, (bx - ax) / 2)

            ShapePath {
                strokeColor: Theme.series(arc.modelData.from)
                strokeWidth: 1 + arc.modelData.count * 1.6
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                startX: arc.ax
                startY: root.baseY
                PathArc {
                    x: arc.bx
                    y: root.baseY
                    radiusX: arc.r
                    radiusY: arc.r * 0.72
                    direction: PathArc.Clockwise
                }
            }
        }
    }

    Repeater {
        model: root.links
        delegate: Txt {
            required property var modelData
            text: String(modelData.count)
            color: Theme.faint
            monospace: true
            font.pixelSize: Theme.fMeta
            x: (root.nodeX(modelData.from) + root.nodeX(modelData.to)) / 2 - width / 2
            y: root.baseY - Math.abs(root.nodeX(modelData.to) - root.nodeX(modelData.from)) / 2 * 0.72 - 20
        }
    }

    Repeater {
        model: root.nodes
        delegate: Item {
            id: node
            required property var modelData
            required property int index
            anchors.fill: parent

            Rectangle {
                width: 14
                height: 14
                radius: 7
                color: Theme.series(node.index)
                x: root.nodeX(node.index) - 7
                y: root.baseY - 7
            }
            Txt {
                text: node.modelData.name
                color: Theme.dim
                font.pixelSize: Theme.fBody
                x: root.nodeX(node.index) - width / 2
                y: root.baseY + 14
            }
        }
    }

    Txt {
        anchors.centerIn: parent
        visible: root.links.length === 0
        text: "No cross-department help today"
        color: Theme.faint
        font.pixelSize: Theme.fBody
    }
}
