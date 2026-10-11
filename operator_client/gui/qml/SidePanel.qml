import QtQuick
import QtQuick.Controls.Basic
import "."

// THE ITEM BESIDE ITS LIST (7 Oct 2026): a click in the list shows the item here at once, at the
// list's height, with its facts as label / value rows, any short sections under them, and its actions
// at the foot. Charts and drawings of the same item stay below the list, full width.
//
//   facts: [[label, value, colour?, mono?]]       -- a value is text; a colour tints it
//   default content: sections under the facts      actions: the buttons at the foot (right aligned)
//   foot / dock: a band above the actions          extra: controls in the header
Rectangle {
    id: root
    property string title: ""
    property string sub: ""
    property var facts: []
    property int factLabelWidth: 116
    property bool fixed: true              // false: grows with its content (Reports' two panels)
    default property alias content: sections.data
    property alias actions: actionRow.data
    property alias foot: footBox.data
    property alias dock: dockBox.data
    property alias extra: extraRow.data
    property bool footShown: true            // a page that hides its foot or dock says so here
    property bool dockShown: true
    // a band shows only when something in it does
    function anyShown(it) { for (var i = 0; i < it.children.length; i++) if (it.children[i].visible) return true; return false }

    property bool showEmpty: false
    property string emptyIcon: "inbox"
    property string emptyTitle: "Nothing picked"
    property string emptyText: ""

    color: Theme.surface
    radius: Theme.radius
    border.width: 1
    border.color: Theme.border
    implicitHeight: fixed ? Theme.listHeight
                          : head.height + flick.contentHeight + footArea.height + 4
    clip: true

    Item {
        id: head
        visible: !root.showEmpty
        x: 1; y: 1
        width: parent.width - 2
        height: visible ? 40 : 0
        Row {
            anchors.left: parent.left
            anchors.leftMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            width: Math.max(0, parent.width - 28 - extraRow.width - 8)
            clip: true
            Txt { id: tt; text: root.title; font.weight: Font.DemiBold; width: Math.min(implicitWidth, parent.width) }
            Txt {
                visible: root.sub !== ""
                text: root.sub
                color: Theme.text3
                font.pixelSize: Theme.fSmall
                anchors.baseline: tt.baseline
                width: Math.max(0, Math.min(implicitWidth, parent.width - tt.width - 8))
            }
        }
        Row {
            id: extraRow
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6
        }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
    }

    Flickable {
        id: flick
        visible: !root.showEmpty
        x: 1
        anchors.top: head.bottom
        anchors.bottom: footArea.top
        width: parent.width - 2
        contentHeight: body.height + 16
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: flick.contentHeight > flick.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff }

        Column {
            id: body
            x: 16
            y: 2
            width: flick.width - 32
            Repeater {
                model: root.facts
                delegate: Item {
                    required property var modelData
                    width: body.width
                    height: Math.max(33, val.implicitHeight + 14)
                    Txt {
                        y: 7
                        width: root.factLabelWidth - 8
                        text: modelData[0]
                        color: Theme.text3
                    }
                    Txt {
                        id: val
                        x: root.factLabelWidth
                        y: 7
                        width: parent.width - root.factLabelWidth
                        text: modelData[1] === undefined || modelData[1] === null ? "—" : String(modelData[1])
                        color: modelData[2] ? modelData[2] : Theme.text
                        mono: !!modelData[3]
                        wrapMode: Text.Wrap
                        elide: Text.ElideNone
                        textFormat: Text.PlainText
                    }
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                }
            }
            Item { width: 1; height: root.facts.length && sections.children.length ? 14 : 0 }
            Column {
                id: sections
                width: body.width
                spacing: 16
            }
        }
    }

    Column {
        id: footArea
        visible: !root.showEmpty
        x: 1
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 1
        width: parent.width - 2
        Item {
            width: parent.width
            readonly property bool on: root.footShown && root.anyShown(footBox)
            height: on ? footBox.childrenRect.height + 22 : 0
            clip: true
            Rectangle { width: parent.width; height: 1; color: Theme.border }
            Item { id: footBox; x: 16; y: 10; width: parent.width - 32; height: childrenRect.height }
        }
        Item {
            width: parent.width
            readonly property bool on: root.dockShown && root.anyShown(dockBox)
            height: on ? dockBox.childrenRect.height + 22 : 0
            clip: true
            Rectangle { width: parent.width; height: 1; color: Theme.border }
            Item { id: dockBox; x: 16; y: 10; width: parent.width - 32; height: childrenRect.height }
        }
        Item {
            width: parent.width
            height: root.anyShown(actionRow) ? 50 : 0
            clip: true
            Rectangle { width: parent.width; height: 1; color: Theme.border }
            Row {
                id: actionRow
                anchors.right: parent.right
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                layoutDirection: Qt.LeftToRight
            }
        }
    }

    Empty {
        visible: root.showEmpty
        anchors.centerIn: parent
        width: parent.width
        icon: root.emptyIcon
        title: root.emptyTitle
        text: root.emptyText
        h: 200
    }
}
