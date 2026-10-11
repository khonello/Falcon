import QtQuick
import "."

// A link in running text: accent, no underline, a pointer on hover. `quiet` is grey.
Txt {
    id: root
    property bool quiet: false
    signal clicked()
    color: quiet ? Theme.text3 : area.containsMouse ? Qt.lighter(Theme.accent, 1.15) : Theme.accent
    elide: Text.ElideNone
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
