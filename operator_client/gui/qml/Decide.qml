import QtQuick
import "."

// What confirming does (.decide): one line in a tinted box.
Rectangle {
    id: root
    property string text: ""
    property color c: Theme.accent
    width: parent ? parent.width : 0
    height: t.height + 24 + 2
    radius: 6
    color: Theme.alpha(c, 0.09)
    border.width: 1
    border.color: Theme.alpha(c, 0.35)
    Txt { id: t; x: 15; y: 13; width: parent.width - 30; text: root.text; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
}
