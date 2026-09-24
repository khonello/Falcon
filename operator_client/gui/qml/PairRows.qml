import QtQuick
import "."

// Assistance, treatment A from board C06: one line per pair, read as a sentence. It is the default
// because most days the honest answer is "nobody helped anybody", and a diagram is a heavy
// instrument for a mostly-empty fact. The arc diagram is the alternative, not the default.
Column {
    id: root

    property var pairs: []                  // [{ from_name, to_name, count, tint }]
    spacing: 0

    Repeater {
        model: root.pairs
        delegate: Item {
            required property var modelData
            readonly property bool never: modelData.count === 0
            width: root.width
            height: 34

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 9

                Rectangle {
                    width: 10; height: 10; radius: 5
                    color: modelData.fromTint
                    opacity: never ? 0.3 : 1
                    anchors.verticalCenter: parent.verticalCenter
                }
                Txt {
                    text: modelData.from_name
                    color: never ? Theme.faint : Theme.ink
                    font.pixelSize: Theme.fBody
                    anchors.verticalCenter: parent.verticalCenter
                }
                Icon {
                    name: "fwd"
                    color: Theme.line2
                    size: 13
                    anchors.verticalCenter: parent.verticalCenter
                }
                Rectangle {
                    width: 10; height: 10; radius: 5
                    color: modelData.toTint
                    opacity: never ? 0.3 : 1
                    anchors.verticalCenter: parent.verticalCenter
                }
                Txt {
                    text: modelData.to_name
                    color: never ? Theme.faint : Theme.ink
                    font.pixelSize: Theme.fBody
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Txt {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: never ? "never"
                            : modelData.count + (modelData.count === 1 ? " session" : " sessions")
                color: Theme.faint
                font.pixelSize: Theme.fMeta
            }
        }
    }
}
