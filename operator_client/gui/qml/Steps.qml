import QtQuick
import "."

// WHERE YOU ARE IN SOMETHING THAT HAS AN ORDER. Only where the order is real -- a proposal that must
// be read before it is committed, a flow that must be described before it is checked. Never as
// decoration on a form that is one page.
Item {
    id: root
    property var steps: []                // [string]
    property int current: 0

    implicitHeight: 32

    Row {
        anchors.fill: parent
        spacing: 0

        Repeater {
            model: root.steps
            delegate: Item {
                required property var modelData
                required property int index
                readonly property bool done: index < root.current
                readonly property bool here: index === root.current
                width: root.width / root.steps.length
                height: root.height

                Rectangle {
                    id: pip
                    width: 22
                    height: 22
                    radius: 11
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    color: parent.here ? Theme.primary : parent.done ? Theme.primarySoft : Theme.fillStrong

                    Txt {
                        anchors.centerIn: parent
                        visible: !parent.parent.done
                        text: String(index + 1)
                        color: parent.parent.here ? Theme.onDark : Theme.mid
                        font.pixelSize: 11
                        strong: true
                    }
                    Icon {
                        anchors.centerIn: parent
                        visible: parent.parent.done
                        name: "check"
                        size: 13
                        color: Theme.primary
                    }
                }
                Txt {
                    anchors.left: pip.right
                    anchors.leftMargin: Theme.s2
                    anchors.right: rule.left
                    anchors.rightMargin: Theme.s2
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData
                    tone: parent.here ? "ink" : "mid"
                    strong: parent.here
                    font.pixelSize: Theme.fSmall
                }
                Rectangle {
                    id: rule
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: index === root.steps.length - 1 ? 0 : Theme.s4
                    height: 1
                    color: Theme.split
                }
            }
        }
    }
}
