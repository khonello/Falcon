import QtQuick
import "."

// One row of a body list: its own rounded card, one line of title, at most one value, a chevron.
// Never a container -- selecting it fills the detail card.
Rectangle {
    id: root

    property string icon: ""
    property color iconColor: Theme.dim
    property string initials: ""
    property string title: ""
    property string sub: ""
    property string value: ""
    property string tone: ""                 // "" | accent | ok | warn | danger
    property bool selected: false
    property bool chevron: true
    signal clicked()

    implicitHeight: Theme.rowHeight
    radius: Theme.radiusMd
    color: mouse.containsMouse ? Theme.line : Theme.ground
    Behavior on color { ColorAnimation { duration: Theme.durFast } }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: "transparent"
        border.width: root.selected ? 1 : 0
        border.color: Theme.selectLine
    }

    Row {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 12

        Icon {
            name: root.icon
            color: root.iconColor
            size: 16
            visible: root.icon !== "" && root.initials === ""
            anchors.verticalCenter: parent.verticalCenter
        }
        Avatar {
            initials: root.initials
            size: 28
            visible: root.initials !== ""
            anchors.verticalCenter: parent.verticalCenter
        }
        Column {
            width: parent.width - (root.icon !== "" || root.initials !== "" ? 40 : 0) - valueRow.width - 24
            spacing: 2
            anchors.verticalCenter: parent.verticalCenter

            Txt {
                width: parent.width
                text: root.title
                font.pixelSize: Theme.fRow
                font.weight: Font.Medium
            }
            Txt {
                width: parent.width
                text: root.sub
                visible: root.sub !== ""
                color: Theme.faint
                font.pixelSize: Theme.fMeta
            }
        }
        Row {
            id: valueRow
            spacing: 10
            anchors.verticalCenter: parent.verticalCenter

            Txt {
                text: root.value
                visible: root.value !== ""
                color: root.tone === "" ? Theme.dim : Theme.tone(root.tone)
                font.pixelSize: Theme.fBody
                font.weight: root.tone === "" ? Font.Normal : Font.Medium
                anchors.verticalCenter: parent.verticalCenter
            }
            Icon {
                name: "chev"
                color: Theme.faint
                size: 14
                visible: root.chevron
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
