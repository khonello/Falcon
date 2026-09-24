import QtQuick
import QtQuick.Controls
import "."

// The whole fleet as one strip, answering one question: which machines nobody signed in to. The
// used ones stay faded, so the proportion is the shape -- and the answer is NAMED underneath,
// because a number stamped in a square repeats across departments (OPS-01, FIN-01, LOG-01) and
// would say nothing.
Column {
    id: root

    property var hosts: []                  // [{ hostname, quiet }] in a stable order
    property int gap: 6
    property int maxSize: 28
    readonly property var quiet: hosts.filter(function (h) { return h.quiet })
    readonly property int size: Math.max(12, Math.min(maxSize,
        Math.floor((width - (hosts.length - 1) * gap) / Math.max(1, hosts.length))))

    spacing: 12

    Row {
        spacing: root.gap

        Repeater {
            model: root.hosts
            delegate: Rectangle {
                required property var modelData
                width: root.size
                height: root.size
                radius: Math.round(root.size * 0.25)
                color: modelData.quiet ? Theme.warn : Theme.line
                opacity: modelData.quiet ? 0.9 : 0.4

                ToolTip.visible: area.containsMouse
                ToolTip.text: modelData.hostname + (modelData.quiet ? " — never signed in" : " — used today")
                MouseArea { id: area; anchors.fill: parent; hoverEnabled: true }
            }
        }
    }

    // named, not numbered -- and past four the list stops being a list and becomes a count
    Txt {
        width: parent.width
        visible: root.quiet.length > 0
        text: {
            var names = root.quiet.map(function (h) { return h.hostname })
            if (names.length <= 4) return names.join(", ")
            return names.slice(0, 3).join(", ") + " and " + (names.length - 3) + " more"
        }
        color: Theme.faint
        monospace: true
        font.pixelSize: Theme.fMeta
        elide: Text.ElideRight
    }
}
