import QtQuick
import QtQuick.Controls.Basic
import "."

// Detail from a table row, from the right. A subject with its own workspace opens a page instead.
Popup {
    id: root
    property string title: ""
    property string subtitle: ""
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
    width: 420
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
        Rectangle { width: 1; height: parent.height; color: Theme.split }
    }
    Overlay.modal: Rectangle { color: Qt.rgba(0, 0, 0, 0.35) }

    Item {
        id: head
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 56
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.split }
        Column {
            anchors.left: parent.left
            anchors.leftMargin: Theme.s4
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1
            Txt { text: root.title; strong: true; font.pixelSize: Theme.fLead }
            Txt { text: root.subtitle; tone: "mid"; font.pixelSize: Theme.fSmall; visible: text !== "" }
        }
        Btn {
            kind: "text"
            small: true
            iconName: "close"
            anchors.right: parent.right
            anchors.rightMargin: Theme.s2
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.close()
        }
    }

    Column {
        id: content
        anchors.top: head.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Theme.s4
        spacing: Theme.s3
    }

    Row {
        id: foot
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.margins: Theme.s4
        spacing: Theme.s2
    }
}
