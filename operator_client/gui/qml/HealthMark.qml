import QtQuick
import "."

// One of the five health marks. Colour is spent only where someone has to act: everything fine is the
// same quiet grey; a problem gets red, filled for critical and tinted for high; something to watch
// gets one small amber dot; offline is dashed.
//   k: quiet | watch | high | crit | offline
Item {
    id: root
    property string k: "quiet"
    property int size: 12
    property string label: ""
    property int fontSize: 12
    property bool bordered: true            // the small mark has a hairline; a map tile does not
    implicitWidth: size
    implicitHeight: size

    Rectangle {
        anchors.fill: parent
        radius: root.size > 24 ? 4 : 3
        color: root.k === "crit" ? Theme.crit
             : root.k === "high" ? Theme.mix(Theme.crit, Theme.surface, 0.14)
             : root.k === "offline" ? "transparent" : Theme.surface3
        border.width: root.k === "offline" ? 0 : (root.bordered && (root.k === "quiet" || root.k === "watch") ? 1 : 0)
        border.color: Theme.borderStrong
        // dashed, for offline
        Canvas {
            visible: root.k === "offline"
            anchors.fill: parent
            onPaint: {
                var c = getContext("2d"); c.reset()
                c.strokeStyle = Theme.borderStrong; c.lineWidth = 1; c.setLineDash([3, 3])
                c.beginPath(); c.roundedRect(0.5, 0.5, width - 1, height - 1, 3, 3); c.stroke()
            }
            Connections { target: Theme; function onDarkChanged() { parent.requestPaint() } }
        }
        Txt {
            visible: root.label !== ""
            anchors.centerIn: parent
            text: root.label
            mono: true
            font.pixelSize: root.fontSize
            font.weight: Font.Medium
            elide: Text.ElideNone
            color: root.k === "crit" ? Theme.inverse : root.k === "high" ? Theme.crit : root.k === "offline" ? Theme.text4 : Theme.text2
        }
    }
    Rectangle {
        visible: root.k === "watch"
        width: root.size > 24 ? 7 : 6
        height: width
        radius: width / 2
        color: Theme.med
        x: root.size > 24 ? parent.width - width - 4 : parent.width - width + 3
        y: root.size > 24 ? 4 : -3
        border.width: root.size > 24 ? 0 : 1.5
        border.color: Theme.surface
    }
}
