import QtQuick
import QtQuick.Shapes
import "."

// One glyph, stroked. Give it a name from Icons and a colour; nothing else.
//
// The sub-paths are joined into a single `d`: SVG path data takes many subpaths, and a Shape's
// ShapePath cannot be produced by a Repeater (a Repeater's delegate has to be an Item).
Item {
    id: root
    property string name: ""
    property color color: Theme.mid
    property int size: 16
    property real weight: 1.6

    implicitWidth: size
    implicitHeight: size
    visible: Icons.has(name)

    Shape {
        anchors.fill: parent
        antialiasing: true
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            strokeColor: root.color
            strokeWidth: root.weight * (root.size / 16)
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            scale: Qt.size(root.size / 24, root.size / 24)
            PathSvg { path: Icons.has(root.name) ? Icons.glyph[root.name].join(" ") : "" }
        }
    }
}
