import QtQuick
import "."

// THE LID (board T05): level 3's only chrome. A Super User inside an Admin sees that Admin's
// interface exactly as the Admin sees it -- their rail, their sheet, their home -- and this one line
// across the top is the whole of the difference. 38 px, one line, never a panel.
//
// It is drawn in the SAME language as the held session's banner on Must see (HeldCard, compact): a
// quiet surface, a red outline, the ring and the time in red. The user picked that one over a solid
// red bar (26 Sep 2026) -- so holding and being inside read as one thing, seen from two places.
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
    color: Qt.rgba(1, 1, 1, 0.03)
    border.color: Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.45)
    border.width: 1

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10
        Ring {
            width: 16; height: 16
            color: Theme.danger
            fraction: Day.leftFraction(root.session.entered_at, root.session.deadline_at, root.nowMs)
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            objectName: "lidWho"
            text: "You are inside " + root.name
            color: Theme.ink
            font.pixelSize: Theme.fBody
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            text: root.hostname
            color: Theme.faint
            monospace: true
            font.pixelSize: Theme.fMeta
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            objectName: "lidLeft"
            text: Day.leftText(root.session.deadline_at, root.nowMs) + " left"
            color: Theme.danger
            monospace: true
            font.pixelSize: Theme.fBody
            font.weight: Font.Bold
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    Row {
        anchors.right: parent.right
        anchors.rightMargin: 6
        anchors.verticalCenter: parent.verticalCenter
        spacing: 16

        // stepping out is not leaving: it is said here because nothing invisible is load-bearing
        Txt {
            text: "Esc steps out"
            color: Theme.faint
            font.pixelSize: Theme.fMeta
            anchors.verticalCenter: parent.verticalCenter
            MouseArea {
                anchors.fill: parent
                anchors.margins: -6
                cursorShape: Qt.PointingHandCursor
                onClicked: root.stepOut()
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
                Icon { name: "clock"; color: extendArea.containsMouse ? Theme.ink : Theme.dim; size: 13
                       anchors.verticalCenter: parent.verticalCenter }
                Txt {
                    text: "Extend"
                    color: extendArea.containsMouse ? Theme.ink : Theme.dim
                    font.pixelSize: Theme.fBody
                    font.weight: Font.DemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            MouseArea {
                id: extendArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.extend()
            }
        }
        TBtn {
            objectName: "lidLeave"
            text: "Leave"
            iconName: "back"
            tone: "danger"
            small: true
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.leave()
        }
    }
}
