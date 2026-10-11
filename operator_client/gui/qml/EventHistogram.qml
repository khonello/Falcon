import QtQuick
import "."

// EVENTS PER INTERVAL, stacked by kind, with a drag across it to narrow what is listed beside it.
// entries: [{t (ms), kind}] · range: 1h | 6h | 24h | 7d · brush: [from, to] (ms) or null.
Item {
    id: root
    property var entries: []
    property string range: "24h"
    property var kinds: Kinds.keys
    property var brush: null
    property bool brushable: true
    signal brushed(var b)
    implicitHeight: 150

    readonly property real now: Time.now
    readonly property var spec: range === "1h" ? { h: 1, bins: 12, step: 10 / 60 }
                              : range === "6h" ? { h: 6, bins: 36, step: 1 }
                              : range === "7d" ? { h: 168, bins: 84, step: 24 } : { h: 24, bins: 48, step: 3 }
    readonly property real a: now - spec.h * 3600000
    readonly property real bw: spec.h * 3600000 / spec.bins
    readonly property var bins: {
        var b = [], n = spec.bins
        for (var i = 0; i < n; i++) { var o = {}; for (var k = 0; k < Kinds.keys.length; k++) o[Kinds.keys[k]] = 0; b.push(o) }
        for (var j = 0; j < entries.length; j++) {
            var e = entries[j]
            if (e.t === null || e.t < a || kinds.indexOf(e.kind) < 0) continue
            var x = Math.min(n - 1, Math.floor((e.t - a) / bw)); b[x][e.kind] += 1
        }
        return b
    }
    readonly property var totals: bins.map(function (o) { var s = 0; for (var k in o) s += o[k]; return s })
    readonly property real mx: niceMax(Math.max(4, Math.max.apply(null, totals.concat([0]))))
    function niceMax(v) { var p = Math.pow(10, Math.floor(Math.log(v) / Math.LN10)), m = v / p; return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p }

    readonly property int pl: 34
    readonly property int pr: 8
    readonly property int pt: 8
    readonly property int pb: 22
    readonly property real pw: width - pl - pr
    readonly property real ph: height - pt - pb
    readonly property real cw: pw / spec.bins
    property int hov: -1
    property var drag: null

    function binAt(x) { return Math.max(0, Math.min(spec.bins - 1, Math.floor((x - pl) / cw))) }
    readonly property var sel: drag ? [Math.min(drag[0], drag[1]), Math.max(drag[0], drag[1])]
                             : brush ? [Math.floor((brush[0] - a) / bw), Math.floor((brush[1] - a) / bw - 1e-6)] : null
    function tick(t) { var d = new Date(t); return range === "7d" ? Time.days[d.getDay()] : Time.hhmm(d) }

    onBinsChanged: cv.requestPaint()
    onSelChanged: cv.requestPaint()
    onHovChanged: cv.requestPaint()
    onWidthChanged: cv.requestPaint()
    Connections { target: Theme; function onDarkChanged() { cv.requestPaint() } }

    Canvas {
        id: cv
        anchors.fill: parent
        onPaint: {
            var c = getContext("2d"); c.reset()
            var yy = function (v) { return root.pt + root.ph - (v / root.mx) * root.ph }
            c.font = "10px '" + Theme.mono + "'"
            c.textAlign = "right"
            ;[0, root.mx / 2, root.mx].forEach(function (v) {
                c.strokeStyle = Theme.grid; c.beginPath(); c.moveTo(root.pl, yy(v) + 0.5); c.lineTo(root.width - root.pr, yy(v) + 0.5); c.stroke()
                c.fillStyle = Theme.text3; c.fillText(String(Math.round(v)), root.pl - 6, yy(v) + 4)
            })
            if (root.sel) {
                c.fillStyle = Theme.accentSoft; c.strokeStyle = Theme.accent
                c.fillRect(root.pl + root.sel[0] * root.cw, root.pt, (root.sel[1] - root.sel[0] + 1) * root.cw, root.ph)
                c.strokeRect(root.pl + root.sel[0] * root.cw + 0.5, root.pt + 0.5, (root.sel[1] - root.sel[0] + 1) * root.cw - 1, root.ph - 1)
            }
            for (var i = 0; i < root.bins.length; i++) {
                var acc = 0
                for (var k = 0; k < Kinds.keys.length; k++) {
                    var kk = Kinds.keys[k], v = root.bins[i][kk]
                    if (!v) continue
                    var y0 = yy(acc), y1 = yy(acc + v); acc += v
                    c.globalAlpha = root.hov < 0 || root.hov === i ? 1 : 0.55
                    c.fillStyle = Kinds.color(kk)
                    c.fillRect(root.pl + i * root.cw + 0.5, y1, Math.max(1, root.cw - 1.5), Math.max(0.5, y0 - y1))
                }
            }
            c.globalAlpha = 1
            c.textAlign = "center"; c.fillStyle = Theme.text3
            var stepMs = root.spec.step * 3600000, t0 = Math.ceil(root.a / stepMs) * stepMs
            for (var t = t0; t <= root.now; t += stepMs) {
                var x = root.pl + ((t - root.a) / (root.spec.h * 3600000)) * root.pw
                c.fillText(root.tick(t), x, root.height - 6)
            }
        }
    }
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.brushable ? Qt.CrossCursor : Qt.ArrowCursor
        onPositionChanged: function (m) { root.hov = root.binAt(m.x); if (root.drag) root.drag = [root.drag[0], root.binAt(m.x)] }
        onExited: root.hov = -1
        onPressed: function (m) { if (root.brushable) root.drag = [root.binAt(m.x), root.binAt(m.x)] }
        onReleased: {
            if (!root.drag) return
            var lo = Math.min(root.drag[0], root.drag[1]), hi = Math.max(root.drag[0], root.drag[1])
            root.drag = null
            if (lo === hi && root.brush) root.brushed(null)
            else root.brushed([root.a + lo * root.bw, root.a + (hi + 1) * root.bw])
        }
    }
    // the bin under the pointer, in words
    Rectangle {
        visible: root.hov >= 0 && !root.drag
        x: Math.min(root.pl + root.hov * root.cw + root.cw + 8, root.width - width)
        y: 4
        width: 190
        height: ttc.height + 14
        radius: 5
        color: Theme.surface
        border.width: 1
        border.color: Theme.borderStrong
        Column {
            id: ttc
            x: 9; y: 7
            width: parent.width - 18
            spacing: 2
            Txt {
                mono: true; color: Theme.text3; font.pixelSize: 11
                text: root.hov >= 0 ? (root.range === "7d" ? Time.days[new Date(root.a + root.hov * root.bw).getDay()] + " " : "")
                                     + Time.hhmm(root.a + root.hov * root.bw) + " – " + Time.hhmm(root.a + (root.hov + 1) * root.bw) : ""
            }
            Repeater {
                model: root.hov >= 0 ? Kinds.keys.filter(function (k) { return root.bins[root.hov][k] > 0 }) : []
                Row {
                    required property var modelData
                    width: ttc.width
                    spacing: 8
                    Rectangle { width: 10; height: 10; radius: 2; color: Kinds.color(modelData); anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: Kinds.words[modelData]; color: Theme.text2; font.pixelSize: 12; width: parent.width - 60 }
                    Txt { text: String(root.bins[root.hov][modelData]); mono: true; font.weight: Font.DemiBold; font.pixelSize: 12; elide: Text.ElideNone }
                }
            }
            Txt { visible: root.hov >= 0 && root.totals[root.hov] === 0; text: "No events"; color: Theme.text3; font.pixelSize: 12 }
        }
    }
}
