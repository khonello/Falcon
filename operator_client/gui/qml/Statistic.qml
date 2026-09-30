import QtQuick
import "."

// ONE FIGURE, SAID ONCE. A figure earns a tile only when somebody acts on the number itself -- how
// many machines are behind, how many people are waiting. A number nobody acts on is a sentence.
Column {
    id: root
    property string label: ""
    property string value: ""
    property string unit: ""
    property string tone: ""              // "" | warn | danger
    property string note: ""

    spacing: 2

    Txt { text: root.label; tone: "mid"; font.pixelSize: Theme.fSmall }
    Row {
        spacing: Theme.s1 + 2
        Txt {
            text: root.value
            tone: root.tone === "" ? "ink" : root.tone
            font.pixelSize: 26
            font.weight: Font.DemiBold
            anchors.bottom: parent.bottom
        }
        Txt {
            text: root.unit
            tone: "quiet"
            font.pixelSize: Theme.fSmall
            visible: root.unit !== ""
            anchors.bottom: parent.bottom
            bottomPadding: 5
        }
    }
    Txt {
        text: root.note
        tone: "quiet"
        font.pixelSize: 11
        visible: root.note !== ""
    }
}
