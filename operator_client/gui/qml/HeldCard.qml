import QtQuick
import "."

// A HELD SESSION, AS A CONTAINER (board DP09). Starting a traversal does not move the window: it
// makes the session, and the session is drawn here, where it was started, carrying its clock and the
// way back in. Double click goes in -- the same gesture as everything else. Leave ends it.
//
// A live-state card, never a viewport: there is no screen streaming in the protocol.
Rectangle {
    id: root

    property var admin: null               // the Admin whose workstation is held
    property var session: ({})
    property double nowMs: Date.now()
    // One line, for the mirror on Must see: the same container, not a second design -- same words,
    // same clock, same double click, same Leave -- flattened to sit in a header.
    property bool compact: false
    signal goInside()
    signal leave()

    readonly property var says: falcon.narrate("held", {
        name: admin ? admin.name : "", hostname: admin ? admin.hostname : "",
        entered_at: session.entered_at, deadline_at: session.deadline_at })

    implicitHeight: compact ? 34 : col.implicitHeight + 32
    implicitWidth: compact ? line.implicitWidth + 24 : 330
    radius: Theme.radiusMd
    color: area.containsMouse ? Qt.rgba(1, 1, 1, 0.06) : Qt.rgba(1, 1, 1, 0.03)
    border.color: Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.45)
    border.width: 1

    // underneath the buttons, so a click on Leave is Leave and a double click anywhere else goes in
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onDoubleClicked: root.goInside()
    }

    Row {
        id: line
        visible: root.compact
        anchors.left: parent.left
        anchors.leftMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10
        Ring {
            width: 16; height: 16
            color: Theme.danger
            fraction: Day.leftFraction(root.session.entered_at, root.session.deadline_at, root.nowMs)
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            text: "Holding " + (root.admin ? (root.admin.name || "an Admin") : "")
            color: Theme.ink
            font.pixelSize: Theme.fBody
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            text: root.admin ? (root.admin.hostname || "") : ""
            color: Theme.faint
            monospace: true
            font.pixelSize: Theme.fMeta
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            objectName: "heldLineLeft"
            text: Day.leftText(root.session.deadline_at, root.nowMs) + " left"
            color: Theme.danger
            monospace: true
            font.pixelSize: Theme.fBody
            font.weight: Font.Bold
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            text: "double-click to go in"
            color: Theme.faint
            font.pixelSize: Theme.fMeta
            anchors.verticalCenter: parent.verticalCenter
        }
        TBtn {
            text: "Leave"
            iconName: "back"
            tone: "danger"
            small: true
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.leave()
        }
    }

    Column {
        id: col
        visible: !root.compact
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 16
        spacing: 12

        Item {
            width: parent.width
            height: 34
            Row {
                spacing: 10
                anchors.verticalCenter: parent.verticalCenter
                Avatar { initials: Theme.initials(root.admin ? root.admin.name : ""); size: 30
                         anchors.verticalCenter: parent.verticalCenter }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1
                    Txt { text: root.admin ? (root.admin.name || "Admin") : ""; color: Theme.ink
                          font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                    Txt { text: root.admin ? (root.admin.hostname || "") : ""; color: Theme.faint
                          monospace: true; font.pixelSize: Theme.fMeta }
                }
            }
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Ring {
                    width: 20; height: 20
                    color: Theme.danger
                    fraction: Day.leftFraction(root.session.entered_at, root.session.deadline_at, root.nowMs)
                    anchors.verticalCenter: parent.verticalCenter
                }
                Txt {
                    objectName: "heldLeft"
                    text: Day.leftText(root.session.deadline_at, root.nowMs)
                    color: Theme.danger
                    monospace: true
                    font.pixelSize: Theme.fBody
                    font.weight: Font.Bold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        Rectangle { width: parent.width; height: 1; color: Theme.line }

        Txt {
            width: parent.width
            text: root.says.sentence || ""
            color: Theme.dim
            font.pixelSize: Theme.fBody
            wrapMode: Text.WordWrap
        }

        Item {
            width: parent.width
            height: 28
            Txt {
                text: "Double-click to go in"
                color: Theme.faint
                font.pixelSize: Theme.fMeta
                anchors.verticalCenter: parent.verticalCenter
            }
            TBtn {
                objectName: "heldLeave"
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: "Leave"
                iconName: "back"
                tone: "danger"
                small: true
                onClicked: root.leave()
            }
        }
    }
}
