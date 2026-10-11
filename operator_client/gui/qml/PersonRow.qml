import QtQuick
import "."

// A person on a line: their initials, their name and one grey line under it, and an act on the right.
Item {
    id: root
    property string name: ""
    property string sub: ""
    property string act: ""
    property color dot: "transparent"           // a status dot on the avatar (busy, at their desk)
    signal acted()
    implicitHeight: 48

    Rectangle {
        id: av
        width: 30; height: 30; radius: 15
        color: Theme.surface3
        anchors.verticalCenter: parent.verticalCenter
        Txt { anchors.centerIn: parent; text: Theme.initials(root.name); font.pixelSize: 11; font.weight: Font.DemiBold; color: Theme.text2; elide: Text.ElideNone }
        Rectangle { visible: root.dot !== "transparent"; width: 9; height: 9; radius: 5; color: root.dot; border.width: 2; border.color: Theme.surface; anchors.right: parent.right; anchors.bottom: parent.bottom }
    }
    Column {
        anchors.left: av.right
        anchors.leftMargin: 10
        anchors.right: btn.left
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        Txt { width: parent.width; text: root.name; font.weight: Font.Medium }
        Txt { width: parent.width; text: root.sub; color: Theme.text3; font.pixelSize: 12 }
    }
    Btn {
        id: btn
        visible: root.act !== ""
        width: visible ? implicitWidth : 0
        small: true
        ghost: true
        kind: "primary"
        text: root.act
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        onClicked: root.acted()
    }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
}
