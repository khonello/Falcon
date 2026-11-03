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
    // CSS's line box, as the concept sets it (line-height 1.5): every line is 1.5 times the size, the text in the middle
    // of it. Qt puts a line's extra height under the text, so the padding moves it down by half and gives it back below.
    property real lh: 1.5
    lineHeightMode: Text.FixedHeight
    lineHeight: font.pixelSize * lh
    topPadding: (font.pixelSize * lh - font.pixelSize * 1.3) / 2
    bottomPadding: -topPadding
}
