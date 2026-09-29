import QtQuick
import QtQuick.Shapes
import "."

// Department -> Admin -> its machines, drawn. Colour is the department and nothing else; the shape is
// the level. Picking a department descends into it: the same drawing with everything else quietened,
// so descent is a change of attention rather than a different picture.
//
// ONE MARK PER DEPARTMENT, never one per machine (design/PATTERNS.md 3a): a constellation of dots put
// every department's whole fleet in one container, which stops reading at twelve departments of sixty.
// Each department now carries a single 30 px screen holding its machine count, in the worst tone among
// them, with the reason in words. Machines are named only where a department is maximised.
Item {
    id: root

    property var departments: []           // hierarchy.tree's departments, in order
    property int focusId: 0                // 0 = the whole system
    property int selectedId: 0             // ringed, not recoloured: colour already means state
    // One gesture, one meaning (design/PATTERNS.md): a single click SELECTS a department and brings its
    // text beside the map; a double click ENTERS it, and only then does the crumb grow.
    signal picked(int departmentId)
    signal entered(int departmentId)

    // the drawing is centred in whatever width it is given, and the PC constellation spreads with
    // it -- otherwise a wide cell leaves the whole map hugging its left edge
    // markFor(dept) -> { label, status, line }: the department's one mark, from whoever owns the
    // machine state (Fleet). Without it the mark is a quiet count.
    property var markFor: null
    readonly property real baseDeptX: Math.max(150, width * 0.32)
    readonly property real basePcX: Math.max(baseDeptX + 110, width * 0.58)
    // the drawing runs you -> department -> its one mark, so the content ends at the mark plus its words
    readonly property real contentWidth: basePcX + 150
    readonly property real xOffset: Math.max(0, (width - contentWidth) / 2)
    readonly property real rootX: 46 + xOffset
    readonly property real deptX: baseDeptX + xOffset
    readonly property real pcX: basePcX + xOffset

    function deptY(i) { return height * (i + 1) / (departments.length + 1) }
    function lit(d) { return focusId === 0 || focusId === d.department_id }
    function tintOf(i) { return Theme.series(i) }
    function markOf(dept) {
        if (root.markFor) return root.markFor(dept)
        var n = dept && dept.workers ? dept.workers.length : 0
        return { label: String(n), status: n === 0 ? "free" : "ok", line: n === 1 ? "one machine" : n + " machines" }
    }

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
                // this department -> its machines, as one line to one mark
                ShapePath {
                    strokeColor: Qt.rgba(lane.tint.r, lane.tint.g, lane.tint.b, lane.on ? 0.30 : 0.08)
                    strokeWidth: 1.4
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    PathPolyline { path: root.curve(root.deptX + 9, lane.dy, root.pcX - 6, lane.dy) }
                }
            }

            MachineMark {
                readonly property var mark: root.markOf(lane.modelData)
                size: 30
                label: mark.label
                status: mark.status
                line: mark.line
                lineTone: mark.status === "danger" ? "danger" : mark.status === "warn" ? "warn" : ""
                opacity: lane.on ? 1 : 0.24
                x: root.pcX
                y: lane.dy - 14
                onDoubleClicked: root.entered(lane.modelData.department_id)
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
                onDoubleClicked: root.entered(lane.modelData.department_id)
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
