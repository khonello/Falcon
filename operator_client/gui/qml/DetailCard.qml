import QtQuick
import "."

// The detail card. Always in the lane, never opens and never closes -- only its contents change,
// so it carries no close button. Nothing selected shows the same card holding its empty state.
Rectangle {
    id: root

    property string title: ""
    property string sub: ""
    property string leadIcon: ""
    property string leadInitials: ""
    property bool empty: false
    property string emptyIcon: "monitor"
    property string emptyLine: "Nothing selected"
    property string emptyHint: "Pick a row or a card and it opens here."
    default property alias content: body.data

    width: Theme.laneWidth
    radius: Theme.radiusLg
    color: Theme.pane
    border.width: 1
    border.color: Theme.line
    implicitHeight: empty ? 250 : (head.height + body.implicitHeight + 16)

    Item {
        id: head
        visible: !root.empty
        width: parent.width
        height: root.empty ? 0 : 64
        anchors.top: parent.top

        Row {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.top: parent.top
            anchors.topMargin: 16
            spacing: 10

            Avatar {
                initials: root.leadInitials
                size: 36
                visible: root.leadInitials !== ""
            }
            Rectangle {
                width: 36
                height: 36
                radius: Theme.radiusMd
                color: Theme.ground
                visible: root.leadIcon !== "" && root.leadInitials === ""
                Icon { anchors.centerIn: parent; name: root.leadIcon; color: Theme.dim; size: 18 }
            }
            Column {
                spacing: 2
                Txt { text: root.title; font.pixelSize: Theme.fSection + 1; font.weight: Font.DemiBold }
                Txt { text: root.sub; visible: root.sub !== ""; color: Theme.faint; font.pixelSize: Theme.fMeta }
            }
        }
    }

    Column {
        id: body
        visible: !root.empty
        anchors.top: head.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 10
    }

    Column {
        visible: root.empty
        anchors.centerIn: parent
        width: parent.width - 48
        spacing: 12

        Rectangle {
            width: 52
            height: 52
            radius: Theme.radiusLg
            color: Theme.ground
            anchors.horizontalCenter: parent.horizontalCenter
            Icon { anchors.centerIn: parent; name: root.emptyIcon; color: Theme.faint; size: 23 }
        }
        Txt {
            width: parent.width
            text: root.emptyLine
            color: Theme.dim
            font.pixelSize: Theme.fRow
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
        }
        Txt {
            width: parent.width
            text: root.emptyHint
            color: Theme.faint
            font.pixelSize: Theme.fBody
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
        }
    }
}
