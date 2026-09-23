import QtQuick
import "."

// One figure, large, with what it counts underneath. The tone is the only colour it carries.
Column {
    id: root

    property string value: ""
    property string label: ""
    property string sub: ""
    property string tone: ""

    spacing: 6

    Txt {
        text: root.value
        color: root.tone === "" ? Theme.ink : Theme.tone(root.tone)
        monospace: true
        font.pixelSize: 40
        font.weight: Font.DemiBold
    }
    Txt {
        text: root.label
        color: Theme.dim
        font.pixelSize: Theme.fBody
        font.weight: Font.Medium
    }
    Txt {
        text: root.sub
        visible: root.sub !== ""
        color: Theme.faint
        font.pixelSize: Theme.fMeta
    }
}
