import QtQuick
import "."

// THE SESSION WINDOW: entering a worker's machine opens its screen here. One window over the console, full
// screen if wanted; Back to the console keeps the session, Leave ends it. See / See and control and the
// screen itself need the Worker to send its screen, which is not built yet (`cannot`): the window says so
// rather than drawing a pretend desktop.
Item {
    id: root
    objectName: "sessionWindow"
    anchors.fill: parent
    readonly property string cannot: "The Worker does not send its screen yet, so there is nothing to watch or control here"
    readonly property var s: falcon.session || ({})
    readonly property var m: s.pc_id !== undefined ? Fleet.byPc[s.pc_id] || null : null
    property bool hidden: false
    property bool full: false
    property string mode: "control"
    visible: falcon.traversing && m !== null && !hidden && !Nav.boss
    z: 50
    onMChanged: { hidden = false; full = false }

    readonly property int secs: { var t = Time.ms(s.deadline_at); return t === null ? -1 : Math.max(0, Math.floor((t - Time.now) / 1000)) }
    readonly property string who: m && m.user ? m.user : "Nobody"

    Rectangle { anchors.fill: parent; color: Theme.scrim }
    MouseArea { anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.AllButtons; onWheel: function (w) { w.accepted = true } }

    Rectangle {
        id: win
        width: root.full ? parent.width : Math.min(1180, parent.width * 0.96)
        height: root.full ? parent.height : Math.min(parent.height - 40, col.implicitHeight + 32)
        anchors.centerIn: parent
        radius: root.full ? 0 : Theme.radius
        color: Theme.surface
        border.color: Theme.border
        MouseArea { anchors.fill: parent }
        Column {
            id: col
            x: 16; y: 16
            width: parent.width - 32
            spacing: 12
            Row {
                width: parent.width
                spacing: 10
                Icon { name: "desktop"; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: root.m ? root.m.host : ""; mono: true; font.pixelSize: 15; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
                Txt { text: root.who === "Nobody" ? "nobody signed in" : root.who + "'s session"; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
                Segmented { enabled: false; value: root.mode; options: [{ value: "see", label: "See" }, { value: "control", label: "See and control" }]; anchors.verticalCenter: parent.verticalCenter }
            }
            Row {
                spacing: 8
                Txt { anchors.verticalCenter: parent.verticalCenter; mono: true; elide: Text.ElideNone; rightPadding: 6
                      color: root.secs >= 0 && root.secs < 300 ? Theme.crit : Theme.text2
                      text: root.secs < 0 ? "no time limit" : Math.floor(root.secs / 60) + ":" + Time.pad(root.secs % 60) + " left" }
                Btn { small: true; text: "Extend"; onClicked: falcon.call("hierarchy.extend_session", { session_id: root.s.session_id }, function (ok, r) {
                          if (ok) Msg.ok(falcon.extensionMinutes + " more minutes · recorded"); else Msg.failed(r.message || "Not extended") }) }
                Btn { small: true; iconName: root.full ? "fullscreenexit" : "fullscreen"; text: root.full ? "Smaller" : "Full screen"; onClicked: root.full = !root.full }
                Btn { small: true; text: "Back to the console"; onClicked: { root.hidden = true; Msg.ok("Still in " + root.m.host + " · return to it from the machine") } }
                Btn { small: true; danger: true; text: "Leave"
                      onClicked: { var h = root.m.host, u = root.m.user
                                   falcon.call("hierarchy.end_session", { session_id: root.s.session_id }, function (ok, r) {
                                       if (ok) Msg.ok("Left " + h + (u ? " · " + u + " has it back" : "")); else Msg.failed(r.message || "Could not leave") }) } }
            }
            Rectangle {
                width: parent.width
                height: root.full ? win.height - 180 : Math.min(560, width * 0.56)
                radius: 6
                color: Theme.screen
                Column {
                    anchors.centerIn: parent
                    width: Math.min(460, parent.width - 40)
                    spacing: 8
                    Icon { name: "desktop"; size: 30; color: Theme.screenMute; anchors.horizontalCenter: parent.horizontalCenter }
                    Txt { width: parent.width; horizontalAlignment: Text.AlignHCenter; color: Theme.screenText; font.weight: Font.Medium; text: "You are in " + (root.m ? root.m.host : "") }
                    Txt { width: parent.width; horizontalAlignment: Text.AlignHCenter; color: Theme.screenMute; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone; text: root.cannot + "." }
                }
            }
            Row {
                width: parent.width
                spacing: 18
                Txt { width: (parent.width - 18) / 2; color: Theme.text2; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                      text: root.who === "Nobody" ? "Nobody is signed in to see anything." : root.who + " is locked out while you are in." }
                Txt { width: (parent.width - 18) / 2; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                      text: "Only one session at a time on " + (root.m ? root.m.host : "it") + "; nobody else can enter while you are in. Recorded in the audit log." }
            }
        }
    }
}
