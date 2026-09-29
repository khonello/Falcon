import QtQuick
import "."

// SOURCE, THEN WHERE IT LANDS, AND WHERE IT BROKE. A flow runs one direction, so the picture does
// too: left to right, one line per destination. The nodes are filled like every other card -- the
// source one step darker, a broken destination a tinted fill rather than a red ring -- and only the
// link to a broken one is drawn red and dashed (docs/UI.md).
Item {
    id: root

    property string source: ""            // hostname
    property string sourcePath: ""
    property var destinations: []         // the flow's destinations, as the Engine sends them
    property int nodeHeight: 52
    // the nodes give way to the links, not the other way round: in a drawer there is not
    // much room, and a picture with no space between its parts is not a picture
    readonly property int nodeWidth: Math.min(190, Math.max(120, width * 0.40))
    property int gap: 18

    readonly property int rows: Math.max(1, destinations.length)
    implicitHeight: rows * nodeHeight + (rows - 1) * gap

    function broken(d) { return !!(d && d.suggestion) }

    // --- the links, behind the nodes --------------------------------------------------------------
    Canvas {
        id: wires
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var x1 = root.nodeWidth
            var x2 = width - root.nodeWidth
            var y1 = height / 2
            for (var i = 0; i < root.destinations.length; i++) {
                var y2 = i * (root.nodeHeight + root.gap) + root.nodeHeight / 2
                var bad = root.broken(root.destinations[i])
                ctx.beginPath()
                ctx.moveTo(x1, y1)
                ctx.bezierCurveTo((x1 + x2) / 2, y1, (x1 + x2) / 2, y2, x2, y2)
                ctx.lineWidth = bad ? 2 : 1
                ctx.strokeStyle = bad ? "#cf1322" : "#d9d9d9"
                ctx.setLineDash(bad ? [5, 4] : [])
                ctx.stroke()
            }
        }
    }
    onDestinationsChanged: wires.requestPaint()
    onWidthChanged: wires.requestPaint()
    onHeightChanged: wires.requestPaint()

    // --- the source: one step darker, because everything starts there ------------------------------
    Rectangle {
        width: root.nodeWidth - Theme.s3
        height: root.nodeHeight
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        radius: Theme.radius
        color: Theme.fillStrong
        border.width: 1
        border.color: Theme.border

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: Theme.s2
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1
            Txt {
                width: parent.width
                text: root.source || "the source"
                mono: true
                strong: true
                font.pixelSize: Theme.fSmall
            }
            Txt {
                width: parent.width
                text: Sync.folder(root.sourcePath)
                tone: "mid"
                font.pixelSize: 11
            }
        }
    }

    // --- where it lands ----------------------------------------------------------------------------
    Column {
        anchors.right: parent.right
        anchors.top: parent.top
        width: root.nodeWidth - Theme.s3
        spacing: root.gap

        Repeater {
            model: root.destinations
            delegate: Rectangle {
                required property var modelData
                readonly property bool bad: root.broken(modelData)

                width: parent.width
                height: root.nodeHeight
                radius: Theme.radius
                color: bad ? Theme.dangerSoft : Theme.fill
                border.width: 1
                border.color: bad ? "#ffccc7" : Theme.split

                Column {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: Theme.s2
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1
                    Txt {
                        width: parent.width
                        text: modelData.destination_hostname || "remote storage"
                        mono: true
                        strong: true
                        tone: parent.parent.bad ? "danger" : "ink"
                        font.pixelSize: Theme.fSmall
                    }
                    Txt {
                        width: parent.width
                        text: Sync.folder(modelData.destination_path)
                        tone: parent.parent.bad ? "danger" : "mid"
                        font.pixelSize: 11
                    }
                }
            }
        }
    }
}
