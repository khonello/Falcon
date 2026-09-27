import QtQuick
import QtQuick.Shapes
import "."

// ANYTHING THAT BRANCHES, AS A TREE (design/PATTERNS.md section 6 -- "very beautiful, just breathtaking").
//
// Nodes are cards with a BARE icon; joins are cubic curves from the right middle of one node to the left middle of the
// next, quiet (rgba white 0.22). A broken branch: its nodes get a thin danger ring and its joins go dashed danger; the
// rest stays quiet. Positions are the caller's (a flow's layout is computed from its stages, not guessed here).
//
//   nodes  [{ id, x, y, w, icon, label, sub, tone, bad }]
//   links  [{ from, to, bad }]   -- ids
Item {
    id: root

    property var nodes: []
    property var links: []
    property int nodeHeight: 46
    signal nodeClicked(var node)

    function nodeById(id) {
        for (var i = 0; i < nodes.length; i++) if (nodes[i].id === id) return nodes[i]
        return null
    }

    Repeater {
        model: root.links
        delegate: Shape {
            id: join
            required property var modelData
            readonly property var a: root.nodeById(modelData.from)
            readonly property var b: root.nodeById(modelData.to)
            readonly property real x1: a ? a.x + (a.w || 150) : 0
            readonly property real y1: a ? a.y + root.nodeHeight / 2 : 0
            readonly property real x2: b ? b.x : 0
            readonly property real y2: b ? b.y + root.nodeHeight / 2 : 0
            anchors.fill: parent
            antialiasing: true
            layer.enabled: true
            layer.samples: 4
            ShapePath {
                strokeColor: join.modelData.bad ? Theme.danger : Qt.rgba(1, 1, 1, 0.22)
                strokeWidth: 2.2
                strokeStyle: join.modelData.bad ? ShapePath.DashLine : ShapePath.SolidLine
                dashPattern: [2.5, 2.5]
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                startX: join.x1; startY: join.y1
                PathCubic {
                    x: join.x2; y: join.y2
                    control1X: (join.x1 + join.x2) / 2; control1Y: join.y1
                    control2X: (join.x1 + join.x2) / 2; control2Y: join.y2
                }
            }
        }
    }

    Repeater {
        model: root.nodes
        delegate: Rectangle {
            required property var modelData
            x: modelData.x
            y: modelData.y
            width: modelData.w || 150
            height: root.nodeHeight
            radius: 12
            color: area.containsMouse ? Qt.lighter(Theme.pane, 1.12) : Theme.pane
            border.width: modelData.bad ? 1.5 : 0
            border.color: Theme.danger

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10
                Icon { name: modelData.icon || "folder"; size: 17; anchors.verticalCenter: parent.verticalCenter
                       color: modelData.bad ? Theme.danger : Theme.tone(modelData.tone || "accent") }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1
                    Txt { text: modelData.label || ""; color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                    Txt { visible: !!modelData.sub; text: modelData.sub || ""; font.pixelSize: Theme.fMeta - 1
                          color: modelData.bad ? Theme.danger : Theme.faint }
                }
            }
            MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: root.nodeClicked(modelData) }
        }
    }
}
