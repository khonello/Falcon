import QtQuick
import "."

// MACHINES IN USE TODAY, one lane per department (the concept's DayLanes): how many of its machines had
// someone on them, as a grey shape; amber where an hour is unusual (someone on a machine at night); pins
// where something needs someone (a restricted copy, red) or is unusual (a deviation, or an entry at night,
// amber); a verdict on the right. Hover for the count at that moment. Built from the day's sessions.
//
// A machine counts once however many sessions it has: its sessions are joined end to end, so a hand-over
// between people is not a gap, and an Admin entering a worker's machine is not a second machine. The count
// steps at the real times and is drawn as a running average over half an hour, so arrivals close together
// read as one rise instead of a staircase; the readout stays exact.
Item {
    id: root
    property var rows: []                 // [{key, label, hosts: [host], color?}]
    property int lane: 56
    property int slots: 0
    property bool report: false           // the concept's Report view: each lane's verdict and its pins, as text
    readonly property int lw: 104
    readonly property int rw: 136
    readonly property int gap: 10
    readonly property int chartH: Math.max(rows.length, slots) * (lane + gap) + 22
    implicitHeight: report ? rep.implicitHeight : chartH + legend.height + 8
    readonly property real nowH: Time.nowHours()
    readonly property real pw: Math.max(100, width - lw - rw)
    function xAt(h) { return lw + (Math.max(0, Math.min(nowH, h)) / Math.max(1, nowH)) * pw }
    function night(h) { return h < 6 || h >= 18 }
    property real hov: -1

    readonly property var profs: rows.map(function (r) {
        var hosts = r.hosts, inLane = function (h) { return hosts.indexOf(h) >= 0 }
        var ss = Fleet.sessionsToday.filter(function (s) { return inLane(s.hostname) })
        var VERB = { native: "signed in on", traversal: "entered" }
        var moves = []
        hosts.forEach(function (host) {
            var bl = ss.filter(function (s) { return s.hostname === host }).map(function (s) {
                return { a: Math.max(0, Time.hoursOf(s.entered_at)), b: s.ended_at ? Time.hoursOf(s.ended_at) : root.nowH, who: s.occupant_name || "Someone", via: s.occupied_via }
            }).filter(function (x) { return x.b > 0 }).sort(function (x, y) { return x.a - y.a })
            var cur = null
            function close() { if (cur && cur.to < root.nowH - 0.01) moves.push({ t: cur.to, d: -1, text: cur.last + " left " + host }) }
            bl.forEach(function (x) {
                if (cur && x.a - cur.to < 0.05) { cur.to = Math.max(cur.to, x.b); cur.last = x.who; return }
                close(); cur = { to: x.b, last: x.who }
                moves.push({ t: x.a, d: 1, text: x.who + " " + (VERB[x.via] || "signed in on") + " " + host })
            })
            close()
        })
        moves.sort(function (x, y) { return x.t - y.t })
        var steps = [{ t: 0, n: 0, text: "" }]
        moves.forEach(function (m) { steps.push({ t: m.t, n: Math.max(0, steps[steps.length - 1].n + m.d), text: m.text }) })
        // pins: a restricted copy (red), a deviation or an entry at night (amber), today only
        var pins = []
        Fleet.violations.forEach(function (v) {
            var m = Fleet.byPc[v.found_on_pc_id], host = m ? m.host : v.hostname, t = Time.hoursOf(v.detected_at)
            if (inLane(host) && t >= 0) pins.push({ t: t, c: Theme.crit, text: Time.hhmm(v.detected_at) + " · " + (m && m.user ? m.user : "Someone") + " · a copy of " + v.filename + " · " + host })
        })
        Fleet.deviations.forEach(function (d) {
            var m = Fleet.byPc[d.observed_pc_id], t = Time.hoursOf(d.detected_at)
            if (m && inLane(m.host) && t >= 0) pins.push({ t: t, c: Theme.med, text: Time.hhmm(d.detected_at) + " · " + Rules.devRecord(d).short + " · " + m.host })
        })
        ss.forEach(function (s) {
            var t = Time.hoursOf(s.entered_at)
            if (s.occupied_via !== "native" && t >= 0 && root.night(t))
                pins.push({ t: t, c: Theme.med, text: Time.hhmm(s.entered_at) + " · " + (s.occupant_name || "Someone") + " · entered outside working hours · " + s.hostname })
        })
        pins.sort(function (a, b) { return a.t - b.t })
        // an hour is unusual when someone was on a machine at night; the hour in progress is never judged
        var done = Math.floor(root.nowH), odd = []
        for (var h = 0; h < 24; h++) odd.push(h < done && root.night(h) && pins.some(function (p) { return p.c === Theme.med && p.t >= h && p.t < h + 1 && /outside working hours/.test(p.text) }))
        var atNight = odd.some(function (o) { return o }) || pins.some(function (p) { return /outside working hours/.test(p.text) })
        return { steps: steps, total: hosts.length, pins: pins, odd: odd,
                 verdict: !hosts.length ? ["No machines", Theme.text4] : atNight ? ["Activity at night", Theme.med] : ["As usual", Theme.text3] }
    })
    function stepAt(p, t) { var k = 0; while (k + 1 < p.steps.length && p.steps[k + 1].t <= t) k++; return p.steps[k] }
    // the running average over half an hour around t
    function mean(p, a, b) {
        var sum = 0, t = a, k = 0
        while (k + 1 < p.steps.length && p.steps[k + 1].t <= a) k++
        while (t < b) { var next = Math.min(b, k + 1 < p.steps.length ? p.steps[k + 1].t : b); sum += p.steps[k].n * (next - t); t = next; k++ }
        return sum / Math.max(1e-6, b - a)
    }
    onProfsChanged: cv.requestPaint()
    onWidthChanged: cv.requestPaint()
    onHovChanged: cv.requestPaint()
    Connections { target: Theme; function onDarkChanged() { cv.requestPaint() } }

    Canvas {
        id: cv
        visible: !root.report
        width: parent.width
        height: root.chartH
        onPaint: {
            var c = getContext("2d"); c.reset()
            root.rows.forEach(function (r, i) {
                var p = root.profs[i], y0 = i * (root.lane + root.gap), sc = (root.lane - 14) / Math.max(1, p.total)
                c.fillStyle = Theme.surface2; c.fillRect(root.lw, y0, root.pw, root.lane)
                c.globalAlpha = 0.55; c.fillStyle = Theme.surface3; c.fillRect(root.xAt(0), y0, root.xAt(Math.min(6, root.nowH)) - root.xAt(0), root.lane); c.globalAlpha = 1
                p.odd.forEach(function (o, h) { if (!o) return; c.globalAlpha = 0.16; c.fillStyle = Theme.med; c.fillRect(root.xAt(h), y0, root.xAt(h + 1) - root.xAt(h), root.lane); c.globalAlpha = 1 })
                c.font = "500 " + (root.lane > 40 ? "12.5" : "11.5") + "px '" + Theme.sans + "'"; c.fillStyle = r.color || Theme.text; c.textAlign = "left"
                c.fillText(r.label.length > 14 ? r.label.slice(0, 13) + "…" : r.label, 0, y0 + root.lane / 2 + 4)
                var base = y0 + root.lane - 4
                c.beginPath()
                for (var t = 0, k = 0; t <= root.nowH + 1e-9; t += 1 / 30, k++) {
                    var u = Math.min(t, root.nowH), a0 = Math.max(0, u - 0.25), b0 = Math.max(Math.min(root.nowH, u + 0.25), a0 + 1e-6)
                    var y = base - root.mean(p, a0, b0) * sc
                    if (k) c.lineTo(root.xAt(u), y); else c.moveTo(root.xAt(u), y)
                }
                c.strokeStyle = Theme.ser6; c.lineWidth = 1.5; c.lineJoin = "round"; c.stroke()
                c.lineTo(root.xAt(root.nowH), base); c.lineTo(root.xAt(0), base); c.closePath()
                c.globalAlpha = 0.32; c.fillStyle = Theme.ser6; c.fill(); c.globalAlpha = 1
                p.pins.forEach(function (pn) {
                    var x = root.xAt(pn.t)
                    c.strokeStyle = pn.c; c.lineWidth = 1.25; c.beginPath(); c.moveTo(x, y0 + 9); c.lineTo(x, base); c.stroke()
                    c.fillStyle = pn.c; c.strokeStyle = Theme.surface; c.lineWidth = 1.5; c.beginPath(); c.arc(x, y0 + 8, root.lane > 40 ? 5 : 4, 0, Math.PI * 2); c.fill(); c.stroke()
                })
                c.font = "12px '" + Theme.sans + "'"; c.fillStyle = p.verdict[1]; c.fillText(p.verdict[0], root.lw + root.pw + 14, y0 + root.lane / 2 + 4)
            })
            var H = cv.height
            c.font = "10.5px '" + Theme.mono + "'"; c.fillStyle = Theme.text3
            for (var h = 0; h <= root.nowH; h += 2) { c.textAlign = h === 0 ? "start" : "center"; c.fillText(Time.pad(h) + ":00", root.xAt(h), H - 6) }
            c.font = "600 10.5px '" + Theme.mono + "'"; c.textAlign = "end"; c.fillStyle = Theme.crit; c.fillText("now", root.xAt(root.nowH), H - 6)
            if (root.hov >= 0) { var hx = root.xAt(root.hov); c.strokeStyle = Theme.text3; c.lineWidth = 1; c.setLineDash([2, 3]); c.beginPath(); c.moveTo(hx, 0); c.lineTo(hx, H - 22); c.stroke(); c.setLineDash([]) }
        }
    }
    MouseArea {
        visible: !root.report
        width: cv.width; height: cv.height
        hoverEnabled: true
        onPositionChanged: function (m) { root.hov = m.x < root.lw || m.x > root.lw + root.pw ? -1 : (m.x - root.lw) / root.pw * root.nowH }
        onExited: root.hov = -1
    }
    // the readout: each lane's count at that moment, and what last changed it
    Rectangle {
        visible: !root.report && root.hov >= 0
        x: Math.min(root.xAt(Math.max(0, root.hov)) + 12, root.width - width - 4)
        y: 0
        width: 300
        height: tipCol.height + 14
        radius: 5
        color: Theme.surface
        border.width: 1
        border.color: Theme.borderStrong
        z: 5
        Column {
            id: tipCol
            x: 9; y: 7
            width: parent.width - 18
            spacing: 4
            Txt { text: Time.pad(Math.floor(Math.max(0, root.hov))) + ":" + Time.pad(Math.floor((Math.max(0, root.hov) % 1) * 60)); mono: true; color: Theme.text3; font.pixelSize: 11 }
            Repeater {
                model: root.hov >= 0 ? root.rows : []
                Row {
                    required property var modelData
                    required property int index
                    readonly property var st: root.stepAt(root.profs[index], root.hov)
                    spacing: 8
                    Txt { width: 80; text: modelData.label; color: Theme.text2; font.pixelSize: 12 }
                    Column {
                        width: tipCol.width - 88
                        Txt { textFormat: Text.StyledText; font.pixelSize: 12; width: parent.width
                              text: "<b>" + parent.parent.st.n + "</b><font color='" + Theme.text3 + "'> of " + root.profs[index].total + " in use</font>" }
                        Txt { visible: !!parent.parent.st.text; width: parent.width; color: Theme.text3; font.pixelSize: 11
                              text: "since " + Time.pad(Math.floor(parent.parent.st.t)) + ":" + Time.pad(Math.floor((parent.parent.st.t % 1) * 60)) + " · " + parent.parent.st.text }
                    }
                }
            }
        }
    }
    Row {
        id: legend
        visible: !root.report
        anchors.top: cv.bottom
        anchors.topMargin: 8
        spacing: 14
        Repeater {
            model: [[Theme.alpha(Theme.ser6, 0.45), "machines in use today", 2], [Theme.alpha(Theme.med, 0.3), "unusual for that hour", 2],
                    [Theme.crit, "needs someone", 5], [Theme.med, "unusual", 5], [Theme.surface3, "before 06:00", 2]]
            Row { required property var modelData; spacing: 6
                  Rectangle { width: 10; height: 10; radius: modelData[2]; color: modelData[0]; anchors.verticalCenter: parent.verticalCenter }
                  Txt { text: modelData[1]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
        }
    }
    // the Report view (the concept's DayReport): the lane, its verdict, and up to four of its pins
    Column {
        id: rep
        visible: root.report
        width: parent.width
        spacing: 10
        Repeater {
            model: root.report ? root.rows : []
            Column {
                required property var modelData
                required property int index
                readonly property var p: root.profs[index]
                width: rep.width
                spacing: 2
                Txt { width: parent.width; textFormat: Text.StyledText; font.pixelSize: 13
                      text: "<b>" + modelData.label + "</b> <font color='" + parent.p.verdict[1] + "'>· " + parent.p.verdict[0].toLowerCase() + "</font>" }
                Repeater {
                    model: parent.p.pins.slice(0, 4)
                    Row { required property var modelData; spacing: 8
                          Rectangle { width: 8; height: 8; radius: 2; color: modelData.c; anchors.verticalCenter: parent.verticalCenter }
                          Txt { text: modelData.text; font.pixelSize: 13; elide: Text.ElideNone } }
                }
                Txt { visible: parent.p.pins.length > 4; leftPadding: 16; text: "+" + (parent.p.pins.length - 4) + " more in the audit log"; color: Theme.text3; font.pixelSize: 12 }
            }
        }
    }
}
