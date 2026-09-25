import QtQuick
import QtQuick.Shapes
import "."

// A held session's clock as a ring: the arc is what is left. Under five minutes the ring is all
// that changes (board T05) -- no colour swap, no pulse, because the lid is already red.
Item {
    id: root

    property real fraction: 1              // 0..1, what is left
    property color color: "#ffffff"
    property real thickness: 2.5

    implicitWidth: 20
    implicitHeight: 20

    Shape {
        anchors.fill: parent
        antialiasing: true
        layer.enabled: true
        layer.samples: 4

        ShapePath {
            strokeColor: Qt.rgba(root.color.r, root.color.g, root.color.b, 0.28)
            strokeWidth: root.thickness
            fillColor: "transparent"
            PathAngleArc {
                centerX: root.width / 2; centerY: root.height / 2
                radiusX: root.width / 2 - root.thickness; radiusY: root.height / 2 - root.thickness
                startAngle: 0; sweepAngle: 360
            }
        }
        ShapePath {
            strokeColor: root.color
            strokeWidth: root.thickness
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            PathAngleArc {
                centerX: root.width / 2; centerY: root.height / 2
                radiusX: root.width / 2 - root.thickness; radiusY: root.height / 2 - root.thickness
                startAngle: -90; sweepAngle: 360 * Math.max(0, Math.min(1, root.fraction))
            }
        }
    }
}
