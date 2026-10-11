import QtQuick
import QtQuick.Controls.Basic
import "."

// A panel from the right, for creating something small or picking from a long list: the title, a
// body that scrolls, and a foot with a line on the left and the buttons on the right.
Popup {
    id: root
    property string title: ""
    property string subtitle: ""
    property string note: ""                     // the foot's line: what is missing, or what will happen
    default property alias body: content.data
    property alias footer: foot.data

    // A popup lives in the Overlay, not in the page that declared it, so leaving that page does not
    // take it with it. `page` ties it back: when the page goes, so does this.
    property Item page: null
    Connections {
        target: root.page
        enabled: root.page !== null
        function onVisibleChanged() { if (root.page && !root.page.visible) root.close() }
    }

    parent: Overlay.overlay
    x: parent ? parent.width - width : 0
    y: 0
    width: 440
    height: parent ? parent.height : 0
    padding: 0
    modal: true
    dim: true

    enter: Transition { NumberAnimation { property: "x"; from: root.parent ? root.parent.width : 0
                                          to: root.parent ? root.parent.width - root.width : 0
                                          duration: Theme.durBase; easing.type: Easing.OutCubic } }
    exit: Transition { NumberAnimation { property: "x"; to: root.parent ? root.parent.width : 0
                                         duration: Theme.durFast } }

    background: Rectangle {
        color: Theme.surface
        Rectangle { width: 1; height: parent.height; color: Theme.border }
        // nothing pressed inside this drawer may reach the page behind it
        MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true }
    }
    Overlay.modal: Rectangle { color: Theme.scrim }

    Item {
        id: head
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 56
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
        Btn {
            id: shut
            kind: "text"
            small: true
            iconName: "close"
            anchors.left: parent.left
            anchors.leftMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.close()
        }
        Column {
            anchors.left: shut.right
            anchors.leftMargin: 8
            anchors.right: parent.right
            anchors.rightMargin: 20
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1
            Txt { width: parent.width; text: root.title; font.weight: Font.DemiBold; font.pixelSize: Theme.fLead }
            Txt { width: parent.width; text: root.subtitle; color: Theme.text3; font.pixelSize: Theme.fSmall; visible: text !== "" }
        }
    }

    Flickable {
        anchors.top: head.bottom
        anchors.bottom: footBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        contentHeight: content.height + 40
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}
        Column {
            id: content
            x: 24; y: 20
            width: parent.width - 48
            spacing: 18
        }
    }

    Item {
        id: footBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: foot.children.length ? 56 : 0
        visible: foot.children.length > 0
        Rectangle { width: parent.width; height: 1; color: Theme.border }
        Txt {
            x: 24
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - foot.width - 60
            text: root.note
            color: Theme.text3
            font.pixelSize: 12
        }
        Row {
            id: foot
            anchors.right: parent.right
            anchors.rightMargin: 24
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
        }
    }
}
