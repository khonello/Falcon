import QtQuick
import "."

// A SMALL ROW (the concept's ao-su / ao-run): a 30px round icon, a name (13, medium) over a line (12), and one small
// button at the right; padded 8 10 on surface-2, radius 8. `done` strikes the name through, quietly.
Rectangle {
    id: root
    property string icon: "checksquare"
    property string title: ""
    property string line: ""
    property bool lineHot: false
    property bool done: false
    property string act: ""
    property string actKind: "default"
    signal acted()
    signal open()

    width: parent ? parent.width : 300
    height: 16 + Math.max(30, col.implicitHeight)
    radius: Theme.radiusLg
    color: Theme.surface2
    MouseArea { anchors.fill: parent; onClicked: root.open() }
    Rectangle {
        id: ic
        x: 10
        anchors.verticalCenter: parent.verticalCenter
        width: 30; height: 30; radius: 15
        color: Theme.surface3
        Icon { anchors.centerIn: parent; name: root.icon; size: 14; color: Theme.text2 }
    }
    Column {
        id: col
        x: 50
        width: parent.width - 50 - 10 - (b.visible ? b.width + 10 : 0)
        anchors.verticalCenter: parent.verticalCenter
        Txt { width: parent.width; text: root.title; font.weight: Font.Medium; color: root.done ? Theme.text3 : Theme.text; font.strikeout: root.done }
        Txt { visible: root.line !== ""; width: parent.width; text: root.line; font.pixelSize: Theme.fSmall; color: root.lineHot ? Theme.crit : Theme.text3 }
    }
    Btn {
        id: b
        visible: root.act !== ""
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        small: true
        kind: root.actKind
        text: root.act
        onClicked: root.acted()
    }
}
