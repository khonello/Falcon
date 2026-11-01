import QtQuick
import "."

// ONE DEPARTMENT TASK, LEFT TO RIGHT: given, seen, under way, done by the department, completed by you.
// A lane per Admin told, filled as far as that Admin has got; only the Super User takes it to the last step.
Item {
    id: root
    property var task: null
    readonly property var adm: task ? (task.admins || []) : []
    readonly property var steps: ["Given", "Seen", "Under way", "Done", "Completed by you"]
    readonly property var order: ["told", "seen", "ongoing", "done"]
    readonly property int lw: 130
    readonly property int rh: 40
    readonly property int topY: 30
    implicitHeight: topY + adm.length * rh + 8
    function xAt(i) { return lw + 10 + (i / 4) * (width - lw - 90) }
    readonly property bool late: task ? Time.past(task.deadline_at) : false
    readonly property bool anyDone: adm.some(function (a) { return a.state === "done" })

    onTaskChanged: cv.requestPaint()
    onWidthChanged: cv.requestPaint()
    Connections { target: Theme; function onDarkChanged() { cv.requestPaint() } }
    Repeater {
        model: root.steps
        Txt { required property var modelData; required property int index; x: root.xAt(index) - implicitWidth / 2; y: 2; text: modelData
              color: index === 4 ? Theme.text : Theme.text3; font.weight: index === 4 ? Font.DemiBold : Font.Normal; font.pixelSize: 12; elide: Text.ElideNone }
    }
    Repeater {
        model: root.adm
        Txt { required property var modelData; required property int index; x: 0; y: root.topY + index * root.rh + root.rh / 2 - 9; text: modelData.name; width: root.lw - 8 }
    }
    Repeater {
        model: root.adm
        Txt { required property var modelData; required property int index
              readonly property int k: root.order.indexOf(modelData.state)
              visible: !!modelData.state_at; x: root.xAt(k) + 11; y: root.topY + index * root.rh + root.rh / 2 - 22
              text: modelData.state_at ? Time.atDay(modelData.state_at) : ""; mono: true; color: Theme.text3; font.pixelSize: 10; elide: Text.ElideNone }
    }
    Canvas {
        id: cv
        anchors.fill: parent
        onPaint: {
            var c = getContext("2d"); c.reset()
            var H = height
            for (var i = 0; i < 5; i++) { c.strokeStyle = Theme.grid; c.beginPath(); c.moveTo(root.xAt(i) + 0.5, 22); c.lineTo(root.xAt(i) + 0.5, H - 6); c.stroke() }
            root.adm.forEach(function (a, j) {
                var k = root.order.indexOf(a.state), y = root.topY + j * root.rh + root.rh / 2
                var col = k === 3 ? Theme.ok : root.late ? Theme.crit : Theme.accent
                c.strokeStyle = Theme.borderStrong; c.lineWidth = 2; c.beginPath(); c.moveTo(root.xAt(0), y); c.lineTo(root.xAt(3), y); c.stroke()
                if (k > 0) { c.strokeStyle = col; c.lineWidth = 3; c.beginPath(); c.moveTo(root.xAt(0), y); c.lineTo(root.xAt(k), y); c.stroke() }
                for (var i = 0; i < 4; i++) {
                    c.lineWidth = 1.75; c.strokeStyle = i <= k ? col : Theme.text4; c.fillStyle = i === k ? col : Theme.surface
                    c.beginPath(); c.arc(root.xAt(i), y, i === k ? 6.5 : 4, 0, Math.PI * 2); c.fill(); c.stroke()
                }
                if (k === 3) { c.strokeStyle = Theme.ok; c.lineWidth = 1.5; c.setLineDash([4, 4]); c.beginPath(); c.moveTo(root.xAt(3) + 8, y); c.lineTo(root.xAt(4) - 10, y); c.stroke(); c.setLineDash([]) }
            })
            var cy = root.topY + (root.adm.length * root.rh) / 2
            c.lineWidth = 1.75; c.strokeStyle = root.anyDone ? Theme.ok : Theme.text4; c.fillStyle = root.anyDone ? Theme.mix(Theme.ok, Theme.surface, 0.18) : Theme.surface
            c.beginPath(); c.arc(root.xAt(4), cy, 9, 0, Math.PI * 2); c.fill(); c.stroke()
        }
    }
}
