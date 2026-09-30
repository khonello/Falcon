import QtQuick
import QtQuick.Controls.Basic
import "."

// SOMETHING THAT SHOULD NOT SIT ON SCREEN IN THE CLEAR -- a client key being pasted in. It can be
// revealed, because a key nobody can check is a key typed wrong.
Item {
    id: root
    property alias text: field.text
    property string placeholder: ""
    property bool shown: false

    implicitWidth: 320
    implicitHeight: Theme.control

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: field.activeFocus ? Theme.primary : hov.containsMouse ? Theme.primaryHover : Theme.border
        Behavior on border.color { ColorAnimation { duration: Theme.durFast } }

        MouseArea { id: hov; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }

        TextField {
            id: field
            anchors.left: parent.left
            anchors.leftMargin: Theme.s3
            anchors.right: eye.left
            anchors.verticalCenter: parent.verticalCenter
            background: null
            padding: 0
            echoMode: root.shown ? TextInput.Normal : TextInput.Password
            placeholderText: root.placeholder
            placeholderTextColor: Theme.quiet
            color: Theme.ink
            font.family: Theme.mono
            font.pixelSize: Theme.fSmall
            selectByMouse: true
        }
        Item {
            id: eye
            width: 30
            height: parent.height
            anchors.right: parent.right
            Icon {
                anchors.centerIn: parent
                name: root.shown ? "lock" : "info"
                size: 13
                color: eh.containsMouse ? Theme.mid : Theme.quiet
            }
            MouseArea {
                id: eh
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.shown = !root.shown
            }
        }
    }
}
