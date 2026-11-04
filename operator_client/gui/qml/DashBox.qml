import QtQuick
import "."

// CSS's 1px dashed border around a box, corners rounded: lay it over the box, it takes no presses.
Canvas {
    id: root
    property color c: Theme.borderStrong
    property real radius: 7
    anchors.fill: parent
    onCChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        var g = getContext("2d"), r = radius, w = width - 1, h = height - 1
        g.clearRect(0, 0, width, height)
        g.strokeStyle = c
        g.lineWidth = 1
        g.setLineDash([3, 3])
        g.beginPath()
        g.moveTo(0.5 + r, 0.5)
        g.lineTo(0.5 + w - r, 0.5); g.arcTo(0.5 + w, 0.5, 0.5 + w, 0.5 + r, r)
        g.lineTo(0.5 + w, 0.5 + h - r); g.arcTo(0.5 + w, 0.5 + h, 0.5 + w - r, 0.5 + h, r)
        g.lineTo(0.5 + r, 0.5 + h); g.arcTo(0.5, 0.5 + h, 0.5, 0.5 + h - r, r)
        g.lineTo(0.5, 0.5 + r); g.arcTo(0.5, 0.5, 0.5 + r, 0.5, r)
        g.stroke()
    }
}
