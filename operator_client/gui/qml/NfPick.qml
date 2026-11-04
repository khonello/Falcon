import QtQuick
import "."

// One of a few choices, said in full (nfv-pick): a dot, what it is and what it means.
Rectangle {
    id: root
    property bool on: false
    property string title: ""
    property string desc: ""
    signal picked()
    width: parent ? parent.width : 0
    height: tc.height + 24 + 2
    radius: 8
    color: on ? Theme.mix(Theme.accent, Theme.surface2, 0.08) : Theme.surface2
    border.width: 1
    border.color: on ? Theme.accent : ma.containsMouse ? Theme.borderStrong : "transparent"
    Rectangle { x: 15; y: 15; width: 14; height: 14; radius: 7; color: "transparent"; border.width: root.on ? 4 : 1.5; border.color: root.on ? Theme.accent : Theme.borderStrong }
    Column {
        id: tc
        x: 41; y: 13
        width: parent.width - 56
        spacing: 2
        Txt { width: parent.width; text: root.title; font.pixelSize: 13; font.weight: Font.DemiBold }
        Txt { visible: root.desc !== ""; width: parent.width; text: root.desc; color: Theme.text3; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
    }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.picked() }
}
