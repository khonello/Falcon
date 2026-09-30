import QtQuick
import "."

// A LINE BETWEEN TWO BLOCKS, optionally with a word sitting in it. Use it where a gap alone is
// ambiguous; a gap alone is usually enough.
Item {
    id: root
    property string text: ""

    implicitWidth: parent ? parent.width : 200
    implicitHeight: text === "" ? Theme.s4 : 22

    Rectangle {
        anchors.left: parent.left
        anchors.right: root.text === "" ? parent.right : label.left
        anchors.rightMargin: root.text === "" ? 0 : Theme.s3
        anchors.verticalCenter: parent.verticalCenter
        height: 1
        color: Theme.split
    }
    Txt {
        id: label
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        visible: root.text !== ""
        text: root.text
        tone: "quiet"
        font.pixelSize: 11
    }
    Rectangle {
        anchors.left: label.right
        anchors.leftMargin: Theme.s3
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        visible: root.text !== ""
        height: 1
        color: Theme.split
    }
}
