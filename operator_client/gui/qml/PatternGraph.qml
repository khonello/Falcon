import QtQuick
import "."

// The pattern, left to right: what starts it, what is expected, the branch to a deviation, and what
// happens then. Never: three boxes. Follow: kept above, the dashed late branch below. Limit: four boxes.
Item {
    id: root
    property var s: Rules.blank()
    readonly property bool fol: s.shape === "follow"
    implicitHeight: fol ? 156 : 92
    readonly property int nh: 54
    readonly property int gap: 84
    readonly property real nw: Math.min(196, Math.floor((Math.max(560, width) - 8 - 3 * gap) / 4))
    readonly property real y1: fol ? 38 : implicitHeight / 2
    readonly property real y2: fol ? 118 : implicitHeight / 2
    function xAt(c) { return 4 + c * (nw + gap) }
    readonly property string lim: s.within ? Rules.dur(s.within.n * Rules.units[s.within.unit]) : ""
    readonly property string resp: ["Record"].concat(s.resp && s.resp.report ? ["Tell you"] : [], s.resp && s.resp.admin ? ["Tell the Admin"] : [],
                                                       s.resp && s.resp.action ? ["Run " + (s.resp.actionName || "an action")] : []).join(" · ")
    // [col, y, title, sub, tone]
    readonly property var nodes: s.shape === "never"
        ? [[0, y1, "It happens", Rules.trig[s.trigger], ""], [1, y1, "A deviation", "Noted at once", "dev"], [2, y1, "Then", resp, ""]]
        : fol ? [[0, y1, "Trigger", Rules.trig[s.trigger], ""], [1, y1, "Expected within " + lim, Rules.exp[s.expect], ""], [2, y1, "Kept", "Nothing is recorded", "ok"],
                 [2, y2, "A deviation", "Noted when time runs out", "dev"], [3, y2, "Then", resp, ""]]
        : [[0, y1, "Counted", s.reading, ""], [1, y1, "The line", (s.limit.n === 0 ? "None" : "More than " + s.limit.n) + " per " + s.limit.per, ""],
           [2, y1, "A deviation", "Noted when it goes over", "dev"], [3, y1, "Then", resp, ""]]
    // [c1, ya, c2, yb, tone, label]
    readonly property var edges: s.shape === "never" ? [[0, y1, 1, y1, "", ""], [1, y1, 2, y1, "", ""]]
        : fol ? [[0, y1, 1, y1, "", ""], [1, y1, 2, y1, "ok", "in time"], [1, y1, 2, y2, "dev", "too late"], [2, y2, 3, y2, "", ""]]
        : [[0, y1, 1, y1, "", ""], [1, y1, 2, y1, "dev", "over the line"], [2, y1, 3, y1, "", ""]]
    onSChanged: cv.requestPaint()
    onWidthChanged: cv.requestPaint()
    Connections { target: Theme; function onDarkChanged() { cv.requestPaint() } }

    Canvas {
        id: cv
        anchors.fill: parent
        onPaint: {
            var c = getContext("2d"); c.reset()
            root.edges.forEach(function (e) {
                var x1 = root.xAt(e[0]) + root.nw, x2 = root.xAt(e[2]), m = (x1 + x2) / 2
                var col = e[4] === "dev" ? Theme.crit : e[4] === "ok" ? Theme.ok : Theme.text3
                c.strokeStyle = col; c.lineWidth = 1.75; c.setLineDash(e[4] === "dev" ? [5, 4] : [])
                c.beginPath(); c.moveTo(x1, e[1]); c.bezierCurveTo(m, e[1], m, e[3], x2 - 6, e[3]); c.stroke(); c.setLineDash([])
                c.fillStyle = col; c.beginPath(); c.moveTo(x2 - 7, e[3] - 4); c.lineTo(x2, e[3]); c.lineTo(x2 - 7, e[3] + 4); c.closePath(); c.fill()
                if (e[5]) { c.font = "11px '" + Theme.sans + "'"; c.textAlign = "center"; var tx = (x1 + x2) / 2, ty = (e[1] + e[3]) / 2 - 7
                            c.lineWidth = 4; c.strokeStyle = Theme.surface; c.strokeText(e[5], tx, ty); c.fillStyle = col; c.fillText(e[5], tx, ty) }
            })
            root.nodes.forEach(function (n) {
                var x = root.xAt(n[0]), y = n[1] - root.nh / 2
                c.fillStyle = n[4] === "dev" ? Theme.mix(Theme.crit, Theme.surface, 0.07) : Theme.surface
                c.strokeStyle = n[4] === "dev" ? Theme.crit : n[4] === "ok" ? Theme.ok : Theme.borderStrong
                c.lineWidth = 1; c.setLineDash(n[4] === "dev" ? [4, 3] : [])
                c.beginPath(); c.roundedRect(x + 0.5, y + 0.5, root.nw, root.nh, 5, 5); c.fill(); c.stroke(); c.setLineDash([])
            })
        }
    }
    Repeater {
        model: root.nodes
        Column {
            required property var modelData
            x: root.xAt(modelData[0]) + 10; y: modelData[1] - 17
            width: root.nw - 20; spacing: 2
            Txt { width: parent.width; text: modelData[2]; font.pixelSize: 12; font.weight: Font.DemiBold }
            Txt { width: parent.width; text: modelData[3] || ""; font.pixelSize: 11; color: Theme.text3 }
        }
    }
}
