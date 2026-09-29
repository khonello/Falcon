import QtQuick
import "."

// Label left, value right, read straight down (docs/UI.md rule 0). Never a two-column grid: that
// makes you hunt for which value belongs to which label.
Column {
    id: root
    property var items: []                   // [{ label, value, tone, mono, tag }]
    spacing: 0

    Repeater {
        model: root.items
        delegate: Item {
            required property var modelData
            width: parent.width
            height: 34

            Txt {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: modelData.label
                tone: "mid"
                font.pixelSize: Theme.fSmall
            }
            Txt {
                visible: !modelData.tag
                anchors.right: parent.right
                anchors.left: parent.left
                anchors.leftMargin: 120
                anchors.verticalCenter: parent.verticalCenter
                horizontalAlignment: Text.AlignRight
                text: modelData.value === undefined ? "" : String(modelData.value)
                tone: modelData.tone || "ink"
                mono: !!modelData.mono
                font.pixelSize: modelData.mono ? Theme.fSmall : Theme.fBody
            }
            Tag {
                visible: !!modelData.tag
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: modelData.value === undefined ? "" : String(modelData.value)
                tone: modelData.tone || ""
            }
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.split
            }
        }
    }
}
