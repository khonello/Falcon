import QtQuick
import QtQuick.Controls.Basic
import "."

// A dialog: the one place the console stops you. A title, the body, and the buttons at the foot on
// the right. `footer` takes the buttons; with none, the foot is not drawn.
Popup {
    id: root
    property string title: ""
    property string subtitle: ""
    default property alias body: content.data
    property alias footer: foot.data
    property int pad: 24

    // A popup lives in the Overlay, not in the page that declared it, so leaving that page does not
    // take it with it. `page` ties it back: when the page goes, so does this.
    property Item page: null
    Connections {
        target: root.page
        enabled: root.page !== null
        function onVisibleChanged() { if (root.page && !root.page.visible) root.close() }
    }

    parent: Overlay.overlay
    anchors.centerIn: Overlay.overlay
    width: 520
    height: head.height + content.childrenRect.height + 2 * 8 + footBar.height + 8
    padding: 0
    modal: true
    dim: true
    closePolicy: Popup.CloseOnEscape

    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.durFast } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.durFast } }

    background: Rectangle {
        radius: Theme.radiusLg
        color: Theme.surface
        border.width: Theme.dark ? 1 : 0
        border.color: Theme.border
        // nothing pressed inside this dialog may reach the page behind it
        MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true }
    }
    Overlay.modal: Rectangle { color: Theme.scrim }

    Item {
        id: head
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 52
        Column {
            anchors.left: parent.left
            anchors.leftMargin: root.pad
            anchors.right: shut.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1
            Txt { width: parent.width; text: root.title; font.weight: Font.DemiBold; font.pixelSize: Theme.fLead }
            Txt { width: parent.width; text: root.subtitle; color: Theme.text3; font.pixelSize: Theme.fSmall; visible: text !== "" }
        }
        Btn {
            id: shut
            kind: "text"
            small: true
            iconName: "close"
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.close()
        }
    }

    Column {
        id: content
        anchors.top: head.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: root.pad
        anchors.rightMargin: root.pad
        spacing: 12
    }

    Item {
        id: footBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: foot.children.length ? 60 : 12
        Row {
            id: foot
            anchors.right: parent.right
            anchors.rightMargin: root.pad
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
        }
    }
}
