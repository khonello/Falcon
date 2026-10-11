import QtQuick
import "."

// SEVEN DAYS AS BARS, stacked by series, today on the right; hover a day for its numbers.
// series: [{name, c, v: [7 numbers, oldest first]}]. `pickable` lets a click pick a day (index 0..6).
Item {
    id: root
    property var series: []
    property bool pickable: false
    property int picked: -1
    signal pick(int day)
    implicitHeight: 150

    readonly property var labels: { var out = []; for (var i = 6; i >= 0; i--) { var d = new Date(Time.now - i * 86400000); out.push(i === 0 ? "Today" : Time.days[d.getDay()]) } return out }
    readonly property var tot: [0, 1, 2, 3, 4, 5, 6].map(function (i) { return root.series.reduce(function (a, s) { return a + (s.v[i] || 0) }, 0) })
    readonly property real mx: { var m = Math.max(4, Math.max.apply(null, tot)), p = Math.pow(10, Math.floor(Math.log(m) / Math.LN10)), r = m / p; return (r <= 1 ? 1 : r <= 2 ? 2 : r <= 5 ? 5 : 10) * p }
    readonly property int pl: 28
    readonly property real pw: width - pl - 6
    readonly property real ph: height - 8 - 22
    readonly property real cw: pw / 7
    property int hov: -1
    function yAt(v) { return 8 + ph - (v / mx) * ph }

    onSeriesChanged: cv.requestPaint()
    onWidthChanged: cv.requestPaint()
    onHovChanged: cv.requestPaint()
    onPickedChanged: cv.requestPaint()
    Connections { target: Theme; function onDarkChanged() { cv.requestPaint() } }
    Canvas {
        id: cv
        anchors.fill: parent
        onPaint: {
            var c = getContext("2d"); c.reset()
            c.font = "10px '" + Theme.mono + "'"; c.textAlign = "right"
            ;[0, root.mx / 2, root.mx].forEach(function (v) {
                c.strokeStyle = Theme.grid; c.beginPath(); c.moveTo(root.pl, root.yAt(v) + 0.5); c.lineTo(root.width - 6, root.yAt(v) + 0.5); c.stroke()
                c.fillStyle = Theme.text3; c.fillText(String(Math.round(v)), root.pl - 6, root.yAt(v) + 4)
            })
            for (var i = 0; i < 7; i++) {
                if (root.hov === i || root.picked === i) { c.fillStyle = root.picked === i ? Theme.accentSoft : Theme.surface2; c.fillRect(root.pl + i * root.cw, 8, root.cw, root.ph) }
                var acc = 0
                c.globalAlpha = root.picked >= 0 && root.picked !== i ? 0.4 : 1
                for (var s = 0; s < root.series.length; s++) {
                    var v = root.series[s].v[i] || 0; if (!v) continue
                    var y0 = root.yAt(acc), y1 = root.yAt(acc + v); acc += v
                    c.fillStyle = root.series[s].c
                    c.fillRect(root.pl + i * root.cw + root.cw * 0.22, y1, root.cw * 0.56, Math.max(1, y0 - y1))
                }
                c.globalAlpha = 1
                c.fillStyle = root.picked === i ? Theme.accent : Theme.text3; c.textAlign = "center"; c.font = "10px '" + Theme.sans + "'"
                c.fillText(root.labels[i], root.pl + i * root.cw + root.cw / 2, root.height - 6)
            }
        }
    }
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.pickable ? Qt.PointingHandCursor : Qt.ArrowCursor
        onPositionChanged: function (m) { var i = Math.floor((m.x - root.pl) / root.cw); root.hov = i >= 0 && i < 7 ? i : -1 }
        onExited: root.hov = -1
        onClicked: if (root.pickable && root.hov >= 0 && root.tot[root.hov]) root.pick(root.picked === root.hov ? -1 : root.hov)
    }
    Rectangle {
        visible: root.hov >= 0
        x: Math.min(root.pl + (root.hov + 1) * root.cw, root.width - width)
        y: 4
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
            Txt { text: root.hov >= 0 ? root.labels[root.hov] + (root.tot[root.hov] === 0 ? " · nothing" : "") : ""; mono: true; color: Theme.text3; font.pixelSize: 11 }
            Repeater {
                model: root.hov >= 0 ? root.series.filter(function (s) { return s.v[root.hov] }) : []
                Row { required property var modelData; width: tc.width; spacing: 8
                      Rectangle { width: 10; height: 10; radius: 2; color: modelData.c; anchors.verticalCenter: parent.verticalCenter }
                      Txt { text: modelData.name; color: Theme.text2; font.pixelSize: 12; width: parent.width - 60 }
                      Txt { text: String(modelData.v[root.hov]); mono: true; font.weight: Font.DemiBold; font.pixelSize: 12; elide: Text.ElideNone } }
            }
        }
    }
}
