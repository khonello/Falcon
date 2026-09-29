import QtQuick
import "."

// What would be here, and the one way to make one. A zero is a result, not an absence.
Column {
    id: root
    property string text: "Nothing here yet"
    property string hint: ""
    property string action: ""
    signal actionTriggered()

    spacing: Theme.s2
    Item {
        width: parent.width
        height: 44
        Icon {
            anchors.centerIn: parent
            name: "folder"
            size: 30
            color: Theme.quiet
        }
    }
    Txt { width: parent.width; text: root.text; tone: "mid"; horizontalAlignment: Text.AlignHCenter }
    Txt {
        width: parent.width
        visible: root.hint !== ""
        text: root.hint
        tone: "quiet"
        font.pixelSize: Theme.fSmall
        horizontalAlignment: Text.AlignHCenter
    }
    Item {
        width: parent.width
        height: root.action === "" ? 0 : btn.height + Theme.s2
        visible: root.action !== ""
        Btn {
            id: btn
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            kind: "primary"
            small: true
            text: root.action
            onClicked: root.actionTriggered()
        }
    }
}
