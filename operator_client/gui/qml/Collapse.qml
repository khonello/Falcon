import QtQuick
import "."

// WHAT MOST PEOPLE DO NOT NEED TO SEE. A long form's advanced half, folded away -- but never anything
// required, and never anything that would change what the form does without being opened.
Column {
    id: root
    property string title: ""
    property bool open: false
    default property alias body: inner.data

    spacing: 0

    Rectangle {
        width: root.width
        height: 34
        radius: Theme.radiusSm
        color: hh.containsMouse ? Theme.hover : "transparent"

        Icon {
            id: caret
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            name: root.open ? "chevd" : "chevr"
            size: 12
            color: Theme.quiet
        }
        Txt {
            anchors.left: caret.right
            anchors.leftMargin: Theme.s2
            anchors.verticalCenter: parent.verticalCenter
            text: root.title
            tone: "mid"
            font.pixelSize: Theme.fSmall
        }
        MouseArea {
            id: hh
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.open = !root.open
        }
    }
    Column {
        id: inner
        width: root.width
        visible: root.open
        spacing: Theme.s3
        topPadding: root.open ? Theme.s2 : 0
    }
}
