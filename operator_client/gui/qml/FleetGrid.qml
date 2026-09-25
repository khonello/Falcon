import QtQuick
import "."

// A department's client PCs, at whatever size the department turns out to be.
//
// THE MARK SHRINKS WHILE SHRINKING STILL SAYS SOMETHING, AND PAST THAT THE DRAWING CHANGES KIND.
// Never a scrollbar: a chart you have to scroll has stopped answering "how many, how healthy" in one
// look, and it breaks the rule that a count is drawn against the largest, because you can no longer
// see the largest. This mirrors `slot_size()` in design/scale.py -- keep the two in step.
//
//   <=  8   46 px, the hostname inside the slot   -- every machine readable
//   <= 30   30 px, no labels                      -- every machine countable
//   <= 120  16 px, dense                          -- proportion and outliers
//   >  120  one bar per state                     -- the shape of the fleet, exceptions named
//
// Which machine and what is wrong with it is the maximised view's job (Its machines, opened), which
// is why this panel drops the names rather than trying to keep them.
Item {
    id: root

    property var hosts: []                  // [{ hostname, state }], state a tone name
    property int gap: 6
    // Maximised, the panel has the room the cell did not: every mark goes back to 46 px and carries
    // its hostname again. That is the whole argument for maximising rather than recomposing.
    property bool forceLabels: false
    readonly property int count: hosts.length
    readonly property int slot: forceLabels ? 46
                              : count <= 8 ? 46 : count <= 30 ? 30 : count <= 120 ? 16 : 0
    readonly property bool labelled: forceLabels || count <= 8
    readonly property bool asBars: slot === 0 && !forceLabels

    implicitHeight: asBars ? bars.implicitHeight : flow.implicitHeight

    function tally(state) {
        var n = 0
        for (var i = 0; i < hosts.length; i++) if (hosts[i].state === state) n++
        return n
    }

    Flow {
        id: flow
        visible: !root.asBars
        width: parent.width
        spacing: root.count > 30 ? 3 : root.gap

        Repeater {
            model: root.asBars ? 0 : root.hosts
            delegate: Rectangle {
                required property var modelData
                width: root.slot
                height: root.slot
                radius: Math.max(3, Math.floor(root.slot / 3.5))
                color: Theme.tone(modelData.state || "ok")
                opacity: 0.92

                Txt {
                    visible: root.labelled
                    anchors.centerIn: parent
                    text: String(modelData.hostname || "").split("-").pop()
                    color: Theme.chartBg
                    font.pixelSize: 14
                    font.weight: Font.Medium
                    monospace: true
                }
            }
        }
    }

    // Past the point where one mark per machine says anything, the fleet is drawn as its shape.
    Column {
        id: bars
        visible: root.asBars
        width: parent.width
        spacing: 8

        Repeater {
            model: [ { key: "ok", label: "Confirmed" }, { key: "warn", label: "Behind" },
                     { key: "danger", label: "Out of place" } ]
            delegate: Item {
                required property var modelData
                readonly property int n: root.tally(modelData.key)
                visible: n > 0
                width: bars.width
                height: visible ? 30 : 0

                Txt {
                    id: lbl
                    text: modelData.label
                    color: Theme.dim
                    font.pixelSize: Theme.fMeta
                }
                Txt {
                    anchors.right: parent.right
                    text: String(parent.n)
                    color: Theme.faint
                    font.pixelSize: Theme.fMeta
                    monospace: true
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width * (root.count > 0 ? parent.n / root.count : 0)
                    height: 10
                    radius: 5
                    color: Theme.tone(modelData.key)
                    opacity: 0.92
                }
            }
        }
    }
}
