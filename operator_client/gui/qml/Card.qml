import QtQuick
import "."

// FILLED by default (docs/UI.md): an empty white box on a white page is a line drawing of nothing.
// `outlined` is for a card holding a form, or a conversation, where a fill fights the contents.
Rectangle {
    id: root
    property bool outlined: false
    property string tint: ""                 // warn | danger -- an exception, and then the fill says so
    property string title: ""
    default property alias content: body.data

    implicitHeight: body.implicitHeight + (title === "" ? 0 : head.height) + 2 * Theme.s4
    radius: Theme.radiusLg
    color: tint !== "" ? Theme.toneSoft(tint) : outlined ? Theme.surface : Theme.fill
    border.width: outlined ? 1 : 0
    border.color: Theme.split

    Txt {
        id: head
        visible: root.title !== ""
        height: visible ? implicitHeight + Theme.s2 : 0
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.s4
        anchors.bottomMargin: 0
        text: root.title
        strong: true
    }
    Column {
        id: body
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: root.title === "" ? parent.top : head.bottom
        anchors.margins: Theme.s4
        anchors.topMargin: root.title === "" ? Theme.s4 : 0
        spacing: Theme.s2
    }
}
