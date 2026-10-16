import QtQuick
import "."

// A CASE AS A PICTURE: what was touched and where it went, in columns -- where it began, where it was put, packed, taken out, and the traces left. The
// Engine draws nothing: it sends nodes (with their column, badges and counts) and the lines between them; this lays them out and paints them. A burst of the
// same step in one folder is one node ("14 files in Staging"), so a long evening reads as a handful of things.
Item {
    id: root
    objectName: "caseGraph"
    property var graph: ({ nodes: [], edges: [] })
    readonly property var colNames: ["Where it began", "Where it was put", "Packed", "Taken out", "Traces"]
    readonly property real colW: Math.max(120, (width - 8) / 5)
    readonly property real rowH: 76
    readonly property var nodes: graph && graph.nodes ? graph.nodes : []
    readonly property var edges: graph && graph.edges ? graph.edges : []
    readonly property var placed: {
        var rows = {}, out = {}
        nodes.forEach(function (n) {
            var r = rows[n.col] === undefined ? 0 : rows[n.col]
            rows[n.col] = r + 1
            out[n.id] = { x: n.col * colW + 8, y: 30 + r * rowH, w: colW - 44, h: 60, n: n }
        })
        return out
    }
    readonly property int tallest: { var m = 0, c = {}; nodes.forEach(function (n) { c[n.col] = (c[n.col] || 0) + 1; m = Math.max(m, c[n.col]) }); return m }
    implicitHeight: Math.max(140, 30 + tallest * rowH + 10)
    height: implicitHeight

    function toneOf(kind) { return kind === "drive" ? Theme.crit : kind === "archive" ? Theme.med : kind === "staging" ? Theme.accent : kind === "system" ? Theme.ser5 : kind === "trace" ? Theme.text4 : Theme.text3 }

    // column headings, only where something is
    Repeater {
        model: root.colNames
        Txt {
            required property string modelData
            required property int index
            visible: root.nodes.some(function (n) { return n.col === index })
            x: index * root.colW + 12; y: 6
            text: modelData.toUpperCase(); color: Theme.text4; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 0.6; elide: Text.ElideNone
        }
    }

    Canvas {
        id: lines
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections { target: root; function onPlacedChanged() { lines.requestPaint() } function onEdgesChanged() { lines.requestPaint() } }
        Connections { target: Theme; function onDarkChanged() { lines.requestPaint() } }
        onPaint: {
            var c = getContext("2d")
            c.reset()
            c.lineWidth = 1.5
            root.edges.forEach(function (e) {
                var a = root.placed[e.from], b = root.placed[e.to]
                if (!a || !b) return
                var x1 = a.x + a.w, y1 = a.y + a.h / 2, x2 = b.x, y2 = b.y + b.h / 2
                if (b.x <= a.x) { x1 = a.x + a.w / 2; y1 = a.y + a.h; x2 = b.x + b.w / 2; y2 = b.y }       // same column: down the side
                c.strokeStyle = Theme.alpha(Theme.text3, 0.75)
                c.beginPath()
                c.moveTo(x1, y1)
                var mx = (x1 + x2) / 2
                c.bezierCurveTo(mx, y1, mx, y2, x2, y2)
                c.stroke()
                // the arrow head
                c.fillStyle = c.strokeStyle
                c.beginPath()
                c.moveTo(x2, y2); c.lineTo(x2 - 7, y2 - 4); c.lineTo(x2 - 7, y2 + 4); c.closePath(); c.fill()
                c.fillStyle = Theme.text2
                c.font = "10px sans-serif"
                c.textAlign = "center"
                c.fillText(e.verb, mx, Math.min(y1, y2) - 4 + Math.abs(y2 - y1) / 2)
            })
        }
    }

    Repeater {
        model: root.nodes
        Rectangle {
            required property var modelData
            readonly property var p: root.placed[modelData.id]
            objectName: "node_" + modelData.id
            x: p ? p.x : 0; y: p ? p.y : 0; width: p ? p.w : 100; height: p ? p.h : 40
            radius: 7
            color: Theme.surface
            border.width: 1
            border.color: Theme.alpha(root.toneOf(modelData.kind), 0.6)
            Rectangle { width: 3; height: parent.height - 16; x: 6; y: 8; radius: 2; color: root.toneOf(modelData.kind) }
            Column {
                x: 18; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 26; spacing: 2
                Txt { text: modelData.label; width: parent.width; font.weight: Font.Medium; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
                      mono: modelData.kind === "file" || modelData.kind === "system" || modelData.kind === "archive" }
                Row {
                    spacing: 5
                    visible: modelData.badges.length > 0
                    Repeater {
                        model: modelData.badges
                        Rectangle {
                            required property string modelData
                            width: bl.implicitWidth + 10; height: 15; radius: 7
                            color: Theme.alpha(modelData === "deleted" ? Theme.crit : Theme.med, 0.14)
                            Txt { id: bl; anchors.centerIn: parent; text: modelData === "hidden" ? "hidden" : modelData === "deleted" ? "deleted after" : modelData
                                  color: modelData === "deleted" ? Theme.crit : Theme.med; font.pixelSize: 10; elide: Text.ElideNone }
                        }
                    }
                }
            }
        }
    }
}
