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
    // the concept's mono is 12.5px; Qt has only whole pixels, so 13 with the 12.5's advance keeps columns of hosts and times in line
    Component.onCompleted: if (mono && font.pixelSize === 13) font.letterSpacing = -0.3
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
