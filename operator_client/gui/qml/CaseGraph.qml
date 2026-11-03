import QtQuick
import "."

// A CASE AS A PICTURE (the concept's DetGraph): left to right in the order things happened, one lane per stage (where it
// began, where it was put, packed, taken out, the traces) and a lane beside it for a rename or copy within a stage, so a
// path reads as a straight line and never doubles back. A node sits on the row of what it came from. Boxes are 196 x 54,
// 96 apart, their edge in the colour of their kind; each connection carries its verb and the number of its step in the
// story. The Engine sends nodes and edges; this lays them out. Wider than its box, it pans (the page's Flickable).
Item {
    id: root
    objectName: "caseGraph"
    property var graph: ({ nodes: [], edges: [] })
    property var story: []
    readonly property var colNames: ["Where it began", "Where it was put", "Packed", "Taken out", "Traces"]
    readonly property var nodes: graph && graph.nodes ? graph.nodes : []
    readonly property var edges: graph && graph.edges ? graph.edges : []
    readonly property real nw: 196
    readonly property real gap: 96
    readonly property real nh: 54
    readonly property real rh: 78
    readonly property real top0: 36
    readonly property var lay: {
        var by = {}, lane = {}, preds = {}, row = {}
        nodes.forEach(function (n) { by[n.id] = n; lane[n.id] = n.col * 2 })
        edges.forEach(function (e) { var a = by[e.from], b = by[e.to]; if (a && b && a.col === b.col) lane[b.id] = b.col * 2 + 1; (preds[e.to] = preds[e.to] || []).push(e.from) })
        var lanes = Object.keys(lane).map(function (k) { return lane[k] }).filter(function (l, i, a) { return a.indexOf(l) === i }).sort(function (x, y) { return x - y })
        var li = {}; lanes.forEach(function (l, i) { li[l] = i })
        lanes.forEach(function (l) {
            var xs = nodes.filter(function (n) { return lane[n.id] === l }), taken = {}
            function want(n) { var r = (preds[n.id] || []).map(function (q) { return row[q] }).filter(function (v) { return v !== undefined }); return r.length ? Math.min.apply(null, r) : null }
            function put(n, r) { while (taken[r]) r++; taken[r] = true; row[n.id] = r }
            xs.filter(function (n) { return want(n) !== null }).sort(function (a, b) { return want(a) - want(b) }).forEach(function (n) { put(n, want(n)) })
            xs.filter(function (n) { return want(n) === null }).forEach(function (n) { put(n, 0) })
        })
        var at = {}, maxRow = 0
        nodes.forEach(function (n) { at[n.id] = { x: li[lane[n.id]] * (nw + gap) + 4, y: top0 + row[n.id] * rh, w: nw, h: nh }; maxRow = Math.max(maxRow, row[n.id]) })
        return { at: at, lanes: lanes, li: li, w: lanes.length * (nw + gap) - gap + 8, h: top0 + (maxRow + 1) * rh }
    }
    // which line of the story an edge is: its verb and one of its ends named on the same line, each line used once
    readonly property var steps: {
        var by = {}, used = {}, out = {}
        nodes.forEach(function (n) { by[n.id] = n })
        edges.forEach(function (e, k) {
            var a = by[e.from], b = by[e.to]; if (!a || !b) return
            var keys = [b.label, a.label, b.label.split(" in ")[0]].map(function (x) { return String(x).toLowerCase() }), verbs = e.verb === "packed" ? ["created", "packed"] : [e.verb]
            for (var j = 0; j < (story || []).length; j++) {
                var t = String(story[j]).toLowerCase()
                if (!used[j] && verbs.some(function (v) { return t.indexOf(v) >= 0 }) && keys.some(function (x) { return t.indexOf(x) >= 0 })) { used[j] = true; out[k] = j + 1; break }
            }
        })
        return out
    }
    function toneOf(kind) { return kind === "drive" ? Theme.crit : kind === "archive" ? Theme.med : kind === "staging" ? Theme.ser6 : kind === "system" ? Theme.ser5 : kind === "trace" ? Theme.text4 : Theme.text3 }
    function subOf(n) {
        var m = /^(f|dir):(.+)$/.exec(n.id || ""), w = ""
        if (m) {
            var segs = m[2].replace(/\//g, "\\").replace(/^\\+/, "").split("\\").filter(function (s) { return s })
            var root0 = segs.length ? segs[0].toUpperCase() : "", rest = segs.slice(1), dirs = m[1] === "f" ? rest.slice(0, -1) : rest, keep = m[1] === "f" ? 1 : 2
            dirs = dirs.map(function (d) { return d.charAt(0).toUpperCase() + d.slice(1) })
            w = !dirs.length ? root0 + "\\" : dirs.length <= keep ? root0 + "\\" + dirs.join("\\") : root0 + "\\…\\" + dirs.slice(-keep).join("\\")
        }
        return [w].concat((n.badges || []).map(function (b) { return b === "deleted" ? "deleted after" : b })).filter(function (s) { return s }).join(" · ")
    }
    implicitWidth: Math.max(lay.w, 100)
    implicitHeight: Math.max(120, lay.h)
    width: implicitWidth
    height: implicitHeight

    // the lane headings, once per stage
    Repeater {
        model: root.lay.lanes
        Txt {
            required property int modelData
            visible: modelData % 2 === 0 || root.lay.lanes.indexOf(modelData - 1) < 0
            x: root.lay.li[modelData] * (root.nw + root.gap) + 6; y: 2
            text: (root.colNames[Math.floor(modelData / 2)] || "").toUpperCase(); color: Theme.text4; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 0.6; elide: Text.ElideNone
        }
    }
    Canvas {
        id: lines
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections { target: root; function onLayChanged() { lines.requestPaint() } function onStepsChanged() { lines.requestPaint() } }
        Connections { target: Theme; function onDarkChanged() { lines.requestPaint() } }
        onPaint: {
            var c = getContext("2d")
            c.reset()
            root.edges.forEach(function (e, i) {
                var a = root.lay.at[e.from], b = root.lay.at[e.to]
                if (!a || !b) return
                var x1 = a.x + a.w, y1 = a.y + a.h / 2, x2 = b.x, y2 = b.y + b.h / 2
                c.strokeStyle = Theme.text3; c.lineWidth = 1.4
                c.beginPath()
                if (x2 > x1) { var mx = (x1 + x2) / 2; c.moveTo(x1, y1); c.bezierCurveTo(mx, y1, mx, y2, x2 - 2, y2) }
                else { x1 = a.x + a.w / 2; y1 = a.y + a.h; x2 = b.x + b.w / 2; y2 = b.y; c.moveTo(x1, y1); c.bezierCurveTo(x1, y1 + 24, x2, y2 - 24, x2, y2 - 2) }
                c.stroke()
                // the arrow head, along the end of the line
                var horiz = b.x > a.x + a.w
                c.fillStyle = Theme.text3
                c.beginPath()
                if (horiz) { c.moveTo(x2, y2); c.lineTo(x2 - 7, y2 - 3.5); c.lineTo(x2 - 7, y2 + 3.5) } else { c.moveTo(x2, y2); c.lineTo(x2 - 3.5, y2 - 7); c.lineTo(x2 + 3.5, y2 - 7) }
                c.closePath(); c.fill()
                var cx = (x1 + x2) / 2, cy = (y1 + y2) / 2
                c.fillStyle = Theme.text2; c.font = "10.5px 'IBM Plex Sans'"; c.textAlign = "center"
                c.fillText(e.verb || "", cx, cy - 12)
                var n = root.steps[i]
                if (n) {
                    c.beginPath(); c.arc(cx, cy, 8, 0, 2 * Math.PI); c.fillStyle = Theme.surface; c.fill(); c.strokeStyle = Theme.text3; c.lineWidth = 1; c.stroke()
                    c.fillStyle = Theme.text; c.font = "600 9.5px 'IBM Plex Sans'"; c.fillText(String(n), cx, cy + 3.5)
                }
            })
        }
    }
    Repeater {
        model: root.nodes
        Rectangle {
            required property var modelData
            readonly property var p: root.lay.at[modelData.id]
            readonly property string sub: root.subOf(modelData)
            objectName: "node_" + modelData.id
            x: p ? p.x : 0; y: p ? p.y : 0; width: root.nw; height: root.nh
            radius: 7
            color: Theme.surface
            border.width: 1
            border.color: root.toneOf(modelData.kind)
            Txt { x: 14; y: parent.sub ? 24 - baselineOffset : 32 - baselineOffset; width: parent.width - 24; text: modelData.label; font.pixelSize: 12; font.weight: Font.Medium
                  mono: modelData.kind === "file" || modelData.kind === "system" || modelData.kind === "archive" }
            Txt { visible: parent.sub !== ""; x: 14; y: 42 - baselineOffset; width: parent.width - 24; text: parent.sub; font.pixelSize: 11; color: Theme.text3 }
            Tip { text: modelData.label }
        }
    }
}
