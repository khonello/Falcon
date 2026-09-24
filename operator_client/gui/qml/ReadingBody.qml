import QtQuick
import "."

// Density 4, without a panel around it: one sentence, the facts that back it on one line each, and
// at most one action. Used inside a Panel (ReadingPanel) on a page, and inside a GridCell on the
// Overview, so the reading looks the same wherever it lands.
//
// With nothing to report it still reports that, and keeps the rules its fact rows would have sat on.
Column {
    id: root

    property var narration: ({})
    property int maxFacts: 4
    signal actionTriggered()

    readonly property string sentence: narration.sentence || ""
    readonly property var facts: (narration.facts || []).slice(0, maxFacts)
    readonly property string actionLabel: narration.action || ""

    spacing: 10

    Txt {
        width: parent.width
        text: root.sentence
        color: Theme.ink
        font.pixelSize: Theme.fSection
        font.weight: Font.DemiBold
        wrapMode: Text.WordWrap
        elide: Text.ElideNone
        lineHeight: 1.3
        visible: text !== ""
    }

    Item { width: 1; height: 4 }

    Column {
        width: parent.width
        spacing: 0
        visible: root.facts.length > 0

        Repeater {
            model: root.facts
            delegate: Item {
                required property var modelData
                width: parent.width
                height: 32

                Txt {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label
                    color: Theme.dim
                    font.pixelSize: Theme.fBody
                }
                Txt {
                    anchors.right: parent.right
                    anchors.left: parent.left
                    anchors.leftMargin: 110
                    anchors.verticalCenter: parent.verticalCenter
                    horizontalAlignment: Text.AlignRight
                    text: modelData.value
                    color: modelData.tone === "" ? Theme.ink : Theme.tone(modelData.tone)
                    font.pixelSize: Theme.fBody
                    font.weight: Font.Medium
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.line
                }
            }
        }
    }

    // the bones of the rows that are not there
    Column {
        width: parent.width
        spacing: 0
        visible: root.facts.length === 0 && root.sentence !== ""
        opacity: 0.35

        Repeater {
            model: 3
            delegate: Item {
                width: parent.width
                height: 32
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.line
                }
            }
        }
    }

    Item { width: 1; height: 6; visible: root.actionLabel !== "" }

    TBtn {
        text: root.actionLabel
        tone: "accent"
        visible: root.actionLabel !== ""
        onClicked: root.actionTriggered()
    }
}
