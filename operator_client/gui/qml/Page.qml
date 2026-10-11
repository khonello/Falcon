import QtQuick
import QtQuick.Controls.Basic
import "."

// A page of the console: the title and its one line, then the page's panels stacked with 14px between
// them, the whole thing scrolling under the top bar. A page that is an editor (`bare`) has no title:
// its crumb in the top bar says where it is.
Flickable {
    id: root
    property string title: Nav.title(Nav.page)
    property string sub: Nav.subtitle(Nav.page)
    property bool bare: false
    property string refused: ""                // "That is not this console's." and why
    default property alias content: col.data
    readonly property real w: width - 40       // the width a page's own rows lay out in

    contentWidth: width
    contentHeight: col.y + col.height + 48
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar { policy: root.contentHeight > root.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff }

    Column {
        id: head
        visible: !root.bare
        x: 20; y: 18
        width: root.w
        spacing: 2
        Txt { text: root.title; font.pixelSize: Theme.fPage; font.weight: Font.DemiBold; width: parent.width }
        Txt { visible: root.sub !== ""; text: root.sub; color: Theme.text3; width: parent.width }
    }
    Rectangle {
        id: gate
        visible: root.refused !== ""
        x: 20
        y: head.visible ? head.y + head.height + 14 : 18
        width: root.w
        height: visible ? 48 : 0
        radius: Theme.radius
        color: Theme.alpha(Theme.med, 0.10)
        Row {
            x: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12
            Icon { name: "stop"; size: 16; color: Theme.text2; anchors.verticalCenter: parent.verticalCenter }
            Txt { text: "That is not this console's."; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
            Txt { text: root.refused; color: Theme.text2; anchors.verticalCenter: parent.verticalCenter; width: root.w - 260 }
        }
    }
    Column {
        id: col
        x: 20
        y: gate.visible ? gate.y + gate.height + 14 : head.visible ? head.y + head.height + 14 : 18
        width: root.w
        spacing: 14
    }
}
