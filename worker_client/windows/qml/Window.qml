import QtQuick
import QtQuick.Controls
import QtQuick.Window

// THE WORKER'S WINDOWS, as the version 1 Worker concept draws them (docs/design/concepts-worker.html). One of seven, chosen by `kind`,
// filled from `spec`; `answer.give(...)` hands the person's answer back to the service. The three that cover the screen (an Admin
// using the machine, locked, an emergency) are one family: one centred composition, a soft dark ground (deep red for an emergency),
// a strip with the times. The viewing bar sits at the top and never takes a click. The task and message windows are cards over the
// person's work; whatever they show also waits in the Falcon program.
//
// Plain words throughout: "R. Mensah is using this machine", never "traversal". The palette is the console's, written out rather
// than imported -- the Worker package does not depend on the Operator Client.
Window {
    id: win

    readonly property bool covers: kind === "blocked" || kind === "locked" || kind === "emergency"
    readonly property bool bar: kind === "viewing"      // a small notice at the top of the screen that the click goes through

    readonly property color pane: "#ffffff"
    readonly property color ground: "#f8f9fb"
    readonly property color soft2: "#eef0f3"
    readonly property color line: "#e2e5ea"
    readonly property color edge: "#cdd2da"
    readonly property color ink: "#191d25"
    readonly property color dim: "#4a5160"
    readonly property color faint: "#737b8a"
    readonly property color accent: "#2459d6"
    readonly property color accentSoft: Qt.rgba(36 / 255, 89 / 255, 214 / 255, 0.09)
    readonly property color warn: "#b58105"
    readonly property color warnSoft: Qt.rgba(181 / 255, 129 / 255, 5 / 255, 0.12)
    readonly property color white: "#ffffff"
    readonly property string sans: "IBM Plex Sans"          // bundled (worker_client/fonts), as the concept sets it

    visible: true
    color: "transparent"
    title: "Falcon"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | (covers ? Qt.WindowDoesNotAcceptFocus : 0)
           | (bar ? (Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput) : 0)
    width: backdrop ? 1440 : covers ? Screen.width : card.width + 48
    height: backdrop ? 900 : covers ? Screen.height : card.height + 48
    x: backdrop || covers ? 0 : bar ? (Screen.width - width) / 2 : (Screen.width - width) / 2
    y: backdrop || covers ? 0 : bar ? 0 : Math.max(24, (Screen.height - height) / 2 - 40)

    function when(iso) {
        if (!iso) return ""
        var d = new Date(iso), now = new Date()
        var day = d.toDateString() === now.toDateString() ? "today" : Qt.formatDateTime(d, "dddd d MMM")
        return day + " at " + Qt.formatDateTime(d, "HH:mm")
    }
    function hhmm(iso) { return iso ? Qt.formatDateTime(new Date(iso), "HH:mm") : "" }
    function initials(n) { var p = String(n || "IT").split(/[ .]+/).filter(function (x) { return x }); return (p.length > 1 ? p[0][0] + p[1][0] : String(n || "IT").slice(0, 2)).toUpperCase() }
    function along(a, b) { if (!a || !b) return 0; var s = new Date(a).getTime(), e = new Date(b).getTime(); return Math.max(0, Math.min(1, (Date.now() - s) / Math.max(1, e - s))) }

    // a desktop behind, only for pictures of the window (--shot)
    Rectangle {
        anchors.fill: parent
        visible: backdrop && !win.covers
        gradient: Gradient { orientation: Gradient.Horizontal
                             GradientStop { position: 0; color: "#c9d3df" }
                             GradientStop { position: 1; color: "#e4e8ee" } }
    }

    // --- the three covers: one family ----------------------------------------------------------------------------------------------
    Rectangle {
        anchors.fill: parent
        visible: win.covers
        gradient: Gradient {
            GradientStop { position: 0; color: kind === "emergency" ? "#781810" : "#1e2634" }
            GradientStop { position: 1; color: kind === "emergency" ? "#240806" : "#0a0d12" }
        }
        Column {
            anchors.centerIn: parent
            width: Math.min(parent.width * 0.42, 640)
            spacing: 22
            // who, and what it is
            Column {
                width: parent.width
                spacing: 8
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 72; height: 72; radius: 36
                    color: kind === "emergency" ? Qt.rgba(1, 0.47, 0.39, 0.2) : Qt.rgba(91 / 255, 140 / 255, 1, 0.22)
                    border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.14)
                    Text { visible: kind === "blocked"; anchors.centerIn: parent; text: win.initials(spec.occupant_name); color: win.white; font.family: win.sans; font.pixelSize: 22; font.weight: Font.DemiBold }
                    Glyph { visible: kind !== "blocked"; anchors.centerIn: parent; name: kind === "locked" ? "lock" : "warn"; size: 30; color: win.white }
                }
                Item { width: 1; height: 4 }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; font.family: win.sans; font.pixelSize: 12; font.weight: Font.DemiBold; font.letterSpacing: 1
                       color: kind === "emergency" ? "#ffb4a8" : Qt.rgba(1, 1, 1, 0.5)
                       text: kind === "blocked" ? "THIS MACHINE IS IN USE" : kind === "locked" ? "THIS MACHINE IS LOCKED"
                             : "EMERGENCY" + (spec.from ? " · FROM " + String(spec.from).toUpperCase() : "") + (spec.at ? " · " + win.hhmm(spec.at) : "") }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: win.white; font.family: win.sans; font.weight: Font.DemiBold
                       font.pixelSize: kind === "emergency" ? 34 : 26
                       text: kind === "blocked" ? (spec.occupant_name || "Your Admin") + " is using this machine"
                             : kind === "locked" ? (spec.by ? spec.by + " locked this machine" : "Your Admin locked this machine") : (spec.title || "An emergency announcement") }
            }
            // why, in their words (locked), or what to do (an emergency)
            Rectangle {
                visible: (kind === "locked" && !!spec.message) || kind === "emergency"
                width: parent.width
                height: why.implicitHeight + 32
                radius: 14
                color: Qt.rgba(1, 1, 1, kind === "emergency" ? 0.06 : 0.04)
                border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.08)
                Text { id: why; x: 22; y: 16; width: parent.width - 44; wrapMode: Text.WordWrap; font.family: win.sans; font.pixelSize: kind === "emergency" ? 17 : 16
                       horizontalAlignment: kind === "emergency" ? Text.AlignLeft : Text.AlignHCenter; color: Qt.rgba(1, 1, 1, 0.86); lineHeight: 1.2
                       text: kind === "emergency" ? (spec.text || "") : "“" + (spec.message || "") + "”" }
            }
            // the times: came in / leaves by, or locked at / unlocks at
            Rectangle {
                visible: (kind === "blocked" && !!spec.deadline_at) || (kind === "locked" && !!spec.until)
                width: parent.width
                height: 74
                radius: 14
                color: Qt.rgba(1, 1, 1, 0.05)
                border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.08)
                readonly property string a: kind === "blocked" ? (spec.since || "") : (spec.at || "")
                readonly property string b: kind === "blocked" ? (spec.deadline_at || "") : (spec.until || "")
                Column { x: 22; anchors.verticalCenter: parent.verticalCenter; visible: parent.a !== ""
                    Text { text: kind === "blocked" ? "Came in" : "Locked at"; color: Qt.rgba(1, 1, 1, 0.5); font.family: win.sans; font.pixelSize: 12 }
                    Text { text: win.hhmm(parent.parent.a); color: win.white; font.family: win.sans; font.pixelSize: 22; font.weight: Font.DemiBold } }
                Rectangle { x: 120; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 240; height: 6; radius: 3; color: Qt.rgba(1, 1, 1, 0.12); visible: parent.a !== ""
                    Rectangle { width: parent.width * win.along(parent.parent.a, parent.parent.b); height: 6; radius: 3; color: "#8fb0ff" } }
                Column { anchors.right: parent.right; anchors.rightMargin: 22; anchors.verticalCenter: parent.verticalCenter
                    Text { anchors.right: parent.right; text: kind === "blocked" ? "Leaves by" : "Unlocks at"; color: Qt.rgba(1, 1, 1, 0.5); font.family: win.sans; font.pixelSize: 12 }
                    Text { anchors.right: parent.right; text: win.hhmm(parent.parent.b); color: win.white; font.family: win.sans; font.pixelSize: 22; font.weight: Font.DemiBold } }
            }
            // what you can do: nothing to press, or the one button
            Column {
                width: parent.width
                spacing: 10
                Rectangle {
                    visible: kind === "emergency"
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: rl.implicitWidth + 44; height: 44; radius: 8; color: win.white
                    Text { id: rl; anchors.centerIn: parent; text: "I have read this"; color: win.ink; font.family: win.sans; font.pixelSize: 15; font.weight: Font.DemiBold }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: answer.give({ seen: true }) }
                }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: Qt.rgba(1, 1, 1, 0.62); font.family: win.sans; font.pixelSize: 14
                       text: kind === "blocked" ? "You can use it again when they leave. Your work stays as you left it."
                             : kind === "locked" ? (spec.until ? "It unlocks by itself at " + win.hhmm(spec.until) + ", or sooner if your Admin unlocks it." : "It unlocks when your Admin unlocks it.")
                             : "It stays in your Falcon program, under Announcements." }
            }
        }
    }

    // --- someone is looking at your screen; you keep working ---------------------------------------------------------------------------
    Rectangle {
        visible: win.bar
        anchors.horizontalCenter: parent.horizontalCenter
        y: 0
        width: vr.implicitWidth + 32; height: 34
        radius: 12
        color: "#1f2937"
        Rectangle { width: parent.width; height: 12; color: parent.color }
        Row {
            id: vr
            anchors.centerIn: parent
            spacing: 9
            Rectangle { width: 8; height: 8; radius: 4; color: "#f2604c"; anchors.verticalCenter: parent.verticalCenter }
            Glyph { name: "eye"; size: 15; color: "#f3f5f8"; anchors.verticalCenter: parent.verticalCenter }
            Text { anchors.verticalCenter: parent.verticalCenter; color: "#f3f5f8"; font.family: win.sans; font.pixelSize: 13
                   text: (spec.occupant_name || "Your Admin") + " is viewing your screen" + (spec.since ? " · since " + win.hhmm(spec.since) : "") }
        }
    }

    // --- the cards: a task, a message, asking --------------------------------------------------------------------------------------------
    Rectangle {
        id: card
        visible: !win.covers && !win.bar
        width: kind === "task" ? 560 : kind === "message" ? 500 : 380
        height: body.implicitHeight + 44
        anchors.centerIn: backdrop ? parent : undefined
        x: 24; y: 24
        radius: 12
        color: win.pane
        border.width: 1
        border.color: win.line

        Column {
            id: body
            x: 22; y: 22
            width: parent.width - 44
            spacing: 12

            // --- a task given to you: who and by when, what it is, what will show the work, Start (never Complete) --------------------------
            Column {
                visible: kind === "task"
                width: parent.width
                spacing: 14
                Item {
                    width: parent.width; height: 48
                    Rectangle { id: tav; width: 40; height: 40; radius: 20; color: win.accentSoft; anchors.verticalCenter: parent.verticalCenter
                                Text { anchors.centerIn: parent; text: win.initials(spec.from); color: win.accent; font.family: win.sans; font.pixelSize: 13; font.weight: Font.DemiBold } }
                    Column { anchors.left: tav.right; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter
                        Text { text: (spec.from || "Your Admin") + " gave you a task"; color: win.ink; font.family: win.sans; font.pixelSize: 15; font.weight: Font.DemiBold }
                        Text { visible: !!spec.given; text: spec.given ? win.when(spec.given) : ""; color: win.faint; font.family: win.sans; font.pixelSize: 12 } }
                    Rectangle { visible: !!spec.due; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: dc.implicitWidth + 24; height: 46; radius: 8; color: win.warnSoft
                        Column { id: dc; anchors.centerIn: parent
                            Text { anchors.right: parent.right; text: "Due"; color: win.warn; font.family: win.sans; font.pixelSize: 11 }
                            Text { anchors.right: parent.right; text: spec.due ? Qt.formatDateTime(new Date(spec.due), "dddd d MMM, HH:mm") : ""; color: win.warn; font.family: win.sans; font.pixelSize: 14; font.weight: Font.DemiBold } } }
                }
                Rectangle { width: parent.width; height: 1; color: win.line }
                Text { width: parent.width; wrapMode: Text.WordWrap; color: win.ink; font.family: win.sans; font.pixelSize: 21; font.weight: Font.DemiBold; text: spec.title || "" }
                Text { width: parent.width; wrapMode: Text.WordWrap; color: win.dim; font.family: win.sans; font.pixelSize: 14; lineHeight: 1.2; visible: !!spec.description && spec.description !== spec.title; text: spec.description || "" }
                Rectangle {
                    visible: (spec.signs || []).length > 0
                    width: parent.width; height: sg.implicitHeight + 28; radius: 10; color: win.ground
                    Column {
                        id: sg
                        x: 14; y: 14; width: parent.width - 28; spacing: 8
                        Item { width: parent.width; height: 16
                            Text { text: "WHAT WILL SHOW THE WORK IS DONE"; color: win.faint; font.family: win.sans; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.6 }
                            Text { anchors.right: parent.right; color: win.faint; font.family: win.sans; font.pixelSize: 12
                                   text: (spec.signs || []).filter(function (s) { return s.seen }).length + " of " + (spec.signs || []).length + " so far" } }
                        Repeater {
                            model: spec.signs || []
                            delegate: Rectangle {
                                required property var modelData
                                // what it is, as the concept marks it: a folder (a path), several files (a count), a file (a name); paths and names in mono
                                readonly property string what: modelData.program ? "program" : /[\\/]/.test(modelData.name) ? "folder" : /^(about |\d+ )/i.test(modelData.name) ? "files" : "file"
                                width: sg.width; height: 34; radius: 6; color: win.pane
                                Glyph { x: 10; anchors.verticalCenter: parent.verticalCenter; name: parent.what === "program" ? "window" : parent.what === "folder" ? "folder" : parent.what === "files" ? "files" : "file"; size: 14; color: win.faint }
                                Text { x: 34; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 140; elide: Text.ElideRight; text: modelData.name + (modelData.hint ? " · " + modelData.hint : ""); color: win.ink
                                       font.family: parent.what === "folder" || parent.what === "file" ? "IBM Plex Mono" : win.sans; font.pixelSize: parent.what === "folder" || parent.what === "file" ? 12 : 13 }
                                Rectangle { anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; width: st.implicitWidth + 16; height: 20; radius: 10; color: win.soft2
                                            Text { id: st; anchors.centerIn: parent; text: modelData.seen ? "changed " + win.hhmm(modelData.seen) : "not yet"; color: win.faint; font.family: win.sans; font.pixelSize: 11 } }
                            }
                        }
                        Text { width: parent.width; wrapMode: Text.WordWrap; text: "Falcon notices these change by itself. You do not have to report anything."; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                    }
                }
                Rectangle { width: parent.width; height: 1; color: win.line }
                Item {
                    width: parent.width; height: 34
                    Text { anchors.verticalCenter: parent.verticalCenter; width: parent.width - 200; wrapMode: Text.WordWrap; color: win.faint; font.family: win.sans; font.pixelSize: 12
                           text: "An IT Admin checks the work and closes the task." }
                    Row { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                        Act { text: "Later"; onClicked: answer.give({ later: true }) }
                        Act { visible: !spec.started; text: "Start"; primary: true; onClicked: answer.give({ start: true }) }
                        Text { visible: !!spec.started; anchors.verticalCenter: parent.verticalCenter; text: "Started"; color: win.dim; font.family: win.sans; font.pixelSize: 13 } }
                }
            }

            // --- a message from IT: the new message first and large; a reply when it came in a conversation ---------------------------------
            Column {
                visible: kind === "message"
                width: parent.width
                spacing: 12
                Item {
                    width: parent.width; height: 44
                    Rectangle { id: mav; width: 38; height: 38; radius: 19; color: win.accentSoft; anchors.verticalCenter: parent.verticalCenter
                                Text { anchors.centerIn: parent; text: win.initials(spec.from); color: win.accent; font.family: win.sans; font.pixelSize: 13; font.weight: Font.DemiBold } }
                    Column { anchors.left: mav.right; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter
                        Text { text: spec.from || "Your IT Admin"; color: win.ink; font.family: win.sans; font.pixelSize: 15; font.weight: Font.DemiBold }
                        Text { text: "IT" + (spec.at ? " · " + win.when(spec.at) : ""); color: win.faint; font.family: win.sans; font.pixelSize: 12 } }
                }
                Rectangle { width: parent.width; height: 1; color: win.line }
                Rectangle {
                    visible: !!spec.earlier
                    width: parent.width; height: 30; radius: 6; color: win.ground
                    Row { x: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                        Glyph { name: "chat"; size: 13; color: win.faint; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: spec.earlier || ""; color: win.faint; font.family: win.sans; font.pixelSize: 12 } }
                }
                Rectangle {
                    width: Math.min(parent.width, mt.implicitWidth + 36); height: mt.implicitHeight + 28
                    radius: 14
                    color: win.soft2
                    Text { id: mt; x: 18; y: 14; width: Math.min(implicitWidth, body.width - 36); wrapMode: Text.WordWrap; color: win.ink; font.family: win.sans; font.pixelSize: 16; lineHeight: 1.2; text: spec.text || "" }
                }
                // a reply, in the conversation the Admin started; a plain notice has OK
                Column {
                    visible: spec.conversation_id !== undefined && spec.conversation_id !== null
                    width: parent.width
                    spacing: 6
                    Row {
                        width: parent.width
                        spacing: 8
                        Rectangle {
                            width: parent.width - sendB.width - 8; height: 40; radius: 20; color: win.ground; border.width: 1; border.color: win.edge
                            TextInput { id: reply; x: 16; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 32; clip: true; font.family: win.sans; font.pixelSize: 14; color: win.ink
                                        onAccepted: if (text.trim()) answer.give({ reply: text.trim(), conversation_id: spec.conversation_id }) }
                            Text { visible: reply.text === ""; x: 16; anchors.verticalCenter: parent.verticalCenter; text: "Write a reply"; color: win.faint; font.family: win.sans; font.pixelSize: 14 }
                        }
                        Act { id: sendB; text: "Send"; primary: true; enabled: reply.text.trim() !== ""; onClicked: answer.give({ reply: reply.text.trim(), conversation_id: spec.conversation_id }) }
                    }
                    Text { text: "Your reply goes to " + (spec.from || "your IT Admin") + " only."; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                }
                Rectangle { width: parent.width; height: 1; color: win.line }
                Item {
                    width: parent.width; height: 32
                    Text { visible: spec.conversation_id !== undefined && spec.conversation_id !== null; anchors.verticalCenter: parent.verticalCenter; color: win.accent; font.family: win.sans; font.pixelSize: 13; text: "Later"
                           MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: answer.give({ later: true }) } }
                    Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: spec.conversation_id !== undefined && spec.conversation_id !== null
                           text: "It stays in Falcon, under Messages."; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                    Act { anchors.right: parent.right; visible: spec.conversation_id === undefined || spec.conversation_id === null; text: "OK"; primary: true; onClicked: answer.give({ seen: true }) }
                }
            }

            // --- asking for help: out of version 1 (Assistance is cut); kept until the service stops opening it (ENGINE-GAPS #19) ----------------
            Column {
                visible: kind === "ask"
                width: parent.width
                spacing: 10
                Text { text: spec.admins && spec.admins.length > 1 ? "Ask for help" : "Ask " + (spec.to || "your Admin") + " for help"; color: win.ink; font.family: win.sans; font.pixelSize: 15; font.weight: Font.DemiBold }
                Text { width: parent.width; wrapMode: Text.WordWrap; color: win.dim; font.family: win.sans; font.pixelSize: 13
                       text: "They will see that you need them, and write to you when they can. You do not have to say anything now." }
                Flow {
                    width: parent.width; spacing: 8
                    Repeater {
                        model: spec.admins || []
                        Act { required property var modelData; text: "Ask " + modelData.name; primary: spec.admins.length === 1; onClicked: answer.give({ to: modelData.account_id }) }
                    }
                }
            }
        }
    }

    // the console's button, in the two kinds these windows need
    component Act: Rectangle {
        id: act
        property string text: ""
        property bool primary: false
        signal clicked()
        width: actLabel.implicitWidth + (act.text === "Start" ? 48 : 36); height: 36; radius: 7
        opacity: enabled ? 1 : 0.45
        color: primary ? (hov.pressed ? Qt.darker(win.accent, 1.15) : hov.containsMouse ? Qt.lighter(win.accent, 1.12) : win.accent)
                       : hov.containsMouse ? win.ground : win.pane
        border.width: primary ? 0 : 1
        border.color: hov.containsMouse ? win.accent : win.edge
        Row { anchors.centerIn: parent; spacing: 6
              Glyph { visible: act.text === "Start"; name: "play"; size: 12
                      color: act.primary ? win.white : win.ink; anchors.verticalCenter: parent.verticalCenter }
              Text { id: actLabel; text: act.text; color: act.primary ? win.white : win.ink
                     font.family: win.sans; font.pixelSize: 13; font.weight: act.primary ? Font.DemiBold : Font.Normal
                     anchors.verticalCenter: parent.verticalCenter } }
        MouseArea { id: hov; anchors.fill: parent; enabled: act.enabled; hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor; onClicked: act.clicked() }
    }
}
