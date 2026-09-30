import QtQuick
import "."

// THE ONE PLACE A TABLE IS WRONG: a conversation. Each message is a block, not a row, because the
// length of what somebody wrote is part of what they said.
Column {
    id: root
    property var items: []                // [{who, body, mine, at}]
    spacing: Theme.s3

    Repeater {
        model: root.items
        delegate: Column {
            required property var modelData
            width: root.width
            spacing: 2

            Row {
                spacing: Theme.s2
                Avatar {
                    name: modelData.mine ? "You" : (modelData.who || "?")
                    size: 20
                    muted: !modelData.mine
                    anchors.verticalCenter: parent.verticalCenter
                }
                Txt {
                    text: modelData.mine ? "You" : (modelData.who || "them")
                    tone: "mid"
                    font.pixelSize: 11
                    anchors.verticalCenter: parent.verticalCenter
                }
                Txt {
                    text: modelData.at || ""
                    tone: "quiet"
                    mono: true
                    font.pixelSize: 11
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            Rectangle {
                x: 28
                width: parent.width - 28
                height: body.contentHeight + 2 * Theme.s2
                radius: Theme.radius
                color: modelData.mine ? Theme.primarySoft : Theme.fill
                border.width: 1
                border.color: Theme.split

                Txt {
                    id: body
                    anchors.fill: parent
                    anchors.margins: Theme.s2
                    text: modelData.body || ""
                    wrapMode: Text.WordWrap
                    elide: Text.ElideNone
                    font.pixelSize: Theme.fSmall
                }
            }
        }
    }
}
