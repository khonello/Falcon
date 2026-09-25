import QtQuick
import "."

// THE LID (board T05): level 3's only chrome. A Super User inside an Admin sees that Admin's
// interface exactly as the Admin sees it -- their rail, their sheet, their home -- and this one red
// line across the top is the whole of the difference. 38 px, one line, never a panel.
//
// One place to look (who, which machine, how long) and one place to press (Extend, Leave). Escape
// steps out and keeps the session; Leave ends it. Holding and looking are different things.
Rectangle {
    id: root

    property string name: ""
    property string hostname: ""
    property var session: ({})
    property double nowMs: Date.now()
    signal extend()
    signal leave()
    signal stepOut()

    implicitHeight: 38
    radius: Theme.radiusMd
    color: Theme.dangerDeep

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        Icon { name: "shield"; color: "#ffffff"; size: 15; anchors.verticalCenter: parent.verticalCenter }
        Txt {
            objectName: "lidWho"
            text: "You are inside " + root.name
            color: "#ffffff"
            font.pixelSize: Theme.fBody
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            text: root.hostname
            color: Qt.rgba(1, 1, 1, 0.72)
            monospace: true
            font.pixelSize: Theme.fMeta
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    Row {
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        spacing: 18

        // stepping out is not leaving: it is said here because nothing invisible is load-bearing
        Txt {
            text: "Esc steps out"
            color: Qt.rgba(1, 1, 1, 0.55)
            font.pixelSize: Theme.fMeta
            anchors.verticalCenter: parent.verticalCenter
            MouseArea {
                anchors.fill: parent
                anchors.margins: -6
                cursorShape: Qt.PointingHandCursor
                onClicked: root.stepOut()
            }
        }
        Row {
            spacing: 8
            anchors.verticalCenter: parent.verticalCenter
            Ring {
                width: 20; height: 20
                fraction: Day.leftFraction(root.session.entered_at, root.session.deadline_at, root.nowMs)
                anchors.verticalCenter: parent.verticalCenter
            }
            Txt {
                objectName: "lidLeft"
                text: Day.leftText(root.session.deadline_at, root.nowMs) + " left"
                color: "#ffffff"
                monospace: true
                font.pixelSize: Theme.fBody
                font.weight: Font.Bold
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        Item {
            width: extendRow.implicitWidth
            height: 28
            anchors.verticalCenter: parent.verticalCenter
            Row {
                id: extendRow
                spacing: 6
                anchors.verticalCenter: parent.verticalCenter
                Icon { name: "clock"; color: "#ffffff"; size: 13; anchors.verticalCenter: parent.verticalCenter }
                Txt {
                    text: "Extend"
                    color: "#ffffff"
                    font.pixelSize: Theme.fBody
                    font.weight: Font.DemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.extend()
            }
        }
        Rectangle {
            width: leaveRow.implicitWidth + 24
            height: 26
            radius: Theme.radiusSm
            color: leaveArea.containsMouse ? Qt.rgba(1, 1, 1, 0.26) : Qt.rgba(1, 1, 1, 0.16)
            anchors.verticalCenter: parent.verticalCenter
            Row {
                id: leaveRow
                anchors.centerIn: parent
                spacing: 6
                Icon { name: "back"; color: "#ffffff"; size: 12; anchors.verticalCenter: parent.verticalCenter }
                Txt {
                    text: "Leave"
                    color: "#ffffff"
                    font.pixelSize: Theme.fBody
                    font.weight: Font.DemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            MouseArea {
                id: leaveArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.leave()
            }
        }
    }
}
