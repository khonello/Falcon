import QtQuick
import QtQuick.Controls.Basic
import "."

// THE SEARCH BOX A TABLE CARRIES. A magnifier on the left, a way to empty it on the right, and it
// filters as you type -- there is no button, because there is nothing to wait for.
Item {
    id: root
    property alias text: field.text
    property string placeholder: "Search"
    signal searched(string text)

    implicitWidth: 240
    implicitHeight: Theme.control

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: field.activeFocus ? Theme.primary : hov.containsMouse ? Theme.primaryHover : Theme.border
        Behavior on border.color { ColorAnimation { duration: Theme.durFast } }

        MouseArea { id: hov; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }

        Icon {
            id: glass
            name: "search"
            size: 14
            color: Theme.quiet
            anchors.left: parent.left
            anchors.leftMargin: Theme.s3
            anchors.verticalCenter: parent.verticalCenter
        }
        TextField {
            id: field
            anchors.left: glass.right
            anchors.leftMargin: Theme.s2
            anchors.right: clear.left
            anchors.verticalCenter: parent.verticalCenter
            background: null
            padding: 0
            placeholderText: root.placeholder
            placeholderTextColor: Theme.quiet
            color: Theme.ink
            font.family: Theme.sans
            font.pixelSize: Theme.fBody
            selectByMouse: true
            onTextChanged: root.searched(text)
        }
        Item {
            id: clear
            width: field.text === "" ? 0 : 24
            height: parent.height
            anchors.right: parent.right
            anchors.rightMargin: Theme.s1
            Icon {
                anchors.centerIn: parent
                visible: field.text !== ""
                name: "close"
                size: 12
                color: ch.containsMouse ? Theme.mid : Theme.quiet
            }
            MouseArea {
                id: ch
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: field.text = ""
            }
        }
    }
}
