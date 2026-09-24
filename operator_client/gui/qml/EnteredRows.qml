import QtQuick
import "."

// Who was on a machine that is not their own, and when. One line each, read as a sentence:
// someone, an arrow, the machine, the time. A body row is one line, and this is a body row.
Column {
    id: root

    property var entries: []               // [{ who, hostname, at, tone, open }]
    property int maxRows: 4

    spacing: 0

    Repeater {
        model: root.entries.slice(0, root.maxRows)
        delegate: Item {
            required property var modelData
            width: parent.width
            height: 30

            Rectangle {
                id: dot
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: 11
                height: 11
                radius: 6
                color: Theme.tone(modelData.tone)
            }
            Txt {
                anchors.left: dot.right
                anchors.leftMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: 92
                text: modelData.who
                elide: Text.ElideRight
                font.pixelSize: Theme.fBody
            }
            // the arrow says the direction of the entry, which is the whole point of the row
            Txt {
                id: arrow
                x: 118
                anchors.verticalCenter: parent.verticalCenter
                text: "→"
                color: Theme.line2
                font.pixelSize: Theme.fBody
            }
            Txt {
                anchors.left: arrow.right
                anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: modelData.hostname
                color: Theme.dim
                monospace: true
                font.pixelSize: Theme.fMeta
            }
            Txt {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: modelData.open ? (modelData.at + " · open") : modelData.at
                color: modelData.open ? Theme.warn : Theme.faint
                monospace: true
                font.pixelSize: Theme.fMeta
            }
        }
    }
}
