import QtQuick
import "."

// MACHINE OCCUPANCY, TODAY: who was signed in to each machine, and when. One lane per machine, twelve
// a page; a working frame you can move, and a line naming any session started outside it. Machines
// someone else entered come first, then ones with their owner on, then empty ones.
Panel {
    id: root
    property var sessions: Fleet.sessionsToday
    title: "Machine occupancy, today"
    sub: "who was signed in to each machine, and when"

    property string view: "Working hours"
    property int from: 6
    property int to: 18
    property int page: 1
    property var hov: null

    readonly property var kinds: ({ native: [Theme.own, "Owner signed in"], traversal: [Theme.ser3, "Admin session"],
                                    you: [Theme.accent, "Your session"] })
    function kindOf(s) { return s.occupied_via === "traversal" && s.occupant_name === "You" ? "you" : (kinds[s.occupied_via] ? s.occupied_via : "traversal") }

    readonly property var lanes: {
        var by = {}, order = []
        for (var i = 0; i < Fleet.machines.length; i++) { by[Fleet.machines[i].host] = []; order.push(Fleet.machines[i].host) }
        for (var k = 0; k < sessions.length; k++) {
            var s = sessions[k]
            if (!by[s.hostname]) { by[s.hostname] = []; order.push(s.hostname) }
            by[s.hostname].push({ a: Time.hoursOf(s.entered_at), b: s.ended_at ? Time.hoursOf(s.ended_at) : Time.nowHours(), who: s.occupant_name, kind: root.kindOf(s) })
        }
        var w = function (h) { var bs = by[h]; return bs.some(function (x) { return x.kind !== "native" }) ? 0 : bs.length ? 1 : 2 }
        return order.map(function (h, i) { return { host: h, blocks: by[h], i: i } })
                    .sort(function (x, y) { return w(x.host) - w(y.host) || x.i - y.i })
    }
    readonly property int pages: Math.max(1, Math.ceil(lanes.length / 12))
    readonly property var shown: lanes.slice((Math.min(page, pages) - 1) * 12, Math.min(page, pages) * 12)
    readonly property bool full: view === "24 hours"
    readonly property real ha: full ? 0 : from
    readonly property real hb: full ? 24 : to
    function outside(bk) { return bk.a < root.from || bk.a >= root.to }
    readonly property var hidden: {
        if (full) return []
        var out = []
        for (var i = 0; i < lanes.length; i++)
            for (var k = 0; k < lanes[i].blocks.length; k++) {
                var bk = lanes[i].blocks[k]
                if (bk.b <= ha || bk.a >= hb) out.push({ host: lanes[i].host, bk: bk })
            }
        return out
    }
    readonly property var hours: {
        var out = []; for (var h = 0; h <= 24; h++) out.push({ value: h, label: Time.pad(h) + ":00" }); return out
    }

    extra: [
        Pager { compact: true; current: root.page; pages: root.pages; total: root.lanes.length; size: 12; what: "machines"; onGo: function (p) { root.page = p } },
        Txt { text: "Working hours"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter },
        Select { width: 82; small: true; options: root.hours.filter(function (h) { return h.value < root.to }); value: root.from; onPicked: function (v) { root.from = v } },
        Txt { text: "to"; color: Theme.text3; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter },
        Select { width: 82; small: true; options: root.hours.filter(function (h) { return h.value > root.from }); value: root.to; onPicked: function (v) { root.to = v } },
        Segmented { options: ["Working hours", "24 hours"]; value: root.view; onPicked: function (v) { root.view = v } }
    ]

    Column {
        width: parent.width
        spacing: 10
        Empty { visible: root.lanes.length === 0; width: parent.width; h: 140; icon: "login"; title: "No machines yet"; text: "Each machine gets a row here: who was signed in, and when." }

        Item {
            id: chart
            visible: root.lanes.length > 0
            width: parent.width
            readonly property int lw: 104
            readonly property int rh: 24
            readonly property real pw: width - lw - 10
            height: (root.pages > 1 ? 12 : root.shown.length) * rh + 26
            function xAt(t) { return lw + ((Math.max(root.ha, Math.min(root.hb, t)) - root.ha) / (root.hb - root.ha)) * pw }

            Canvas {
                id: cv
                anchors.fill: parent
                Connections { target: root; function onShownChanged() { cv.requestPaint() } function onHaChanged() { cv.requestPaint() } function onHbChanged() { cv.requestPaint() } function onFromChanged() { cv.requestPaint() } function onToChanged() { cv.requestPaint() } }
                Connections { target: Theme; function onDarkChanged() { cv.requestPaint() } }
                onWidthChanged: requestPaint()
                onPaint: {
                    var c = getContext("2d"); c.reset()
                    var n = root.shown.length, rh = chart.rh, H = chart.height
                    if (root.full) {
                        c.globalAlpha = 0.7; c.fillStyle = Theme.surface3
                        c.fillRect(chart.xAt(0), 0, chart.xAt(root.from) - chart.xAt(0), n * rh)
                        c.fillRect(chart.xAt(root.to), 0, chart.xAt(24) - chart.xAt(root.to), n * rh)
                        c.globalAlpha = 1
                    }
                    var span = root.hb - root.ha, step = span > 14 ? 3 : span > 8 ? 2 : 1
                    c.font = "10px '" + Theme.mono + "'"
                    for (var t = Math.ceil(root.ha / step) * step; t <= root.hb; t += step) {
                        c.strokeStyle = Theme.grid; c.beginPath(); c.moveTo(chart.xAt(t) + 0.5, 0); c.lineTo(chart.xAt(t) + 0.5, n * rh); c.stroke()
                        c.fillStyle = Theme.text3
                        c.textAlign = t === root.hb ? "right" : t === root.ha ? "left" : "center"
                        c.fillText(Time.pad(t % 24) + ":00", chart.xAt(t), H - 8)
                    }
                    c.textAlign = "left"
                    for (var i = 0; i < n; i++) {
                        var l = root.shown[i]
                        c.fillStyle = Theme.text2; c.font = "12px '" + Theme.mono + "'"
                        c.fillText(l.host.length > 13 ? l.host.slice(0, 6) + "…" + l.host.slice(-5) : l.host, 0, i * rh + 16)
                        c.strokeStyle = Theme.grid; c.beginPath(); c.moveTo(chart.lw, i * rh + rh + 0.5); c.lineTo(chart.width - 10, i * rh + rh + 0.5); c.stroke()
                        for (var k = 0; k < l.blocks.length; k++) {
                            var bk = l.blocks[k]
                            if (bk.b <= root.ha || bk.a >= root.hb) continue
                            var x0 = chart.xAt(bk.a), x1 = chart.xAt(bk.b)
                            c.fillStyle = root.kinds[bk.kind][0]
                            c.fillRect(x0, i * rh + 6, Math.max(3, x1 - x0), rh - 12)
                            if (bk.kind !== "native" && root.outside(bk)) {
                                c.strokeStyle = Theme.med; c.lineWidth = 2; c.strokeRect(x0, i * rh + 6, Math.max(3, x1 - x0), rh - 12); c.lineWidth = 1
                                c.fillStyle = Theme.med; c.font = "11px '" + Theme.sans + "'"
                                c.fillText(bk.who + " · " + Time.pad(Math.floor(bk.a)) + ":" + Time.pad(Math.round((bk.a % 1) * 60)) + " · outside working hours", Math.min(x1 + 6, chart.width - 230), i * rh + 16)
                            }
                        }
                    }
                    var nowH = Time.nowHours()
                    if (nowH > root.ha && nowH < root.hb) { c.strokeStyle = Theme.crit; c.lineWidth = 1.25; c.beginPath(); c.moveTo(chart.xAt(nowH), 0); c.lineTo(chart.xAt(nowH), n * rh); c.stroke() }
                }
            }
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                onPositionChanged: function (m) {
                    var i = Math.floor(m.y / chart.rh), hit = null
                    if (i >= 0 && i < root.shown.length) {
                        var t = root.ha + ((m.x - chart.lw) / chart.pw) * (root.hb - root.ha)
                        root.shown[i].blocks.forEach(function (bk) { if (t >= bk.a && t <= bk.b) hit = { host: root.shown[i].host, bk: bk, x: m.x, y: i * chart.rh } })
                    }
                    root.hov = hit
                }
                onExited: root.hov = null
            }
            Rectangle {
                visible: root.hov !== null
                x: root.hov ? Math.min(root.hov.x, chart.width - width) : 0
                y: root.hov ? root.hov.y + chart.rh : 0
                width: 240
                height: hc.height + 14
                radius: 5
                color: Theme.surface
                border.width: 1
                border.color: Theme.borderStrong
                z: 5
                Column {
                    id: hc
                    x: 9; y: 7
                    width: parent.width - 18
                    spacing: 2
                    readonly property var h: root.hov
                    function hm(x) { return Time.pad(Math.floor(x)) + ":" + Time.pad(Math.round((x % 1) * 60) % 60) }
                    Txt { text: hc.h ? hc.h.host + " · " + hc.hm(hc.h.bk.a) + " – " + (hc.h.bk.b >= Time.nowHours() - 0.01 ? "now" : hc.hm(hc.h.bk.b)) : ""; mono: true; color: Theme.text3; font.pixelSize: 11 }
                    Txt { textFormat: Text.RichText; text: hc.h ? "<span style='font-weight:500'>" + hc.h.bk.who + "</span> <span style='color:" + Theme.text3 + "'>" + root.kinds[hc.h.bk.kind][1] + " · " + Time.dur(hc.h.bk.b - hc.h.bk.a) + "</span>" : "" }
                    Txt { visible: hc.h !== null && hc.h.bk.kind !== "native" && root.outside(hc.h.bk); text: "Started outside working hours"; color: Theme.med }
                }
            }
        }

        Rectangle {
            visible: root.hidden.length > 0
            width: parent.width
            height: 40
            radius: 5
            color: Theme.alpha(Theme.med, 0.10)
            Row {
                x: 10
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Icon { name: "eyeoff"; size: 14; color: Theme.med; anchors.verticalCenter: parent.verticalCenter }
                Txt {
                    anchors.verticalCenter: parent.verticalCenter
                    width: root.width - 220
                    textFormat: Text.RichText
                    text: "<b>" + root.hidden.length + " session" + (root.hidden.length === 1 ? "" : "s") + " outside this view:</b> <span style='color:" + Theme.text2 + "'>"
                          + root.hidden.slice(0, 3).map(function (x) { return x.bk.who + " on " + x.host + " at " + Time.pad(Math.floor(x.bk.a)) + ":" + Time.pad(Math.round((x.bk.a % 1) * 60)) }).join(", ")
                          + (root.hidden.length > 3 ? ", and " + (root.hidden.length - 3) + " more" : "") + "</span>"
                }
            }
            Btn { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; small: true; text: "Show 24 hours"; onClicked: root.view = "24 hours" }
        }

        Row {
            visible: root.lanes.length > 0
            spacing: 14
            Repeater {
                model: ["native", "traversal", "you"]
                Row {
                    required property var modelData
                    spacing: 6
                    Rectangle { width: 10; height: 10; radius: 2; color: root.kinds[modelData][0]; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: root.kinds[modelData][1]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                }
            }
            Row {
                visible: root.full
                spacing: 6
                Rectangle { width: 10; height: 10; radius: 2; color: Theme.surface3; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: "Outside " + Time.pad(root.from) + ":00–" + Time.pad(root.to) + ":00"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
            }
        }
    }
}
