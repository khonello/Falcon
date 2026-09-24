import QtQuick
import "."

// Density 4: a reading panel. One sentence, the facts that back it on one line each, and at most
// one action. The words come from `core/narrate.py` through `falcon.narrate(topic, data)` -- they
// are generated from the same data the charts drew, never written here.
//
// A panel is never blank: with nothing to report it still reports that, in the same shape.
Panel {
    id: root

    property var narration: ({})            // {sentence, facts, action, state, note}
    // How many facts this panel has room for. The narrator may offer more; the panel decides, and
    // the action must never be the thing that falls off the bottom.
    property int maxFacts: 4
    signal actionTriggered()

    readonly property string sentence: narration.sentence || ""
    readonly property var facts: (narration.facts || []).slice(0, maxFacts)
    readonly property string actionLabel: narration.action || ""

    // A reading panel never takes the overlay notice a chart panel does: its content IS words, so
    // with nothing to report it simply says so. What it keeps instead is its shape -- the rules the
    // fact rows would have sat on, drawn quiet.

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

    Item { width: 1; height: 4; visible: root.facts.length > 0 }

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
