import QtQuick
import QtQuick.Shapes
import "."

// One glyph from Icons, stroked in whatever colour it is given. Up to six sub-paths, which is all
// any icon in the set uses; an unused slot draws nothing.
Item {
    id: root

    property string name: ""
    property color color: Theme.dim
    property int size: 16
    property real weight: 1.75

    readonly property var paths: Icons.get(name)
    implicitWidth: size
    implicitHeight: size

    Shape {
        width: 24
        height: 24
        scale: root.size / 24
        transformOrigin: Item.TopLeft
        antialiasing: true
        layer.enabled: true
        layer.samples: 4

        ShapePath {
            strokeColor: root.paths.length > 0 ? root.color : "transparent"
            strokeWidth: root.weight
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.paths.length > 0 ? root.paths[0] : "" }
        }
        ShapePath {
            strokeColor: root.paths.length > 1 ? root.color : "transparent"
            strokeWidth: root.weight
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.paths.length > 1 ? root.paths[1] : "" }
        }
        ShapePath {
            strokeColor: root.paths.length > 2 ? root.color : "transparent"
            strokeWidth: root.weight
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.paths.length > 2 ? root.paths[2] : "" }
        }
        ShapePath {
            strokeColor: root.paths.length > 3 ? root.color : "transparent"
            strokeWidth: root.weight
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.paths.length > 3 ? root.paths[3] : "" }
        }
        ShapePath {
            strokeColor: root.paths.length > 4 ? root.color : "transparent"
            strokeWidth: root.weight
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.paths.length > 4 ? root.paths[4] : "" }
        }
        ShapePath {
            strokeColor: root.paths.length > 5 ? root.color : "transparent"
            strokeWidth: root.weight
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.paths.length > 5 ? root.paths[5] : "" }
        }
    }
}
