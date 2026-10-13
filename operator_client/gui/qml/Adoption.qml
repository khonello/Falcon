import QtQuick
import "."

// MACHINES ON THE CURRENT VERSION, DAY BY DAY since it was approved (the concept's Adoption): a line climbing to
// the goal (every machine, dashed green), the gap at the end drawn amber, "N of G" beside it; hover a day for who
// updated that day. days: [{day (ISO date), n, joined: [host], note}] from rollout.gate's adoption.
Item {
    id: root
    property var days: []
    property int goal: 0
    property string version: ""
    implicitHeight: 200
    readonly property int pl: 30
    readonly property int pr: 70
    readonly property int pt: 14
    readonly property int pb: 24
    readonly property real pw: Math.max(40, width - pl - pr)
    readonly property real ph: height - pt - pb
    readonly property int n: days.length
    function xAt(i) { return pl + (n > 1 ? i / (n - 1) : 0.5) * pw }
    function yAt(v) { return pt + ph - (v / Math.max(1, goal)) * ph }
    function label(d, i) { if (i === n - 1) return "Today"; var t = new Date(d + "T00:00:00"); return t.getDate() + " " + Time.months[t.getMonth()] }
    readonly property int last: n ? days[n - 1].n : 0
    property int hov: -1

    onDaysChanged: cv.requestPaint()
    onWidthChanged: cv.requestPaint()
    onHovChanged: cv.requestPaint()
    Connections { target: Theme; function onDarkChanged() { cv.requestPaint() } }

    Canvas {
        id: cv
        anchors.fill: parent
        onPaint: {
            var c = getContext("2d"); c.reset()
            var G = Math.max(1, root.goal)
            c.font = "10.5px '" + Theme.mono + "'"; c.textAlign = "right"
            ;[0, Math.round(G / 2), G].forEach(function (v) {
                c.strokeStyle = Theme.grid; c.lineWidth = 1; c.beginPath(); c.moveTo(root.pl, root.yAt(v)); c.lineTo(root.width - root.pr, root.yAt(v)); c.stroke()
                c.fillStyle = Theme.text3; c.fillText(String(v), root.pl - 6, root.yAt(v) + 4)
            })
            c.strokeStyle = Theme.ok; c.setLineDash([4, 3]); c.beginPath(); c.moveTo(root.pl, root.yAt(G)); c.lineTo(root.width - root.pr, root.yAt(G)); c.stroke(); c.setLineDash([])
            c.font = "11px '" + Theme.sans + "'"; c.textAlign = "left"; c.fillStyle = Theme.ok; c.fillText("Goal: all " + G, root.width - root.pr + 6, root.yAt(G) + 4)
            if (!root.n) return
            c.beginPath()
            root.days.forEach(function (p, i) { if (i) c.lineTo(root.xAt(i), root.yAt(p.n)); else c.moveTo(root.xAt(i), root.yAt(p.n)) })
            c.lineTo(root.xAt(root.n - 1), root.yAt(0)); c.lineTo(root.xAt(0), root.yAt(0)); c.closePath()
            c.globalAlpha = 0.12; c.fillStyle = Theme.ser2; c.fill(); c.globalAlpha = 1
            c.beginPath()
            root.days.forEach(function (p, i) { if (i) c.lineTo(root.xAt(i), root.yAt(p.n)); else c.moveTo(root.xAt(i), root.yAt(p.n)) })
            c.strokeStyle = Theme.ser2; c.lineWidth = 2; c.stroke()
            root.days.forEach(function (p, i) { c.beginPath(); c.arc(root.xAt(i), root.yAt(p.n), root.hov === i ? 4.5 : 3, 0, Math.PI * 2); c.fillStyle = Theme.surface; c.fill(); c.strokeStyle = Theme.ser2; c.lineWidth = 2; c.stroke() })
            c.font = "600 12px '" + Theme.sans + "'"; c.fillStyle = Theme.text; c.fillText(root.last + " of " + G, root.width - root.pr + 6, root.yAt(root.last) + 4)
            c.strokeStyle = Theme.med; c.lineWidth = 1.5; c.setLineDash([2, 2]); c.beginPath(); c.moveTo(root.xAt(root.n - 1) + 2, root.yAt(root.last)); c.lineTo(root.xAt(root.n - 1) + 2, root.yAt(G)); c.stroke(); c.setLineDash([])
            c.font = "10.5px '" + Theme.mono + "'"; c.fillStyle = Theme.text3
            root.days.forEach(function (p, i) { c.textAlign = i === 0 ? "start" : i === root.n - 1 ? "end" : "center"; c.fillText(root.label(p.day, i), root.xAt(i), root.height - 6) })
        }
    }
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        onPositionChanged: function (m) { var i = Math.round((m.x - root.pl) / Math.max(1, root.pw) * (root.n - 1)); root.hov = i >= 0 && i < root.n ? i : -1 }
        onExited: root.hov = -1
    }
    Rectangle {
        visible: root.hov >= 0
        x: Math.min(root.xAt(Math.max(0, root.hov)) + 12, root.width - width - 4)
        y: 4
        width: 260
        height: tipCol.height + 14
        radius: 5
        color: Theme.surface
        border.width: 1
        border.color: Theme.borderStrong
        Column {
            id: tipCol
            x: 9; y: 7
            width: parent.width - 18
            spacing: 3
            readonly property var d: root.hov >= 0 ? root.days[root.hov] : null
            Txt { text: parent.d ? root.label(parent.d.day, root.hov) + (parent.d.note ? " · " + parent.d.note : "") : ""; mono: true; color: Theme.text3; font.pixelSize: 11 }
            Txt { textFormat: Text.StyledText; font.pixelSize: 12; text: parent.d ? "<b>" + parent.d.n + "</b><font color='" + Theme.text3 + "'> of " + root.goal + " machines on " + root.version + "</font>" : "" }
            Txt { width: parent.width; color: Theme.text2; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                  text: parent.d ? "Updated that day: " + (parent.d.joined && parent.d.joined.length ? parent.d.joined.join(", ") : "none") : "" }
        }
    }
}
