import QtQuick
import QtQuick.Controls.Basic
import "."

// RULE 4, AT ROW SIZE. A small destructive act inline -- pausing a flow, dropping a listener -- still
// names its cost, but a whole Modal for it stops the page dead. This asks in place, in one line.
Popup {
    id: root
    property string cost: ""
    property string verb: "Yes"
    property bool destructive: false
    signal accepted()

    width: 280
    padding: Theme.s3
    height: body.implicitHeight + 2 * Theme.s3
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

    background: Rectangle {
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.split
        MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true }
    }

    Column {
        id: body
        width: parent.width
        spacing: Theme.s3

        Row {
            width: parent.width
            spacing: Theme.s2
            Icon {
                name: "warn"
                size: 15
                color: root.destructive ? Theme.danger : Theme.warn
            }
            Txt {
                width: parent.width - 15 - Theme.s2
                text: root.cost
                font.pixelSize: Theme.fSmall
                wrapMode: Text.WordWrap
                elide: Text.ElideNone
            }
        }
        Row {
            anchors.right: parent.right
            spacing: Theme.s2
            Btn { small: true; text: "No"; onClicked: root.close() }
            Btn {
                small: true
                kind: "primary"
                danger: root.destructive
                text: root.verb
                onClicked: { root.close(); root.accepted() }
            }
        }
    }
}
