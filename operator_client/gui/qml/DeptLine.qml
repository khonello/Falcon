import QtQuick
import "."

// One line in a department card: a dot for how it stands, what it is, and a few words at the right. A click opens it.
Rectangle {
    id: root
    property color dot: Theme.text4
    property string text: ""
    property string aside: ""
    property color asideTone: Theme.text3
    signal clicked()
    width: parent ? parent.width : 0
    height: 34
    color: ma.containsMouse ? Theme.surface2 : "transparent"
    radius: 4
    Rectangle { x: 6; width: 8; height: 8; radius: 2; color: root.dot; anchors.verticalCenter: parent.verticalCenter }
    Txt { x: 24; width: parent.width - 24 - tail.width - 14; anchors.verticalCenter: parent.verticalCenter; text: root.text }
    Txt { id: tail; anchors.right: parent.right; anchors.rightMargin: 6; anchors.verticalCenter: parent.verticalCenter; text: root.aside; color: root.asideTone; font.pixelSize: 12; elide: Text.ElideNone }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
