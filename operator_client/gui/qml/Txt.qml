import QtQuick
import "."

// Typography. `tone` picks the weight of ink; `mono` is for hostnames, versions and times.
Text {
    id: root
    property string tone: "ink"             // ink | mid | quiet | accent | warn | danger
    property bool mono: false
    property bool strong: false

    color: Theme.tone(root.tone === "ink" ? "ink" : root.tone)
    font.family: mono ? Theme.mono : Theme.sans
    font.pixelSize: Theme.fBody
    font.weight: strong ? Font.DemiBold : Font.Normal
    renderType: Text.NativeRendering
    elide: Text.ElideRight
    verticalAlignment: Text.AlignVCenter
}
