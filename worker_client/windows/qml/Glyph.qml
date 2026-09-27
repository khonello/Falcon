import QtQuick
import QtQuick.Shapes

// The few icons the Worker's windows use, drawn as the Operator Client draws them (the same paths, stroked). The Worker
// package does not import the Operator Client, so the set it needs lives here.
Item {
    id: root
    property string name: ""
    property color color: "#A6B0BC"
    property int size: 16
    readonly property var set: ({
        shield: ["M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"],
        bell: ["M6 16V11a6 6 0 0 1 12 0v5l2 2H4z", "M10 21h4"],
        lock: ["M5 11h14v10H5z", "M8 11V8a4 4 0 0 1 8 0v3"],
        ping: ["M15 12a3 3 0 1 0 -6 0a3 3 0 1 0 6 0", "M5.6 5.6a9 9 0 0 0 0 12.8", "M18.4 5.6a9 9 0 0 1 0 12.8"],
        tasks: ["M4.5 4.5h15v15h-15z", "M8.5 12.2l2.5 2.5 4.5-5"],
        clock: ["M20.5 12a8.5 8.5 0 1 0 -17 0a8.5 8.5 0 1 0 17 0", "M12 7.5V12l3 2"],
        file: ["M6 3h8l4 4v14H6z", "M14 3v4h4"],
        window: ["M3 4h18v16H3z", "M3 9h18"],
        x: ["M6 6l12 12", "M18 6L6 18"],
        play: ["M7 4l12 8-12 8z"],
        check: ["M5 12l5 5 9-10"]
    })
    readonly property var paths: set[name] || []
    implicitWidth: size
    implicitHeight: size
    Shape {
        width: 24; height: 24
        scale: root.size / 24
        transformOrigin: Item.TopLeft
        antialiasing: true
        layer.enabled: true
        layer.samples: 4
        ShapePath { strokeColor: root.paths.length > 0 ? root.color : "transparent"; strokeWidth: 1.75; fillColor: "transparent"
                    capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin; PathSvg { path: root.paths[0] || "" } }
        ShapePath { strokeColor: root.paths.length > 1 ? root.color : "transparent"; strokeWidth: 1.75; fillColor: "transparent"
                    capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin; PathSvg { path: root.paths[1] || "" } }
        ShapePath { strokeColor: root.paths.length > 2 ? root.color : "transparent"; strokeWidth: 1.75; fillColor: "transparent"
                    capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin; PathSvg { path: root.paths[2] || "" } }
    }
}
