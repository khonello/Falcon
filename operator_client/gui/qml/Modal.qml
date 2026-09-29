import QtQuick
import QtQuick.Controls.Basic
import "."

// A FORM, OR AN ACT WITH A COST NAMED BEFORE THE VERB (docs/UI.md). Centred and modal: it is the one
// place the console stops you. It does not scroll -- a form needing more room than this is a page.
Popup {
    id: root
    property string title: ""
    property string subtitle: ""
    default property alias body: content.data
    property alias footer: foot.data

    parent: Overlay.overlay
    anchors.centerIn: Overlay.overlay
    width: 520
    height: head.height + content.implicitHeight + 2 * Theme.s4 + foot.height
    padding: 0
    modal: true
    dim: true
    closePolicy: Popup.CloseOnEscape

    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.durFast } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.durFast } }

    background: Rectangle { radius: Theme.radiusLg; color: Theme.surface }
    Overlay.modal: Rectangle { color: Qt.rgba(0, 0, 0, 0.35) }

    Item {
        id: head
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 56

        Column {
            anchors.left: parent.left
            anchors.leftMargin: Theme.s5
            anchors.right: shut.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1
            Txt { width: parent.width; text: root.title; strong: true; font.pixelSize: Theme.fLead }
            Txt {
                width: parent.width
                text: root.subtitle
                tone: "mid"
                font.pixelSize: Theme.fSmall
                visible: text !== ""
            }
        }
        Btn {
            id: shut
            kind: "text"
            small: true
            iconName: "close"
            anchors.right: parent.right
            anchors.rightMargin: Theme.s3
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.close()
        }
    }

    Column {
        id: content
        anchors.top: head.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Theme.s5
        anchors.rightMargin: Theme.s5
        spacing: Theme.s4
    }

    Item {
        id: foot
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 56
        Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.split }
    }
}
