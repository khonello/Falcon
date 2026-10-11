import QtQuick
import QtQuick.Layouts
import "."

// A hairline panel: a header of one line (title, a quiet subtitle, controls on the right) and a body.
// `flush` drops the body's padding for lists and tables that run edge to edge. A panel given a
// height lets its body fill it; otherwise the body sets the height.
Rectangle {
    id: root
    property string title: ""
    property string sub: ""
    property bool flush: false
    property int pad: 14
    default property alias content: body.data
    property alias extra: extraRow.data
    readonly property alias bodyItem: body
    readonly property real headerHeight: head.visible ? head.height : 0
    // a panel with a fixed height lets its body fill the rest
    property bool fill: false

    color: Theme.surface
    radius: Theme.radius
    border.width: 1
    border.color: Theme.border
    implicitHeight: headerHeight + (fill ? 0 : body.childrenRect.height + (flush ? 0 : 2 * pad)) + 2
    clip: true

    Item {
        id: head
        visible: root.title !== "" || extraRow.children.length > 0
        x: 1; y: 1
        width: parent.width - 2
        height: visible ? Math.max(40, extraRow.implicitHeight + 12) : 0

        Row {
            id: titles
            anchors.left: parent.left
            anchors.leftMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            width: Math.max(0, parent.width - 28 - extraRow.width - (extraRow.width > 0 ? 10 : 0))
            clip: true
            Txt {
                id: tt
                text: root.title
                font.weight: Font.DemiBold
                width: Math.min(implicitWidth, titles.width)
                anchors.baseline: parent.children[1].baseline
            }
            Txt {
                visible: root.sub !== ""
                text: root.sub
                color: Theme.text3
                font.pixelSize: Theme.fSmall
                width: Math.max(0, Math.min(implicitWidth, titles.width - tt.width - 8))
            }
        }
        Row {
            id: extraRow
            anchors.right: parent.right
            anchors.rightMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
        }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
    }

    Item {
        id: body
        x: root.flush ? 1 : root.pad
        y: head.height + 1 + (root.flush ? 0 : root.pad)
        width: root.width - 2 * x
        height: root.fill ? root.height - y - (root.flush ? 1 : root.pad) : childrenRect.height
    }
}
