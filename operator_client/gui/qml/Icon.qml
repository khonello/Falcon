import QtQuick
import QtQuick.Shapes
import "."

// One glyph. Give it a name and a colour; nothing else. Where the concept has the icon (AntIcons, the Ant Design paths
// the concept draws), it is filled exactly as the concept fills it, an em box of `size`; otherwise the name's stroke from
// Icons is drawn.
//
// The sub-paths are joined into a single `d`: SVG path data takes many subpaths, and a Shape's
// ShapePath cannot be produced by a Repeater (a Repeater's delegate has to be an Item).
Item {
    id: root
    property string name: ""
    property color color: Theme.mid
    property int size: 16
    property real weight: 1.6
    readonly property string antName: Icons.antOf(name)
    readonly property var ant: antName !== "" ? AntIcons.glyph[antName] : null

    implicitWidth: size
    implicitHeight: size
    visible: Icons.has(name)

    Shape {
        visible: root.ant === null
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
            PathSvg { path: root.ant === null && Icons.glyph[root.name] ? Icons.glyph[root.name].join(" ") : "" }
        }
    }
    // the Ant icon: its viewBox (x, y, size) scaled to the em box
    Shape {
        id: antShape
        visible: root.ant !== null
        readonly property real k: root.ant ? root.size / root.ant[2] : 1
        x: root.ant ? -root.ant[0] * k : 0
        y: root.ant ? -root.ant[1] * k : 0
        width: root.size - x
        height: root.size - y
        antialiasing: true
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            strokeColor: "transparent"
            strokeWidth: -1
            fillColor: root.color
            fillRule: ShapePath.WindingFill
            scale: Qt.size(antShape.k, antShape.k)
            PathSvg { path: root.ant ? root.ant[3] : "" }
        }
    }
}
