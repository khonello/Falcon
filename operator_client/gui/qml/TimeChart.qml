import QtQuick
import "."

// A TIME SERIES WITH REAL AXES: gridlines, an optional threshold (dashed red), events marked as
// diamonds, a shaded area under the first series, and a crosshair whose tooltip reads every series.
// series: [{name, c, pts: [[ms, value | null], ...]}] over the top bar's range (or `hours`).
Item {
    id: root
    property var series: []
    property real hours: Time.rangeHours(Nav.range)
    property string unit: ""
    property real yMax: 0
    property var threshold: null
    property var marks: []                   // [{t (ms), label, c}]
    implicitHeight: 168

    readonly property real b: Time.now
    readonly property real a: b - hours * 3600000
    readonly property real mx: {
        if (yMax) return yMax
        var m = 1
        for (var i = 0; i < series.length; i++)
            for (var k = 0; k < series[i].pts.length; k++) if (series[i].pts[k][1] !== null && series[i].pts[k][1] > m) m = series[i].pts[k][1]
        var p = Math.pow(10, Math.floor(Math.log(m) / Math.LN10)), r = m / p
        return (r <= 1 ? 1 : r <= 2 ? 2 : r <= 5 ? 5 : 10) * p
    }
    readonly property int pl: 40
    readonly property int pr: 10
    readonly property int pt: 10
    readonly property int pb: 22
    readonly property real pw: Math.max(10, width - pl - pr)
    readonly property real ph: height - pt - pb
    function xAt(t) { return pl + ((t - a) / (b - a)) * pw }
    function yAt(v) { return pt + ph - (Math.min(v, mx) / mx) * ph }
    property real hov: -1

    function fmtV(v) { return (v >= 100 ? v.toFixed(0) : v.toFixed(1)) + unit }
    function valueAt(s, t) {
        var best = null, d = Infinity
        for (var i = 0; i < s.pts.length; i++) { var dd = Math.abs(s.pts[i][0] - t); if (dd < d) { d = dd; best = s.pts[i][1] } }
        return d < (b - a) / 40 ? best : null
    }

    onSeriesChanged: cv.requestPaint()
    onWidthChanged: cv.requestPaint()
    onHovChanged: cv.requestPaint()
    Connections { target: Theme; function onDarkChanged() { cv.requestPaint() } }

    Canvas {
        id: cv
        anchors.fill: parent
        onPaint: {
            var c = getContext("2d"); c.reset()
            c.font = "10px '" + Theme.mono + "'"
            c.textAlign = "right"
            ;[0, root.mx / 2, root.mx].forEach(function (v) {
                c.strokeStyle = Theme.grid; c.beginPath(); c.moveTo(root.pl, root.yAt(v) + 0.5); c.lineTo(root.width - root.pr, root.yAt(v) + 0.5); c.stroke()
                c.fillStyle = Theme.text3; c.fillText(v >= 1000 ? (v / 1000).toFixed(1) + "k" : String(Math.round(v)), root.pl - 6, root.yAt(v) + 4)
            })
            var step = root.hours <= 1 ? 10 / 60 : root.hours <= 6 ? 1 : root.hours <= 24 ? 3 : 24
            var stepMs = step * 3600000
            c.textAlign = "center"
            for (var t = Math.ceil(root.a / stepMs) * stepMs; t <= root.b; t += stepMs) {
                c.strokeStyle = Theme.grid; c.beginPath(); c.moveTo(root.xAt(t) + 0.5, root.pt); c.lineTo(root.xAt(t) + 0.5, root.pt + root.ph); c.stroke()
                c.fillStyle = Theme.text3
                c.fillText(root.hours > 24 ? Time.days[new Date(t).getDay()] : Time.hhmm(t), root.xAt(t), root.height - 6)
            }
            if (root.threshold !== null) {
                c.strokeStyle = Theme.crit; c.setLineDash([4, 3]); c.beginPath()
                c.moveTo(root.pl, root.yAt(root.threshold)); c.lineTo(root.width - root.pr, root.yAt(root.threshold)); c.stroke(); c.setLineDash([])
                c.fillStyle = Theme.crit; c.textAlign = "right"; c.font = "10px '" + Theme.sans + "'"
                c.fillText("threshold " + root.threshold + root.unit, root.width - root.pr - 2, root.yAt(root.threshold) - 4)
            }
            for (var s = 0; s < root.series.length; s++) {
                var se = root.series[s], pen = false
                c.strokeStyle = se.c; c.lineWidth = 1.5; c.beginPath()
                for (var k = 0; k < se.pts.length; k++) {
                    var p = se.pts[k]
                    if (p[1] === null || p[0] < root.a) { pen = false; continue }
                    if (pen) c.lineTo(root.xAt(p[0]), root.yAt(p[1])); else c.moveTo(root.xAt(p[0]), root.yAt(p[1]))
                    pen = true
                }
                c.stroke()
                if (s === 0 && se.pts.length > 1) {
                    c.globalAlpha = 0.12; c.fillStyle = se.c; c.beginPath()
                    var first = true
                    for (var j = 0; j < se.pts.length; j++) {
                        var q = se.pts[j]; if (q[1] === null || q[0] < root.a) continue
                        if (first) { c.moveTo(root.xAt(q[0]), root.yAt(0)); first = false }
                        c.lineTo(root.xAt(q[0]), root.yAt(q[1]))
                    }
                    var last = se.pts[se.pts.length - 1]
                    c.lineTo(root.xAt(last[0]), root.yAt(0)); c.closePath(); c.fill(); c.globalAlpha = 1
                }
            }
            for (var m = 0; m < root.marks.length; m++) {
                var mk = root.marks[m]; if (mk.t < root.a) continue
                c.strokeStyle = mk.c; c.setLineDash([2, 3]); c.beginPath(); c.moveTo(root.xAt(mk.t), root.pt); c.lineTo(root.xAt(mk.t), root.pt + root.ph); c.stroke(); c.setLineDash([])
                c.fillStyle = mk.c; c.save(); c.translate(root.xAt(mk.t), root.pt + 3); c.rotate(Math.PI / 4); c.fillRect(-4, -4, 8, 8); c.restore()
            }
            if (root.hov >= 0) {
                c.strokeStyle = Theme.text3; c.beginPath(); c.moveTo(root.xAt(root.hov), root.pt); c.lineTo(root.xAt(root.hov), root.pt + root.ph); c.stroke()
            }
        }
    }
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        onPositionChanged: function (m) { root.hov = m.x < root.pl || m.x > root.pl + root.pw ? -1 : root.a + ((m.x - root.pl) / root.pw) * (root.b - root.a) }
        onExited: root.hov = -1
    }
    Rectangle {
        visible: root.hov >= 0
        x: Math.min(root.xAt(root.hov) + 12, root.width - width)
        y: 6
        width: 170
        height: tc.height + 14
        radius: 5
        color: Theme.surface
        border.width: 1
        border.color: Theme.borderStrong
        Column {
            id: tc
            x: 9; y: 7
            width: parent.width - 18
            spacing: 2
            Txt { text: root.hours > 24 ? Time.days[new Date(root.hov).getDay()] + " " + Time.hhmm(root.hov) : Time.hhmm(root.hov); mono: true; color: Theme.text3; font.pixelSize: 11 }
            Repeater {
                model: root.series
                Row {
                    required property var modelData
                    width: tc.width
                    spacing: 8
                    Rectangle { width: 10; height: 3; radius: 2; color: modelData.c; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: modelData.name; color: Theme.text2; font.pixelSize: 12; width: parent.width - 80 }
                    Txt { readonly property var v: root.valueAt(modelData, root.hov); text: v === null ? "no data" : root.fmtV(v); mono: true; font.weight: Font.DemiBold; font.pixelSize: 12; elide: Text.ElideNone }
                }
            }
        }
    }
}
