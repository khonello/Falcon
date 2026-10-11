import QtQuick
import "."

// MACHINES IN USE TODAY, one lane per department: how many of its machines had someone on them, hour by
// hour, as a grey shape stepping at the real times; amber where an hour is unusual (someone on a
// machine at night); a verdict on the right. Built from the day's sessions.
Item {
    id: root
    property var rows: []                 // [{key, label, hosts: [host], color?}]
    property int lane: 56
    property int slots: 0
    readonly property int lw: 104
    readonly property int rw: 136
    readonly property int gap: 10
    implicitHeight: Math.max(rows.length, slots) * (lane + gap) + 22 + legend.height + 8
    readonly property real nowH: Time.nowHours()
    readonly property real pw: Math.max(100, width - lw - rw)
    function xAt(h) { return lw + (Math.max(0, Math.min(nowH, h)) / Math.max(1, nowH)) * pw }

    // per lane: the count at each moment, and the hours flagged
    readonly property var profs: rows.map(function (r) {
        var ss = Fleet.sessionsToday.filter(function (s) { return r.hosts.indexOf(s.hostname) >= 0 })
        var moves = []
        ss.forEach(function (s) {
            var a = Math.max(0, Time.hoursOf(s.entered_at)), b = s.ended_at ? Time.hoursOf(s.ended_at) : root.nowH
            if (b <= 0) return
            moves.push([a, 1]); if (s.ended_at && b < root.nowH) moves.push([b, -1])
        })
        moves.sort(function (x, y) { return x[0] - y[0] })
        var steps = [[0, 0]], n = 0
        moves.forEach(function (m) { n = Math.max(0, n + m[1]); steps.push([m[0], n]) })
        var night = ss.filter(function (s) { var h = Time.hoursOf(s.entered_at); return s.occupied_via !== "native" && h >= 0 && (h < 6 || h >= 18) })
        return { steps: steps, total: r.hosts.length, night: night,
                 verdict: !r.hosts.length ? ["No machines", Theme.text4] : night.length ? ["Activity at night", Theme.med] : ["As usual", Theme.text3] }
    })
    onProfsChanged: cv.requestPaint()
    onWidthChanged: cv.requestPaint()
    Connections { target: Theme; function onDarkChanged() { cv.requestPaint() } }

    Canvas {
        id: cv
        width: parent.width
        height: Math.max(root.rows.length, root.slots) * (root.lane + root.gap) + 22
        onPaint: {
            var c = getContext("2d"); c.reset()
            root.rows.forEach(function (r, i) {
                var p = root.profs[i], y0 = i * (root.lane + root.gap), sc = (root.lane - 14) / Math.max(1, p.total)
                c.fillStyle = Theme.surface2; c.fillRect(root.lw, y0, root.pw, root.lane)
                c.globalAlpha = 0.55; c.fillStyle = Theme.surface3; c.fillRect(root.xAt(0), y0, root.xAt(Math.min(6, root.nowH)) - root.xAt(0), root.lane); c.globalAlpha = 1
                p.night.forEach(function (s) { var h = Math.floor(Time.hoursOf(s.entered_at)); c.globalAlpha = 0.16; c.fillStyle = Theme.med; c.fillRect(root.xAt(h), y0, root.xAt(h + 1) - root.xAt(h), root.lane); c.globalAlpha = 1 })
                c.font = "500 12px '" + Theme.sans + "'"; c.fillStyle = r.color || Theme.text; c.textAlign = "left"
                c.fillText(r.label.length > 14 ? r.label.slice(0, 13) + "…" : r.label, 0, y0 + root.lane / 2 + 4)
                c.beginPath(); c.moveTo(root.xAt(0), y0 + root.lane - 4)
                for (var k = 0; k < p.steps.length; k++) {
                    var st = p.steps[k], nx = k + 1 < p.steps.length ? p.steps[k + 1][0] : root.nowH
                    c.lineTo(root.xAt(st[0]), y0 + root.lane - 4 - st[1] * sc); c.lineTo(root.xAt(nx), y0 + root.lane - 4 - st[1] * sc)
                }
                c.lineTo(root.xAt(root.nowH), y0 + root.lane - 4); c.closePath()
                c.globalAlpha = 0.32; c.fillStyle = Theme.ser6; c.fill(); c.globalAlpha = 1
                c.strokeStyle = Theme.ser6; c.lineWidth = 1.5; c.stroke()
                p.night.forEach(function (s) { var x = root.xAt(Time.hoursOf(s.entered_at)); c.strokeStyle = Theme.med; c.lineWidth = 1.25; c.beginPath(); c.moveTo(x, y0 + 9); c.lineTo(x, y0 + root.lane - 4); c.stroke()
                                             c.fillStyle = Theme.med; c.beginPath(); c.arc(x, y0 + 8, 5, 0, Math.PI * 2); c.fill() })
                c.font = "12px '" + Theme.sans + "'"; c.fillStyle = p.verdict[1]; c.fillText(p.verdict[0], root.lw + root.pw + 14, y0 + root.lane / 2 + 4)
            })
            var H = cv.height
            c.font = "10px '" + Theme.mono + "'"; c.fillStyle = Theme.text3; c.textAlign = "center"
            for (var h = 0; h <= root.nowH; h += 2) c.fillText(Time.pad(h) + ":00", root.xAt(h), H - 6)
            c.textAlign = "end"; c.fillStyle = Theme.crit; c.fillText("now", root.xAt(root.nowH), H - 6)
        }
    }
    Row {
        id: legend
        anchors.top: cv.bottom
        anchors.topMargin: 8
        spacing: 14
        Repeater {
            model: [[Theme.alpha(Theme.ser6, 0.45), "machines in use today", 2], [Theme.alpha(Theme.med, 0.3), "unusual for that hour", 2], [Theme.med, "someone on a machine at night", 5], [Theme.surface3, "before 06:00", 2]]
            Row { required property var modelData; spacing: 6
                  Rectangle { width: 10; height: 10; radius: modelData[2]; color: modelData[0]; anchors.verticalCenter: parent.verticalCenter }
                  Txt { text: modelData[1]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
        }
    }
}
