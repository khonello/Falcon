import QtQuick
import "."

// A CARD, NOT A ROW (design/PATTERNS.md section 4). One component for both kinds:
//   a person  -- `initials` set: an avatar leads
//   a thing   -- `iconName` set: a BARE 18 px icon in its tone leads (never an icon in a tile)
// Title, a line (in tone when it says something), and an optional state word on the right. Anchored left.
// The chosen card is a filled `select` row with a white title -- never a left-edge accent.
Rectangle {
    id: root

    property string initials: ""
    property string iconName: ""
    property string iconTone: "accent"
    property string title: ""
    property string line: ""
    property string lineTone: ""
    property string stateWord: ""
    property string stateTone: ""
    property bool selected: false
    property var modelData: null            // set when used as a pager delegate
    property int index: -1
    signal clicked()
    signal doubleClicked()

    implicitHeight: 58
    radius: 14
    color: selected ? Theme.select : area.containsMouse ? Qt.lighter(Theme.pane, 1.12) : Theme.pane
    Behavior on color { ColorAnimation { duration: Theme.durFast } }

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.right: word.left
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12

        Avatar { visible: root.initials !== ""; initials: root.initials; size: 34; anchors.verticalCenter: parent.verticalCenter }
        Icon { visible: root.initials === "" && root.iconName !== ""; name: root.iconName; size: 18
               color: Theme.tone(root.iconTone); anchors.verticalCenter: parent.verticalCenter }
        Column {
            spacing: 2
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 50
            Txt {
                width: parent.width; elide: Text.ElideRight
                text: root.title; color: root.selected ? "#ffffff" : Theme.ink
                font.pixelSize: Theme.fRow - 1; font.weight: Font.DemiBold
            }
            Txt {
                width: parent.width; elide: Text.ElideRight
                visible: root.line !== ""; text: root.line
                color: root.selected ? Theme.selectSub : root.lineTone === "" ? Theme.faint : Theme.tone(root.lineTone)
                font.pixelSize: Theme.fMeta
            }
        }
    }
    Txt {
        id: word
        anchors.right: parent.right
        anchors.rightMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        text: root.stateWord
        visible: text !== ""
        color: root.stateTone === "" ? Theme.faint : Theme.tone(root.stateTone)
        font.pixelSize: Theme.fMeta
        font.weight: Font.DemiBold
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
        onDoubleClicked: root.doubleClicked()
    }
}
