import QtQuick
import QtQuick.Controls
import "."

// A state in words, in its own colour, with a filled dot. Never clickable, so it cannot be
// confused with the button that changes the thing it describes. `pulse` for a state that wants
// attention until it is addressed (an indicator).
Rectangle {
    id: root
    property string text: ""
    property color tint: Theme.textFaint
    property bool muted: false
    property bool pulse: false

    implicitWidth: row.implicitWidth + Theme.space3 * 2
    implicitHeight: 22
    radius: 11
    color: root.muted ? "transparent" : Theme.wash(root.tint, 0.14)
    border.width: 1
    border.color: root.muted ? Theme.border : Theme.wash(root.tint, 0.55)

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        Rectangle {
            width: 6; height: 6; radius: 3
            anchors.verticalCenter: parent.verticalCenter
            color: root.muted ? Theme.textFaint : root.tint
            SequentialAnimation on opacity {
                running: root.pulse
                loops: Animation.Infinite
                NumberAnimation { to: 0.2; duration: 600; easing.type: Easing.InOutQuad }
                NumberAnimation { to: 1.0; duration: 600; easing.type: Easing.InOutQuad }
            }
        }
        Label {
            text: root.text
            color: root.muted ? Theme.textFaint : root.tint
            font.pixelSize: Theme.fontTiny
            font.bold: true
            font.letterSpacing: 0.6
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
