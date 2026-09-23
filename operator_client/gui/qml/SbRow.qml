import QtQuick
import "."

// A sidebar row: an avatar or an icon, a name, an optional host, and whatever trails it.
// Selected is a filled, muted row -- never an edge on the left.
Rectangle {
    id: root

    property string initials: ""
    property string icon: ""
    property string name: ""
    property string sub: ""
    property string sessionState: ""          // draws the vocabulary icon on the right
    property string badge: ""
    property string badgeTone: "neutral"
    property bool selected: false
    signal clicked()

    width: parent ? parent.width : 0
    height: initials !== "" ? 44 : 40
    radius: Theme.radiusSm
    color: selected ? Theme.select : area.containsMouse ? Theme.line : "transparent"
    Behavior on color { ColorAnimation { duration: Theme.durFast } }

    // the row is inset from the sidebar edges, so the fill reads as a pill
    anchors.leftMargin: 6
    anchors.rightMargin: 6

    Row {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        spacing: 10

        Avatar {
            initials: root.initials
            size: 28
            visible: root.initials !== ""
            anchors.verticalCenter: parent.verticalCenter
        }
        Icon {
            name: root.icon
            color: root.selected ? "#ffffff" : Theme.dim
            size: 15
            visible: root.icon !== "" && root.initials === ""
            anchors.verticalCenter: parent.verticalCenter
        }
        Column {
            width: parent.width - (root.initials !== "" || root.icon !== "" ? 38 : 0) - trail.width - 20
            spacing: 0
            anchors.verticalCenter: parent.verticalCenter

            Txt {
                width: parent.width
                text: root.name
                color: root.selected ? "#ffffff" : Theme.ink
                font.pixelSize: Theme.fBody
                font.weight: Font.Medium
            }
            Txt {
                width: parent.width
                text: root.sub
                visible: root.sub !== ""
                color: root.selected ? Theme.selectSub : Theme.faint
                font.pixelSize: Theme.fSmall
                monospace: root.sub.indexOf("-") > 0 && root.sub.indexOf(" ") < 0
            }
        }
        Row {
            id: trail
            spacing: 8
            anchors.verticalCenter: parent.verticalCenter

            Chip {
                text: root.badge
                tone: root.badgeTone
                visible: root.badge !== ""
                anchors.verticalCenter: parent.verticalCenter
            }
            Icon {
                name: Theme.sessionIcon(root.sessionState)
                color: Theme.sessionColor(root.sessionState)
                size: 14
                visible: root.sessionState !== ""
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
