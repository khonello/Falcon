import QtQuick
import "."

// The week as seven bars, one per day: how many deviations that day, the part still open in red and the
// part dealt with in grey. A click shows only that day in the list.
Item {
    id: root
    property var devs: []            // records from Rules.devRecord
    property var day: null           // 0 today, -1 yesterday ...
    signal pickDay(var k)
    implicitHeight: 190 + 30
    property int hov: -1

    readonly property var days: [-6, -5, -4, -3, -2, -1, 0].map(function (k) {
        var ds = devs.filter(function (d) { return Math.round((Time.startOfDay(Time.ms(d.at)) - Time.startOfDay(Time.now)) / 86400000) === k })
        return { k: k, ds: ds, open: ds.filter(function (d) { return d.out === "open" || d.out === "escalated" }).length, n: ds.length,
                 label: k === 0 ? "Today" : k === -1 ? "Yesterday" : Time.dayName(Time.now + k * 86400000) }
    })
    readonly property int mx: { var m = 4; days.forEach(function (x) { m = Math.max(m, x.n) }); return Math.ceil(m / 2) * 2 }
    readonly property int pl: 34
    readonly property int ph: 190 - 18 - 24
    readonly property real cw: (width - pl - 8) / 7
    readonly property real bw: Math.min(64, cw * 0.56)
    function yOf(v) { return 18 + ph - (v / mx) * ph }
    onDaysChanged: cv.requestPaint()
    onDayChanged: cv.requestPaint()
    onHovChanged: cv.requestPaint()
    onWidthChanged: cv.requestPaint()
    Connections { target: Theme; function onDarkChanged() { cv.requestPaint() } }

    Canvas {
        id: cv
        width: parent.width; height: 190
        onPaint: {
            var c = getContext("2d"); c.reset()
            c.font = "10px '" + Theme.mono + "'"
            ;[0, root.mx / 2, root.mx].forEach(function (v) {
                c.strokeStyle = Theme.grid; c.beginPath(); c.moveTo(root.pl, root.yOf(v) + 0.5); c.lineTo(width - 8, root.yOf(v) + 0.5); c.stroke()
                c.fillStyle = Theme.text3; c.textAlign = "end"; c.fillText(String(v), root.pl - 6, root.yOf(v) + 4)
            })
            root.days.forEach(function (x, i) {
                var cx = root.pl + i * root.cw + root.cw / 2, on = root.day === x.k, dim = root.day !== null && !on
                if (on || root.hov === i) { c.fillStyle = on ? Theme.accentSoft : Theme.surface2; c.fillRect(root.pl + i * root.cw, 18, root.cw, root.ph) }
                c.globalAlpha = dim ? 0.4 : 1
                if (x.n - x.open) { c.fillStyle = Theme.ser6; c.fillRect(cx - root.bw / 2, root.yOf(x.n), root.bw, root.yOf(x.open) - root.yOf(x.n)) }
                if (x.open) { c.fillStyle = Theme.crit; c.fillRect(cx - root.bw / 2, root.yOf(x.open), root.bw, root.yOf(0) - root.yOf(x.open)) }
                c.textAlign = "center"; c.font = "600 12px '" + Theme.mono + "'"; c.fillStyle = x.n ? Theme.text : Theme.text4; c.fillText(String(x.n), cx, root.yOf(x.n) - 6)
                c.font = "11px '" + Theme.sans + "'"; c.fillStyle = on ? Theme.accent : Theme.text3; c.fillText(x.label, cx, 190 - 6)
                c.globalAlpha = 1
            })
        }
        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            readonly property int at: Math.floor((mouseX - root.pl) / root.cw)
            cursorShape: at >= 0 && at < 7 && root.days[at].n ? Qt.PointingHandCursor : Qt.ArrowCursor
            onPositionChanged: root.hov = at >= 0 && at < 7 ? at : -1
            onExited: root.hov = -1
            onClicked: if (at >= 0 && at < 7 && root.days[at].n) root.pickDay(root.day === root.days[at].k ? null : root.days[at].k)
        }
    }
    Item {
        anchors.top: cv.bottom; anchors.topMargin: 8
        width: parent.width; height: 20
        readonly property int tot: root.days.reduce(function (t, x) { return t + x.n }, 0)
        readonly property int still: root.days.reduce(function (t, x) { return t + x.open }, 0)
        readonly property var best: root.days.slice().sort(function (a, b) { return b.n - a.n || b.k - a.k })[0]
        Txt { width: parent.width - lg.width - 12; color: Theme.text2
              text: parent.tot ? Theme.fmt(parent.tot) + " this week, " + Theme.fmt(parent.still) + " still open. The busiest day was " + (parent.best.k >= -1 ? parent.best.label.toLowerCase() : parent.best.label) + ", with " + parent.best.n + "."
                               : "No rule was broken this week." }
        Row { id: lg; anchors.right: parent.right; spacing: 14
              Repeater { model: [[Theme.crit, "Still open"], [Theme.ser6, "Dealt with"]]
                         Row { required property var modelData; spacing: 6
                               Rectangle { width: 10; height: 10; radius: 2; color: modelData[0]; anchors.verticalCenter: parent.verticalCenter }
                               Txt { text: modelData[1]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } } } }
    }
    // the day under the pointer, named
    Rectangle {
        visible: root.hov >= 0 && root.days[root.hov].n > 0
        x: Math.min(root.pl + root.hov * root.cw + root.cw / 2 + root.bw / 2 + 8, root.width - 260); y: 4
        width: 250; height: tc.height + 16; radius: 6; color: Theme.surface; border.color: Theme.border
        Column { id: tc; x: 10; y: 8; width: parent.width - 20; spacing: 2
                 Txt { width: parent.width; font.weight: Font.DemiBold; font.pixelSize: 12
                       text: root.hov >= 0 ? root.days[root.hov].label + " · " + Theme.many(root.days[root.hov].n, "deviation") + ", " + root.days[root.hov].open + " open" : "" }
                 Repeater { model: root.hov >= 0 ? root.days[root.hov].ds.slice(0, 4) : []
                            Txt { required property var modelData; width: parent.width; text: modelData.short; color: Theme.text2; font.pixelSize: 12 } } }
    }
}
