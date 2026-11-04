import QtQuick
import QtQuick.Controls.Basic
import "."

// THE CONCEPT'S tk-drawer: what is made is made in a panel over the page it belongs to, 1120 wide at most, four fifths of the
// window at least. It holds one editor (`Editor`), named by the address (automation/new, actions/edit-3...): closing goes back
// to the page. A click on the page behind closes it, as antd's Drawer does.
Item {
    id: root
    property string src: ""
    property string backTo: ""
    anchors.fill: parent
    visible: src !== ""
    z: 1000
    readonly property var ed: load.item
    function close() { Nav.go(backTo) }

    // closing keeps what was written where the editor says so (`keeps`): it stays loaded behind the page
    property string held: ""
    onSrcChanged: {
        if (src !== "") { held = src; slide.restart() }
        else if (!(ed && ed.keeps)) held = ""
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.scrim
        MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; onClicked: root.close() }
    }
    Rectangle {
        id: panel
        readonly property real to: root.width - width
        x: to
        width: Math.min(1120, root.width * 0.8)
        height: root.height
        color: Theme.bg
        NumberAnimation { id: slide; target: panel; property: "x"; from: root.width; to: panel.to; duration: Theme.durBase; easing.type: Easing.OutCubic
                          onFinished: panel.x = Qt.binding(function () { return panel.to }) }
        // nothing pressed inside may reach the page behind
        MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true }
        Rectangle {
            id: head
            width: parent.width
            height: 54
            color: Theme.surface
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
            Btn { id: shut; x: 21; anchors.verticalCenter: parent.verticalCenter; kind: "text"; small: true; iconName: "close"; onClicked: root.close() }
            Txt { x: 54; anchors.verticalCenter: parent.verticalCenter; text: root.ed ? root.ed.drawerTitle : ""; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideNone }
            Txt { anchors.right: parent.right; anchors.rightMargin: 24; anchors.verticalCenter: parent.verticalCenter; text: root.ed ? root.ed.drawerNote : ""; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
        }
        Flickable {
            id: fl
            anchors.top: head.bottom
            anchors.bottom: parent.bottom
            width: parent.width
            contentWidth: width
            contentHeight: load.height + 32
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            Loader {
                id: load
                x: 20; y: 16
                width: fl.width - 40
                source: root.held
                onLoaded: { item.minHeight = Qt.binding(function () { return fl.height - 32 }); item.closed.connect(root.close); fl.contentY = 0 }
            }
        }
    }
}
