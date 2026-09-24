import QtQuick
import QtQuick.Controls
import "."

// A day on every PC: who held each session, and for how long. One lane per PC, so a PC nobody
// signed into is an empty lane rather than a missing row -- absence is information here.
Item {
    id: root

    property var lanes: []                 // [{ name, hostname?, blocks: [{ state, from, to, label }] }]
                                           // -- from/to in hours; hostname is drawn when there is room
    property real fromHour: 8
    property real toHour: 18
    property int labelWidth: 66
    property int laneHeight: 22
    property int laneGap: 10
    property int tickStep: 2

    readonly property real plot: Math.max(40, width - labelWidth - 8)
    readonly property real lanesHeight: lanes.length * (laneHeight + laneGap)

    function stateColor(s) {
        return s === "traversal" ? Theme.warn : s === "super_user" ? Theme.danger
             : s === "assisted_access" ? Theme.accent : Theme.line2
    }
    function atHour(h) { return labelWidth + ((h - fromHour) / Math.max(0.5, toHour - fromHour)) * plot }

    implicitHeight: lanesHeight + 24

    // the hours, as quiet rules behind the lanes
    Repeater {
        model: Math.floor((root.toHour - root.fromHour) / root.tickStep) + 1
        delegate: Item {
            required property int index
            readonly property real h: root.fromHour + index * root.tickStep
            anchors.fill: parent

            Rectangle {
                x: root.atHour(parent.h)
                y: 4
                width: 1
                height: root.lanesHeight
                color: Theme.line
            }
            Txt {
                text: (parent.h < 10 ? "0" : "") + Math.floor(parent.h)
                color: Theme.faint
                monospace: true
                font.pixelSize: Theme.fSmall
                x: root.atHour(parent.h) - width / 2
                y: root.lanesHeight + 6
            }
        }
    }

    Column {
        width: parent.width
        spacing: root.laneGap

        Repeater {
            model: root.lanes
            delegate: Item {
                id: lane
                required property var modelData
                width: root.width
                height: root.laneHeight

                Txt {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    // the machine's name takes its own column when the lane is wide enough to
                    // carry one: opened, a lane has to say WHICH machine, not only whose it is
                    width: root.labelWidth - (host.visible ? host.width + 16 : 8)
                    text: lane.modelData.name
                    color: lane.modelData.blocks.length > 0 ? Theme.dim : Theme.faint
                    font.pixelSize: Theme.fBody
                    elide: Text.ElideRight
                }
                Txt {
                    id: host
                    anchors.right: parent.left
                    anchors.rightMargin: -(root.labelWidth - 10)
                    anchors.verticalCenter: parent.verticalCenter
                    visible: !!lane.modelData.hostname && root.labelWidth >= 96
                    text: lane.modelData.hostname || ""
                    color: Theme.faint
                    monospace: true
                    font.pixelSize: Theme.fSmall
                }
                Rectangle {
                    x: root.labelWidth
                    width: root.plot
                    height: parent.height
                    radius: 6
                    color: Theme.pane
                    opacity: 0.5
                }
                Repeater {
                    model: lane.modelData.blocks
                    delegate: Rectangle {
                        required property var modelData
                        x: root.atHour(Math.max(root.fromHour, modelData.from))
                        width: Math.max(4, root.atHour(Math.min(root.toHour, modelData.to)) - x - 2)
                        height: lane.height
                        radius: 6
                        color: root.stateColor(modelData.state)

                        ToolTip.visible: area.containsMouse && !!modelData.label
                        ToolTip.text: modelData.label || ""
                        MouseArea { id: area; anchors.fill: parent; hoverEnabled: true }
                    }
                }
            }
        }
    }
}
