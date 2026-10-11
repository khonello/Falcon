import QtQuick
import "."

// A state: a round dot and a few words. `c` is the dot's colour; the words stay in ordinary ink.
// `square` draws the dot as a small square, which is how severity is marked.
Row {
    id: root
    property string text: ""
    property color c: Theme.text4
    property bool square: false
    property bool breathe: false
    property int size: Theme.fBody
    property color textColor: Theme.text
    spacing: 6

    Rectangle {
        width: root.square ? 8 : 7
        height: width
        radius: root.square ? 2 : width / 2
        color: root.c
        anchors.verticalCenter: parent.verticalCenter
        SequentialAnimation on opacity {
            running: root.breathe
            loops: Animation.Infinite
            NumberAnimation { to: 0.35; duration: 600 }
            NumberAnimation { to: 1; duration: 600 }
        }
    }
    Txt {
        text: root.text
        color: root.textColor
        font.pixelSize: root.size
        anchors.verticalCenter: parent.verticalCenter
        elide: Text.ElideNone
    }
}
