import QtQuick
import "."

// Deviations are moments, not quantities, so they are drawn on the day they happened on -- the same
// axis the sessions are drawn on, so the two read as one day. Each mark says itself on one line,
// and the lines alternate above and below the track, so two close marks never collide.
//
// Addressed is a hollow ring, logged is filled: the thing still needing you is the solid one.
Item {
    id: root

    property var marks: []                 // [{ at (hours), what, addressed }]
    property real fromHour: 8
    property real toHour: 18
    property int tickStep: 2
    property int padX: 10

    readonly property real plot: Math.max(40, width - padX * 2)
    readonly property int trackY: 34

    function atHour(h) { return padX + ((h - fromHour) / Math.max(0.5, toHour - fromHour)) * plot }
    function clock(h) {
        var hh = Math.floor(h), mm = Math.round((h - hh) * 60)
        return (hh < 10 ? "0" : "") + hh + ":" + (mm < 10 ? "0" : "") + mm
    }

    implicitHeight: 96

    // the hours, as quiet rules, with their numerals above the track
    Repeater {
        model: Math.floor((root.toHour - root.fromHour) / root.tickStep) + 1
        delegate: Item {
            required property int index
            readonly property real h: root.fromHour + index * root.tickStep
            anchors.fill: parent

            Rectangle {
                x: root.atHour(parent.h)
                y: root.trackY - 6
                width: 1
                height: 22
                color: Theme.line
            }
            Txt {
                text: (parent.h < 10 ? "0" : "") + Math.floor(parent.h)
                color: Theme.faint
                monospace: true
                font.pixelSize: Theme.fSmall
                x: root.atHour(parent.h) - width / 2
                y: root.trackY - 24
            }
        }
    }

    Rectangle {
        x: root.padX
        y: root.trackY
        width: root.plot
        height: 10
        radius: 5
        color: Theme.pane
        opacity: 0.5
    }

    Repeater {
        model: root.marks
        delegate: Item {
            required property var modelData
            required property int index
            readonly property color tint: modelData.addressed ? Theme.ok : Theme.warn
            readonly property real cx: root.atHour(modelData.at)
            readonly property real labelY: index % 2 === 0 ? root.trackY + 24 : root.trackY + 46
            anchors.fill: parent

            Rectangle {
                x: parent.cx - 7
                y: root.trackY - 2
                width: 14
                height: 14
                radius: 7
                color: modelData.addressed ? "transparent" : parent.tint
                border.width: 2
                border.color: parent.tint
            }
            Rectangle {
                x: parent.cx
                y: root.trackY + 13
                width: 1
                height: parent.labelY - root.trackY - 13
                color: parent.tint
                opacity: 0.5
            }
            Row {
                x: Math.min(parent.cx - 6, root.width - width)
                y: parent.labelY
                spacing: 7

                Txt {
                    text: modelData.what
                    font.pixelSize: Theme.fBody
                }
                Txt {
                    text: root.clock(modelData.at) + " · " + (modelData.addressed ? "addressed" : "logged")
                    color: Theme.faint
                    monospace: true
                    font.pixelSize: Theme.fMeta
                }
            }
        }
    }
}
