import QtQuick
import "."

// Density 4: a reading panel. One sentence, the facts that back it on one line each, and at most
// one action. The words come from `core/narrate.py` through `falcon.narrate(topic, data)` -- they
// are generated from the same data the charts drew, never written here.
//
// A panel is never blank: with nothing to report it still reports that, in the same shape.
Panel {
    id: root

    density: 4                              // a reading panel is the end of a page, always
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

    ReadingBody {
        width: parent.width
        narration: root.narration
        maxFacts: root.maxFacts
        onActionTriggered: root.actionTriggered()
    }
}
