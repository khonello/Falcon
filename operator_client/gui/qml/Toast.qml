import QtQuick
import "."

// Where a `Msg` lands: top centre, one line each, gone on its own. It never asks for a click, so it
// never carries an act -- anything that needs answering is a Modal, not this.
Item {
    id: root
    property int life: 3600
    readonly property int count: queue.count

    ListModel { id: queue }

    Connections {
        target: Msg
        function onPosted(text, kind) {
            queue.append({ text: text, kind: kind, until: Date.now() + root.life })
        }
    }

    // one ticker for the whole stack, rather than a timer riding on every line
    Timer {
        interval: 250
        repeat: true
        running: queue.count > 0
        onTriggered: {
            var now = Date.now()
            while (queue.count > 0 && queue.get(0).until <= now) queue.remove(0)
        }
    }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: Theme.s4
        spacing: Theme.s2

        Repeater {
            model: queue
            delegate: Item {
                id: cell
                required property string text
                required property string kind
                width: line.implicitWidth
                height: line.implicitHeight
                Alert {
                    id: line
                    width: parent.width
                    height: parent.height
                    kind: cell.kind
                    text: cell.text
                    color: Theme.surface                    // it floats over the page, so it is opaque
                    border.color: cell.kind === "danger" ? "#ffccc7"
                                  : cell.kind === "warn" ? "#ffe58f" : Theme.border
                }
                opacity: 0
                Component.onCompleted: opacity = 1
                Behavior on opacity { NumberAnimation { duration: Theme.durBase } }
            }
        }
    }
}
