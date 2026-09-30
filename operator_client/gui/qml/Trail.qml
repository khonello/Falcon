import QtQuick
import "."

// WHAT HAPPENED TO THIS ONE SUBJECT, newest first, down a line. Antd calls it a Timeline; this is
// called Trail because the console already has a DayTimeline and they are different things.
//
// The dots follow the ladder: grey unless somebody had to act. No coloured dot per kind.
Column {
    id: root
    property var items: []                // [{at, text, tone}]
    spacing: 0

    Repeater {
        model: root.items
        delegate: Item {
            required property var modelData
            required property int index
            width: root.width
            height: Math.max(34, line.implicitHeight + Theme.s2 * 2)

            Rectangle {
                x: 3
                y: index === 0 ? parent.height / 2 : 0
                width: 1
                height: index === root.items.length - 1 ? parent.height / 2 : parent.height
                color: Theme.split
            }
            Rectangle {
                x: 0
                y: parent.height / 2 - 3.5
                width: 7
                height: 7
                radius: 4
                color: modelData.tone ? Theme.tone(modelData.tone) : Theme.quiet
            }
            Txt {
                id: when
                anchors.left: parent.left
                anchors.leftMargin: Theme.s4
                anchors.verticalCenter: parent.verticalCenter
                width: 46
                text: modelData.at || ""
                tone: "quiet"
                mono: true
                font.pixelSize: Theme.fSmall
            }
            Txt {
                id: line
                anchors.left: when.right
                anchors.leftMargin: Theme.s2
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: modelData.text || ""
                tone: modelData.tone || "ink"
                font.pixelSize: Theme.fSmall
                wrapMode: Text.WordWrap
                elide: Text.ElideNone
            }
        }
    }
}
