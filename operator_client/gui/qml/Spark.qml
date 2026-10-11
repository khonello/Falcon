import QtQuick
import QtQuick.Shapes
import "."

// A small trend line: values (nulls break it), drawn into w x h on its own scale or `max`.
Shape {
    id: root
    property var values: []
    property color c: Theme.ser6
    property real max: 0
    width: 84
    height: 22
    preferredRendererType: Shape.CurveRenderer
    readonly property string d: {
        var v = values || [], n = v.length
        if (n < 2) return ""
        var mx = max
        if (!mx) { mx = 1; for (var i = 0; i < n; i++) if (v[i] !== null && v[i] > mx) mx = v[i] }
        var out = "", pen = false
        for (var k = 0; k < n; k++) {
            if (v[k] === null || v[k] === undefined) { pen = false; continue }
            var x = (k / (n - 1)) * (width - 2) + 1, y = height - 2 - (v[k] / mx) * (height - 4)
            out += (pen ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1)
            pen = true
        }
        return out
    }
    ShapePath {
        strokeColor: root.c
        strokeWidth: 1.25
        fillColor: "transparent"
        joinStyle: ShapePath.RoundJoin
        PathSvg { path: root.d }
    }
}
