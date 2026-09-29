import QtQuick
import "."

// A status word. Colour comes from the ladder and the word is always present -- never colour alone.
Rectangle {
    id: root
    property string text: ""
    property string tone: ""                 // "" = neutral; warn | danger | accent

    implicitWidth: label.implicitWidth + 2 * Theme.s2
    implicitHeight: 22
    radius: Theme.radiusSm
    color: root.tone === "" ? Theme.fillStrong : Theme.toneSoft(root.tone)

    Txt {
        id: label
        anchors.centerIn: parent
        text: root.text
        tone: root.tone === "" ? "mid" : root.tone
        font.pixelSize: Theme.fSmall
    }
}
