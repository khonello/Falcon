import QtQuick
import "."

// The page's name on the left, its ONE primary action on the right. Secondary acts live in the row.
Item {
    id: root
    property string title: ""
    property string subtitle: ""
    default property alias actions: acts.data

    implicitHeight: 52

    Column {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        spacing: 1
        Txt { text: root.title; font.pixelSize: Theme.fTitle; strong: true }
        Txt { text: root.subtitle; tone: "mid"; font.pixelSize: Theme.fSmall; visible: text !== "" }
    }
    Row {
        id: acts
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.s2
    }
}
