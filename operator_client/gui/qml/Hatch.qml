import QtQuick
import "."

// Diagonal hairlines on a ground: the look of a day that belongs to another month, so the first and last
// days of the month read at a glance and nothing is mistaken for a weekend.
Canvas {
    id: root
    property color ground: Theme.surface3
    property color line: Theme.border
    property int gap: 8

    onGroundChanged: requestPaint()
    onLineChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        var c = getContext("2d")
        c.reset()
        c.fillStyle = ground
        c.fillRect(0, 0, width, height)
        c.strokeStyle = line
        c.lineWidth = 1
        c.beginPath()
        for (var x = -height; x < width; x += gap) { c.moveTo(x, height); c.lineTo(x + height, 0) }
        c.stroke()
    }
}
