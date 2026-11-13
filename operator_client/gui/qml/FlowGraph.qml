import QtQuick
import "."

// A FLOW, DRAWN (the concept's FlowGraph): From / Along the way / To over it; its sources at the left and destinations at
// the right as 176 x 28 boxes with "host path" in mono, its steps as 124 x 26 pills between, joined by soft grey curves,
// one row of 38px for each source or destination. A destination waiting for someone to pick a folder is dashed, and so is
// its line; one that stopped taking files is dashed red; a source that is gone says "moved away".
//   srcs: [{host, path, gone}]   stages: [{op}]   dests: [{host, path, ask, bad}]   wait: the flow waits for a folder
Column {
    id: root
    property var srcs: []
    property var stages: []
    property var dests: []
    property bool wait: false
    readonly property int rows: Math.max(srcs.length, dests.length, 1)
    readonly property real gH: rows * 38 + 6
    readonly property real nw: 176
    readonly property real nh: 28
    readonly property real sw: 124
    readonly property real sh: 26
    readonly property real dx: width - nw
    function ys(k, n) { return 3 + (gH - 6) * (k + 0.5) / n }
    function stX(i) { return stages.length === 1 ? (width - sw) / 2 : nw + 80 + (i * (width - 2 * nw - 160 - sw)) / Math.max(1, stages.length - 1) }
    readonly property real firstX: stages.length ? stX(0) : dx
    readonly property real lastX: stages.length ? stX(stages.length - 1) + sw : nw
    width: parent ? parent.width : 800
    spacing: 4
    topPadding: 4
    bottomPadding: 4

    Item {
        width: parent.width
        height: 16
        Repeater {
            model: [["From", root.nw / 2]].concat(root.stages.length ? [["Along the way", (root.stX(0) + root.stX(root.stages.length - 1) + root.sw) / 2]] : []).concat([["To", root.dx + root.nw / 2]])
            delegate: Txt { required property var modelData; x: modelData[1] - implicitWidth / 2; text: modelData[0]; font.pixelSize: 12; color: Theme.text4; elide: Text.ElideNone }
        }
    }
    Item {
        width: parent.width
        height: root.gH
        Canvas {
            id: cv
            anchors.fill: parent
            onPaint: {
                var g = getContext("2d"); g.reset()
                var mid = root.gH / 2
                function line(x1, y1, x2, y2, kind) {
                    g.save()
                    g.strokeStyle = kind === "stop" ? Theme.crit : kind === "idle" ? Theme.text4 : Theme.ser6
                    g.globalAlpha = kind === "stop" ? 0.7 : kind === "idle" ? 1 : 0.85
                    g.lineWidth = 1.2
                    g.setLineDash(kind === "stop" ? [6, 4] : kind === "idle" ? [4, 4] : [])
                    g.beginPath(); g.moveTo(x1, y1); g.bezierCurveTo((x1 + x2) / 2, y1, (x1 + x2) / 2, y2, x2, y2); g.stroke()
                    g.restore()
                }
                function box(bx, by, w, h, kind, round) {
                    g.save()
                    g.beginPath()
                    var r = round ? h / 2 : 5, x = bx + 0.5, y = by - h / 2 + 0.5, ww = w - 1, hh = h - 1
                    g.moveTo(x + r, y); g.arcTo(x + ww, y, x + ww, y + hh, r); g.arcTo(x + ww, y + hh, x, y + hh, r); g.arcTo(x, y + hh, x, y, r); g.arcTo(x, y, x + ww, y, r); g.closePath()
                    g.fillStyle = kind === "wait" ? "transparent" : round ? Theme.surface2 : Theme.surface
                    if (kind !== "wait") g.fill()
                    g.strokeStyle = kind === "stop" || kind === "held" ? Theme.crit : Theme.borderStrong
                    g.lineWidth = kind === "held" ? 1.5 : 1
                    g.setLineDash(kind === "stop" || kind === "wait" ? [5, 4] : [])
                    g.stroke()
                    g.restore()
                }
                var ns = root.srcs.length, nd = root.dests.length
                for (var k = 0; k < ns; k++) line(root.nw, root.ys(k, ns), root.firstX, root.stages.length ? mid : root.ys(0, nd), root.srcs[k].gone ? "stop" : root.wait ? "idle" : "")
                for (var i = 0; i + 1 < root.stages.length; i++) line(root.stX(i) + root.sw, mid, root.stX(i + 1), mid, root.wait ? "idle" : "")
                if (root.stages.length) for (k = 0; k < nd; k++) line(root.lastX, mid, root.dx, root.ys(k, nd), root.dests[k].ask || root.wait ? "idle" : root.dests[k].bad ? "stop" : "")
                for (k = 0; k < ns; k++) box(0, root.ys(k, ns), root.nw, root.nh, root.srcs[k].gone ? "stop" : root.srcs[k].empty ? "wait" : "", false)
                for (i = 0; i < root.stages.length; i++) box(root.stX(i), mid, root.sw, root.sh, "", true)
                for (k = 0; k < nd; k++) box(root.dx, root.ys(k, nd), root.nw, root.nh, root.dests[k].ask || root.dests[k].empty ? "wait" : root.dests[k].bad ? "stop" : "", false)
            }
        }
        Connections { target: Theme; function onDarkChanged() { cv.requestPaint() } }
        // the words in the boxes
        component Label: Txt {
            property string a: ""
            property string b: ""
            property bool m: true
            property real cx: 0
            property real cy: 0
            property real w: 176
            x: cx - w / 2 + 6; y: cy - height / 2 + 1
            width: w - 12
            horizontalAlignment: Text.AlignHCenter
            mono: m
            textFormat: Text.StyledText
            color: Theme.text2
            FontMetrics { id: lm; font: lb.font }
            id: lb
            readonly property string bFit: b ? Theme.fitPath(b, lm, Math.max(40, width - lm.advanceWidth(a + " "))) : ""
            text: a + (b ? "<font color='" + Theme.text3 + "'> " + bFit + "</font>" : "")
            Tip { over: lb; text: lb.bFit !== lb.b ? lb.a + " " + lb.b : "" }
        }
        Repeater { model: root.srcs; delegate: Label { required property var modelData; required property int index; cx: root.nw / 2; cy: root.ys(index, root.srcs.length); a: modelData.host || ""; b: modelData.gone ? "moved away" : modelData.path || "" } }
        Repeater { model: root.stages; delegate: Label { required property var modelData; required property int index; m: false; w: root.sw; cx: root.stX(index) + root.sw / 2; cy: root.gH / 2; a: modelData.op || ""; b: "" } }
        Repeater { model: root.dests; delegate: Label { required property var modelData; required property int index; cx: root.dx + root.nw / 2; cy: root.ys(index, root.dests.length)
                                                         a: modelData.ask ? (modelData.host || "Someone") : modelData.host || ""; b: modelData.ask ? "picks a folder" : modelData.path || "" } }
    }
    onWidthChanged: cv.requestPaint()
    onSrcsChanged: cv.requestPaint()
    onDestsChanged: cv.requestPaint()
    onStagesChanged: cv.requestPaint()
}
