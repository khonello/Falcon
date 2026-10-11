import QtQuick
import "."

// "+24 more": nothing grows with the data, so a list shows a fixed number and counts the rest.
Rectangle {
    id: root
    property int n: 0
    property string what: ""
    signal clicked()
    visible: n > 0
    implicitWidth: t.implicitWidth + 16
    implicitHeight: 22
    radius: 4
    color: "transparent"
    border.width: 1
    border.color: area.containsMouse ? Theme.accent : Theme.borderStrong
    Txt {
        id: t
        anchors.centerIn: parent
        text: "+" + Theme.fmt(root.n) + " more" + (root.what ? " " + root.what : "")
        color: area.containsMouse ? Theme.accent : Theme.text3
        font.pixelSize: 11
        elide: Text.ElideNone
    }
    MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
