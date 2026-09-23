import QtQuick
import QtQuick.Shapes
import "."

// Department -> Admin -> PC, drawn. Colour is the department and nothing else; the shape is the
// level. Picking a department descends into it: the same drawing with everything else quietened,
// so descent is a change of attention rather than a different picture.
Item {
    id: root

    property var departments: []           // hierarchy.tree's departments, in order
    property int focusId: 0                // 0 = the whole system
    signal picked(int departmentId)

    readonly property real rootX: 46
    readonly property real deptX: Math.max(150, width * 0.34)
    readonly property real pcX: Math.max(deptX + 120, width * 0.64)
    readonly property int perRow: 4

    function deptY(i) { return height * (i + 1) / (departments.length + 1) }
    function lit(d) { return focusId === 0 || focusId === d.department_id }
    function tintOf(i) { return Theme.series(i) }
    function pcX2(i) { return pcX + (i % perRow) * 22 }
    function pcY(deptIndex, i) { return deptY(deptIndex) - 18 + Math.floor(i / perRow) * 20 }

    // a cubic as points: one path type for every link on the map, so they all bend alike
    function curve(x0, y0, x1, y1) {
        var cx = (x0 + x1) / 2
        var out = []
        for (var s = 0; s <= 14; s++) {
            var t = s / 14, u = 1 - t
            out.push(Qt.point(u * u * u * x0 + 3 * u * u * t * cx + 3 * u * t * t * cx + t * t * t * x1,
                              u * u * u * y0 + 3 * u * u * t * y0 + 3 * u * t * t * y1 + t * t * t * y1))
        }
        return out
    }

    Repeater {
        model: root.departments
        delegate: Item {
            id: lane
            required property var modelData
            required property int index
            anchors.fill: parent

            readonly property real dy: root.deptY(index)
            readonly property bool on: root.lit(modelData)
            readonly property bool chosen: root.focusId === modelData.department_id
            readonly property color tint: root.tintOf(index)

            Shape {
                anchors.fill: parent
                antialiasing: true
                layer.enabled: true
                layer.samples: 4

                // you -> this department
                ShapePath {
                    strokeColor: Qt.rgba(lane.tint.r, lane.tint.g, lane.tint.b, lane.on ? 0.55 : 0.14)
                    strokeWidth: 1.5
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathPolyline { path: root.curve(root.rootX + 10, root.height / 2, root.deptX - 9, lane.dy) }
                }
                // this department -> each of its PCs
                ShapePath {
                    strokeColor: Qt.rgba(lane.tint.r, lane.tint.g, lane.tint.b, lane.on ? 0.28 : 0.08)
                    strokeWidth: 1
                    fillColor: "transparent"
                    PathMultiline {
                        paths: {
                            var out = []
                            for (var i = 0; i < lane.modelData.workers.length; i++)
                                out.push(root.curve(root.deptX + 9, lane.dy, root.pcX2(i) - 5, root.pcY(lane.index, i)))
                            return out
                        }
                    }
                }
            }

            Repeater {
                model: lane.modelData.workers
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: 10
                    height: 10
                    radius: 5
                    color: lane.tint
                    opacity: lane.on ? 0.85 : 0.2
                    x: root.pcX2(index) - 5
                    y: root.pcY(lane.index, index) - 5
                }
            }

            Rectangle {
                width: lane.chosen ? 20 : 16
                height: width
                radius: width / 2
                color: lane.tint
                opacity: lane.on ? 1 : 0.22
                x: root.deptX - width / 2
                y: lane.dy - width / 2
                Behavior on width { NumberAnimation { duration: Theme.durFast } }
            }
            Rectangle {
                visible: lane.chosen
                width: 30
                height: 30
                radius: 15
                color: "transparent"
                border.width: 1.5
                border.color: Qt.rgba(lane.tint.r, lane.tint.g, lane.tint.b, 0.45)
                x: root.deptX - 15
                y: lane.dy - 15
            }

            Txt {
                id: deptLabel
                text: lane.modelData.name
                color: lane.on ? Theme.ink : Theme.faint
                font.pixelSize: Theme.fBody
                font.weight: lane.chosen ? Font.DemiBold : Font.Normal
                x: root.deptX - (lane.chosen ? 24 : 16) - width
                y: lane.dy - height / 2
            }
            Txt {
                text: lane.modelData.admins.length === 0
                      ? "no Admin"
                      : lane.modelData.admins.length + (lane.modelData.admins.length > 1 ? " Admins" : " Admin")
                color: lane.modelData.admins.length === 0 && lane.on ? Theme.danger : Theme.faint
                font.pixelSize: Theme.fSmall
                x: root.deptX - (lane.chosen ? 24 : 16) - width
                y: lane.dy + 11
            }

            MouseArea {
                x: root.deptX - 130
                y: lane.dy - 17
                width: 160
                height: 36
                cursorShape: Qt.PointingHandCursor
                onClicked: root.picked(lane.modelData.department_id)
            }
        }
    }

    Rectangle {
        width: 20
        height: 20
        radius: 10
        color: Theme.ink
        x: root.rootX - 10
        y: root.height / 2 - 10
        MouseArea {
            anchors.fill: parent
            anchors.margins: -12
            cursorShape: Qt.PointingHandCursor
            onClicked: root.picked(0)
        }
    }
    Txt {
        text: "you"
        color: Theme.dim
        font.pixelSize: Theme.fMeta
        x: root.rootX - width / 2
        y: root.height / 2 + 16
    }
}
