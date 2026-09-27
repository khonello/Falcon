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
//
// It is THE ONE way a session is shown (the user, 27 Sep 2026: "why is the traversal alert never consistent"):
//   inside    You are inside Ama's machine   OPS-07  24:05 left         Esc steps out  Extend  Leave
//   holding   You are holding Ama's machine  OPS-07  24:05 left         Go in          Extend  Leave
//   blocked   The Super User is in charge of your machine                                     Claim
// and the connection's two states join it, in the same bar (ST01, ST03) -- no red alarm for a blip:
//   lost      Lost the connection to the Engine.  Retrying -- next try in 4 s.   Your session ... until 14:50   Retry now
//   renamed   Connected -- but this machine's name has changed.  Registered as SU-PC; it now says ...     Understood
// No pill, no second banner, no status-line echo: the same bar, the same place.
Rectangle {
    id: root

    property string name: ""
    property string hostname: ""
    property var session: ({})
    property double nowMs: Date.now()
    property string mode: "inside"          // inside | holding | blocked | lost | renamed
    property int retryIn: 0
    property string heldLine: ""            // lost: what happens to the session held when the link dropped
    property var notice: null               // renamed: {expected, announced}
    property string blockedBy: ""
    signal extend()
    signal leave()
    signal stepOut()
    signal goIn()
    signal claim()
    signal retry()
    signal understood()

    implicitHeight: 38
    radius: Theme.radiusMd
    color: Qt.rgba(1, 1, 1, 0.03)
    readonly property bool conn: mode === "lost" || mode === "renamed"
    border.color: mode === "lost" ? Theme.line2 : mode === "renamed" ? Qt.rgba(Theme.warn.r, Theme.warn.g, Theme.warn.b, 0.5)
                                   : Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.45)
    border.width: 1

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10
        Icon {
            visible: root.conn
            name: root.mode === "lost" ? "globe" : "warn"
            size: 15
            color: root.mode === "lost" ? Theme.dim : Theme.warn
            anchors.verticalCenter: parent.verticalCenter
        }
        Ring {
            visible: !root.conn && root.mode !== "blocked"
            width: 16; height: 16
            color: Theme.danger
            fraction: Day.leftFraction(root.session.entered_at, root.session.deadline_at, root.nowMs)
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            objectName: "lidWho"
            // only a Super User can block an operator, so the sentence names them once
            text: root.mode === "lost" ? "Lost the connection to the Engine."
                  : root.mode === "renamed" ? "Connected — but this machine's name has changed."
                  : root.mode === "blocked" ? "The Super User is in charge of your machine"
                  : (root.mode === "holding" ? "You are holding " : "You are inside ") + root.name
            color: Theme.ink
            font.pixelSize: Theme.fBody
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            visible: root.conn
            text: root.mode === "lost" ? (root.retryIn > 0 ? "Retrying — next try in " + root.retryIn + " s." : "Trying now…")
                  : root.notice ? "Registered as " + root.notice.expected + "; this machine now says " + root.notice.announced
                                  + ". Noted for your administrator; you can carry on." : ""
            color: Theme.dim
            font.pixelSize: Theme.fMeta
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            visible: !root.conn && root.mode !== "blocked"
            text: root.hostname
            color: Theme.faint
            monospace: true
            font.pixelSize: Theme.fMeta
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            visible: !root.conn && root.mode !== "blocked" && !!root.session && !!root.session.deadline_at
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

        Txt {
            visible: root.mode === "lost" && root.heldLine !== ""
            text: root.heldLine
            color: Theme.warn
            font.pixelSize: Theme.fMeta
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
        GBtn {
            objectName: "lidRetry"
            visible: root.mode === "lost"
            text: "Retry now"
            small: true
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.retry()
        }
        GBtn {
            objectName: "lidUnderstood"
            visible: root.mode === "renamed"
            text: "Understood"
            small: true
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.understood()
        }
        // stepping out is not leaving: it is said here because nothing invisible is load-bearing
        Txt {
            visible: root.mode === "inside"
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
        TBtn {
            objectName: "lidGoIn"
            visible: root.mode === "holding"
            text: "Go in"
            small: true
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.goIn()
        }
        Item {
            visible: !root.conn && root.mode !== "blocked"
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
            objectName: "lidClaim"
            visible: root.mode === "blocked"
            text: "Claim it back"
            tone: "danger"
            small: true
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.claim()
        }
        TBtn {
            visible: !root.conn && root.mode !== "blocked"
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
