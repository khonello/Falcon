import QtQuick
import QtQuick.Controls.Basic
import "."

// MORE THAN A TOOLTIP, LESS THAN A DRAWER. A machine's summary under the cursor in a dense view. It
// holds facts, never acts -- anything you can do lives where you can reach it without hovering.
Popup {
    id: root
    property string title: ""
    default property alias body: inner.data

    width: 260
    padding: Theme.s3
    height: wrap.implicitHeight + 2 * Theme.s3
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.split
        MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true }
    }

    Column {
        id: wrap
        width: parent.width
        spacing: Theme.s2

        Txt {
            width: parent.width
            text: root.title
            strong: true
            visible: root.title !== ""
            font.pixelSize: Theme.fSmall
        }
        Column {
            id: inner
            width: parent.width
            spacing: Theme.s1
        }
    }
}
