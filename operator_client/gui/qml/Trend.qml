import QtQuick
import QtQuick.Shapes
import "."

// One series, so there is no legend: the title names it. The last point carries the only marker
// and the only number, because that is the one a person reads.
Item {
    id: root

    property var points: []                // [Number]
    property color tint: Theme.ok
    property int padLeft: 8
    property int padRight: 34

    readonly property real lo: {
        var m = points.length ? points[0] : 0
        for (var i = 0; i < points.length; i++) m = Math.min(m, points[i])
        return m
    }
    readonly property real hi: {
        var m = points.length ? points[0] : 1
        for (var i = 0; i < points.length; i++) m = Math.max(m, points[i])
        return m
    }
    readonly property real span: Math.max(1, hi - lo)
    readonly property real step: points.length > 1 ? (width - padLeft - padRight) / (points.length - 1) : 0
    readonly property real baseY: height - 14

    function px(i) { return padLeft + i * step }
    function py(i) { return baseY - 6 - ((points[i] - lo) / span) * (height - 40) }

    implicitHeight: 118

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        y: root.baseY
        height: 1
        color: Theme.line
    }

    Shape {
        anchors.fill: parent
        antialiasing: true
        layer.enabled: true
        layer.samples: 4
        visible: root.points.length > 1

        ShapePath {
            strokeColor: root.tint
            strokeWidth: 2
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathPolyline {
                path: {
                    var out = []
                    for (var i = 0; i < root.points.length; i++) out.push(Qt.point(root.px(i), root.py(i)))
                    return out
                }
            }
        }
    }

    Rectangle {
        visible: root.points.length > 0
        width: 9
        height: 9
        radius: 5
        color: root.tint
        border.width: 2
        border.color: Theme.chartBg
        x: root.points.length ? root.px(root.points.length - 1) - 4.5 : 0
        y: root.points.length ? root.py(root.points.length - 1) - 4.5 : 0
    }
    Txt {
        visible: root.points.length > 0
        text: root.points.length ? String(root.points[root.points.length - 1]) : ""
        monospace: true
        font.pixelSize: Theme.fMeta
        x: root.points.length ? root.px(root.points.length - 1) + 10 : 0
        y: root.points.length ? root.py(root.points.length - 1) - 8 : 0
    }
}
