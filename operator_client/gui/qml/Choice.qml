import QtQuick
import "."

// A card-sized option: an icon, a title and one line of what it means. One of several is chosen.
Rectangle {
    id: root
    property bool on: false
    property string icon: ""
    property string title: ""
    property string desc: ""
    property bool disabled: false
    signal clicked()

    implicitWidth: 240
    implicitHeight: col.implicitHeight + 32
    radius: Theme.radius
    color: on ? Theme.accentSoft : Theme.surface
    border.width: 1
    border.color: on ? Theme.accent : area.containsMouse ? Theme.borderStrong : Theme.border
    opacity: disabled ? 0.5 : 1
    Behavior on color { ColorAnimation { duration: Theme.durFast } }

    Column {
        id: col
        x: 16; y: 16
        width: parent.width - 32
        spacing: 6
        Row {
            spacing: 10
            width: parent.width
            Rectangle {
                width: 28; height: 28; radius: 5
                color: root.on ? Theme.accent : Theme.surface3
                anchors.verticalCenter: parent.verticalCenter
                Icon { anchors.centerIn: parent; name: root.icon; size: 15; color: root.on ? Theme.inverse : Theme.text2 }
            }
            Txt {
                text: root.title
                font.weight: Font.DemiBold
                width: parent.width - 38
                wrapMode: Text.WordWrap
                elide: Text.ElideNone
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        Txt {
            visible: root.desc !== ""
            text: root.desc
            color: Theme.text3
            font.pixelSize: 12
            width: parent.width
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
        }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        enabled: !root.disabled
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
