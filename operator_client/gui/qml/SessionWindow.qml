import QtQuick
import "."

// THE SESSION WINDOW: entering a worker's machine opens its screen here. One window over the console, full
// screen if wanted; Back to the console keeps the session, Leave ends it. See (watch: the person keeps working and
// is told) or See and control (your mouse and keyboard on the machine; the person is locked out).
//
// The Engine's session window (session.screen / session.frame / session.control / session.input): the picture is
// started when the window opens and stopped when it closes; frames arrive as pushes (the latest only, never
// queued); in control mode the mouse and keyboard go back as fractions of the screen, batched a few times a second.
Item {
    id: root
    objectName: "sessionWindow"
    anchors.fill: parent
    readonly property var s: falcon.session || ({})
    readonly property var m: s.pc_id !== undefined ? Fleet.byPc[s.pc_id] || null : null
    property bool hidden: false
    property bool full: false
    property string mode: "control"
    property string frame: ""             // the latest picture, as a data URL
    property string problem: ""           // why there is no picture, when there is none
    property bool streaming: false
    property var queue: []                // input waiting to be sent
    readonly property bool shown: falcon.traversing && m !== null && !hidden && !Nav.boss
    visible: shown
    z: 50
    onMChanged: { hidden = false; full = false }

    readonly property int secs: { var t = Time.ms(s.deadline_at); return t === null ? -1 : Math.max(0, Math.floor((t - Time.now) / 1000)) }
    readonly property string who: m && m.user ? m.user : "Nobody"

    function start() {
        if (streaming || !s.session_id) return
        streaming = true; problem = ""; frame = ""
        falcon.call("session.screen", { session_id: s.session_id, action: "start", width: 1280, fps: 3 }, function (ok, r) {
            if (!ok) { root.streaming = false; root.problem = r && r.message ? r.message : "The machine did not send its screen" }
        })
    }
    function stop() {
        if (!streaming) return
        streaming = false
        if (s.session_id) falcon.call("session.screen", { session_id: s.session_id, action: "stop" }, function () {})
    }
    onShownChanged: shown ? start() : stop()
    Connections {
        target: falcon
        function onPushReceived(type, payload) {
            if (type === "session.frame" && payload && payload.session_id === root.s.session_id && payload.png_b64) root.frame = "data:image/png;base64," + payload.png_b64
            if (type === "screen.stop" || type === "session.ended") { root.streaming = false; root.frame = "" }
        }
    }
    function setMode(v) {
        falcon.call("session.control", { session_id: s.session_id, mode: v }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not changed"); return }
            root.mode = v
            Msg.ok(v === "control" ? "Your mouse and keyboard are on " + root.m.host + (root.m.user ? " · " + root.m.user + " is locked out" : "")
                                    : "Watching only · " + (root.m.user || "its person") + " can use " + root.m.host + " again")
        })
    }
    // input, in control mode: positions as fractions of the picture; sent in batches
    function push(e) { if (mode !== "control" || !streaming) return; var q = queue.slice(); q.push(e); if (q.length > 200) q = q.slice(q.length - 200); queue = q }
    Timer { interval: 80; repeat: true; running: root.queue.length > 0
            onTriggered: { var ev = root.queue; root.queue = []; falcon.call("session.input", { session_id: root.s.session_id, events: ev }, function () {}) } }
    // the keys that are not text, as Windows virtual-key codes
    readonly property var vk: { var o = {}; o[Qt.Key_Return] = 13; o[Qt.Key_Enter] = 13; o[Qt.Key_Backspace] = 8; o[Qt.Key_Tab] = 9; o[Qt.Key_Escape] = 27
        o[Qt.Key_Left] = 37; o[Qt.Key_Up] = 38; o[Qt.Key_Right] = 39; o[Qt.Key_Down] = 40; o[Qt.Key_Delete] = 46; o[Qt.Key_Home] = 36; o[Qt.Key_End] = 35
        o[Qt.Key_PageUp] = 33; o[Qt.Key_PageDown] = 34; o[Qt.Key_Shift] = 16; o[Qt.Key_Control] = 17; o[Qt.Key_Alt] = 18; o[Qt.Key_Meta] = 91
        for (var f = 0; f < 12; f++) o[Qt.Key_F1 + f] = 112 + f
        return o }

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
                Segmented { value: root.mode; options: [{ value: "see", label: "See" }, { value: "control", label: "See and control" }]; anchors.verticalCenter: parent.verticalCenter
                            onPicked: function (v) { if (v !== root.mode) root.setMode(v) } }
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
                                   root.stop()
                                   falcon.call("hierarchy.end_session", { session_id: root.s.session_id }, function (ok, r) {
                                       if (ok) Msg.ok("Left " + h + (u ? " · " + u + " has it back" : "")); else Msg.failed(r.message || "Could not leave") }) } }
            }
            Rectangle {
                id: screen
                width: parent.width
                height: root.full ? win.height - 180 : Math.min(560, width * 0.56)
                radius: 6
                color: Theme.screen
                clip: true
                Image {
                    id: pic
                    anchors.fill: parent
                    source: root.frame
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    cache: false
                    asynchronous: false
                    focus: root.shown && root.mode === "control"
                    Keys.onPressed: function (e) {
                        var code = root.vk[e.key]
                        if (code !== undefined) root.push({ t: "key", down: true, vk: code })
                        else if (e.text) root.push({ t: "text", text: e.text })
                        e.accepted = true
                    }
                    Keys.onReleased: function (e) { var code = root.vk[e.key]; if (code !== undefined) root.push({ t: "key", down: false, vk: code }); e.accepted = true }
                }
                // where the picture sits inside the box (it keeps its shape), so a position is a fraction of the machine's screen
                readonly property real pw: pic.paintedWidth
                readonly property real ph: pic.paintedHeight
                readonly property real ox: (width - pw) / 2
                readonly property real oy: (height - ph) / 2
                function fx(x) { return Math.max(0, Math.min(1, (x - ox) / Math.max(1, pw))) }
                function fy(y) { return Math.max(0, Math.min(1, (y - oy) / Math.max(1, ph))) }
                function btn(b) { return b === Qt.RightButton ? "right" : b === Qt.MiddleButton ? "middle" : "left" }
                MouseArea {
                    anchors.fill: parent
                    enabled: root.frame !== ""
                    hoverEnabled: root.mode === "control"
                    acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
                    cursorShape: root.mode === "control" ? Qt.ArrowCursor : Qt.ForbiddenCursor
                    property real last: 0
                    onPositionChanged: function (e) { if (Date.now() - last < 40) return; last = Date.now(); root.push({ t: "move", x: screen.fx(e.x), y: screen.fy(e.y) }) }
                    onPressed: function (e) { pic.forceActiveFocus(); root.push({ t: "down", button: screen.btn(e.button), x: screen.fx(e.x), y: screen.fy(e.y) }) }
                    onReleased: function (e) { root.push({ t: "up", button: screen.btn(e.button), x: screen.fx(e.x), y: screen.fy(e.y) }) }
                    onWheel: function (w) { root.push({ t: "wheel", delta: w.angleDelta.y }); w.accepted = true }
                }
                Column {
                    visible: root.frame === ""
                    anchors.centerIn: parent
                    width: Math.min(460, parent.width - 40)
                    spacing: 8
                    Icon { name: "desktop"; size: 30; color: Theme.screenMute; anchors.horizontalCenter: parent.horizontalCenter }
                    Txt { width: parent.width; horizontalAlignment: Text.AlignHCenter; color: Theme.screenText; font.weight: Font.Medium; text: "You are in " + (root.m ? root.m.host : "") }
                    Txt { width: parent.width; horizontalAlignment: Text.AlignHCenter; color: Theme.screenMute; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                          text: root.problem !== "" ? root.problem + "." : "Waiting for its screen…" }
                    Btn { visible: root.problem !== ""; small: true; text: "Try again"; anchors.horizontalCenter: parent.horizontalCenter; onClicked: root.start() }
                }
            }
            Row {
                width: parent.width
                spacing: 18
                Txt { width: (parent.width - 18) / 2; color: Theme.text2; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                      text: root.who === "Nobody" ? "Nobody is signed in to see anything."
                          : root.mode === "control" ? root.who + " is locked out while you are in, and sees who is working on it."
                          : root.who + " keeps working and sees that you are watching." }
                Txt { width: (parent.width - 18) / 2; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                      text: "Only one session at a time on " + (root.m ? root.m.host : "it") + "; nobody else can enter while you are in. Recorded in the audit log." }
            }
        }
    }
}
