import QtQuick
import QtQuick.Shapes
import "."

// ONE MACHINE, drawn as what it is: a small screen with its number on it (design/PATTERNS.md section 2).
//
// Quiet when fine -- a faint outline and a dim number. When it needs someone, the outline and the number take
// the tone; nothing else changes, and never a dot. 'free' (unused) is only fainter: unused is not a problem.
// The reason is WORDS beneath the mark (name, then line), never a colour alone.
//
// Sizes that work: 84 in a page's hero row, 58 maximised or in a grid, 30-44 beside text, 24 in a line.
Item {
    id: root

    property string label: ""               // the number inside ("07"), or a count ("12") for a department's mark
    property string status: "ok"            // ok | free | warn | danger | entered
    property int size: 58
    property string name: ""                // beneath: who, or the hostname
    property string line: ""                // beneath that: why, in words
    property string lineTone: ""            // tone name for the line; "" = faint

    readonly property color toneColor: status === "warn" || status === "entered" ? Theme.warn
                                     : status === "danger" ? Theme.danger : "transparent"
    readonly property bool needsSomeone: status === "warn" || status === "entered" || status === "danger"
    readonly property int screenH: Math.round(size * 0.66)
    readonly property color stroke: needsSomeone ? toneColor : Qt.rgba(1, 1, 1, 0.30)

    implicitWidth: (name !== "" || line !== "") ? Math.max(size, size + 34) : size
    implicitHeight: screenH + 9 + (name !== "" ? 18 : 0) + (line !== "" ? 15 : 0)

    Item {
        id: mark
        width: root.size
        height: root.screenH + 9
        anchors.horizontalCenter: parent.horizontalCenter
        opacity: root.status === "free" ? 0.45 : 1

        Shape {
            anchors.fill: parent
            antialiasing: true
            layer.enabled: true
            layer.samples: 4
            ShapePath {
                strokeColor: root.stroke
                strokeWidth: 1.5
                fillColor: Qt.rgba(1, 1, 1, 0.03)
                PathRectangle {
                    x: 1; y: 1
                    width: root.size - 2; height: root.screenH - 2
                    radius: Math.max(3, root.size * 0.1)
                }
            }
            ShapePath {
                strokeColor: root.stroke
                strokeWidth: 1.5
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                startX: root.size / 2; startY: root.screenH
                PathLine { x: root.size / 2; y: root.screenH + 5 }
                PathMove { x: root.size / 2 - root.size * 0.18; y: root.screenH + 7 }
                PathLine { x: root.size / 2 + root.size * 0.18; y: root.screenH + 7 }
            }
        }
        Txt {
            objectName: "markLabel"
            width: root.size
            height: root.screenH
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            text: root.label
            visible: root.label !== ""
            monospace: true
            font.pixelSize: Math.max(9, Math.round(root.size * 0.24))
            font.weight: Font.DemiBold
            color: root.needsSomeone ? root.toneColor : Theme.dim
        }
    }

    Column {
        anchors.top: mark.bottom
        anchors.topMargin: 3
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 1
        Txt {
            anchors.horizontalCenter: parent.horizontalCenter
            visible: root.name !== ""
            text: root.name
            color: Theme.ink
            font.pixelSize: root.size >= 70 ? Theme.fRow - 1 : Theme.fMeta
            font.weight: Font.DemiBold
        }
        Txt {
            anchors.horizontalCenter: parent.horizontalCenter
            visible: root.line !== ""
            text: root.line
            color: root.lineTone === "" ? Theme.faint : Theme.tone(root.lineTone)
            font.pixelSize: Theme.fMeta - 1
            font.weight: root.lineTone === "" ? Font.Normal : Font.Medium
        }
    }
}
