import QtQuick
import "."

// The words beside the hues. Every chart that uses colour to mean something carries one, because
// a colour on its own is not a statement.
Flow {
    id: root

    property var items: []            // [{ label, color, round }]
    property string note: ""
    spacing: 16

    Repeater {
        model: root.items
        delegate: Row {
            required property var modelData
            spacing: 6
            Rectangle {
                width: 10
                height: 10
                radius: modelData.round ? 5 : 3
                color: modelData.color
                anchors.verticalCenter: parent.verticalCenter
            }
            Txt {
                text: modelData.label
                color: Theme.dim
                font.pixelSize: Theme.fMeta
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
    Txt {
        text: root.note
        visible: root.note !== ""
        color: Theme.faint
        font.pixelSize: Theme.fMeta
    }
}
