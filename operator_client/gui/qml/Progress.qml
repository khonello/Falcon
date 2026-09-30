import QtQuick
import "."

// HOW FAR THROUGH SOMETHING IS. A real bar that fills, never a stripe on an edge, and it carries the
// figure beside it because a bar alone cannot be read off exactly.
Item {
    id: root
    property real value: 0                // 0..1
    property string tone: "accent"
    property bool showNumber: true
    property string caption: ""

    implicitWidth: 200
    implicitHeight: showNumber || caption !== "" ? 20 : 6

    Rectangle {
        id: track
        anchors.left: parent.left
        anchors.right: figure.visible ? figure.left : parent.right
        anchors.rightMargin: figure.visible ? Theme.s2 : 0
        anchors.verticalCenter: parent.verticalCenter
        height: 6
        radius: 3
        color: Theme.fillStrong

        Rectangle {
            width: parent.width * Math.max(0, Math.min(1, root.value))
            height: parent.height
            radius: parent.radius
            color: Theme.tone(root.tone)
            Behavior on width { NumberAnimation { duration: Theme.durBase } }
        }
    }
    Txt {
        id: figure
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        visible: root.showNumber
        text: Math.round(root.value * 100) + "%"
        tone: "mid"
        mono: true
        font.pixelSize: Theme.fSmall
    }
}
