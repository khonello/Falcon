import QtQuick
import QtQuick.Controls
import QtQuick.Window
import "../../windows/qml" as W

// THE FALCON PROGRAM ON A WORKER'S MACHINE, as the version 1 Worker concept draws it (docs/design/concepts-worker.html). The home of
// Falcon on this machine: everything the other windows show, and everything the person closed, missed or was away for, is gathered
// here. One wide window, opened from the tray or the Start menu, closing it only hides it. Today shows what needs the person at once
// (tasks, messages, announcements side by side, most urgent first); the tabs hold each whole list; My machine shows what IT asks for
// on the phone. It shows what the Worker service on this machine knows, and says when that is not live.
Window {
    id: win
    objectName: "program"
    title: "Falcon"
    width: 1040
    height: 648
    minimumWidth: 860
    minimumHeight: 560
    visible: false
    color: pane
    readonly property color pane: "#ffffff"
    readonly property color ground: "#f3f4f6"
    readonly property color soft: "#f8f9fb"
    readonly property color soft2: "#eef0f3"
    readonly property color line: "#e2e5ea"
    readonly property color edge: "#cdd2da"
    readonly property color ink: "#191d25"
    readonly property color dim: "#4a5160"
    readonly property color faint: "#737b8a"
    readonly property color faintest: "#a6adb9"
    readonly property color accent: "#2459d6"
    readonly property color accentSoft: Qt.rgba(36 / 255, 89 / 255, 214 / 255, 0.09)
    readonly property color warn: "#b58105"
    readonly property color bad: "#c8331f"
    readonly property string sans: "IBM Plex Sans"          // bundled (worker_client/fonts), as the concept sets it
    readonly property real side: 28                         // the sheet's margin
    property string tab: startTab || "today"
    readonly property var view: program.view || ({})
    readonly property bool live: !program.away && view.connected !== false
    readonly property var tasks: view.tasks || []
    readonly property var notes: view.announcements || []
    readonly property var chats: view.messages || []
    readonly property var closed: view.closed || []     // closed this month
    readonly property var mach: view.machine || ({})
    readonly property var toStart: tasks.filter(function (t) { return !t.started })
    readonly property var started: tasks.filter(function (t) { return t.started })
    readonly property int fresh: notes.filter(function (a) { return a.id > program.seenAlert }).length
    readonly property int unread: chats.filter(function (c) { return c.unread > 0 }).length
    property var pickTask: null
    property var pickNote: null
    property var pickChat: null
    property string draft: ""
    // Ask IT: one line to every IT Admin, one request at a time; the conversation opens here when one accepts
    property bool asking: false
    property string askLine: ""
    property var sentRequest: null                      // what was sent from here, until it is answered
    readonly property var myRequest: view.request || sentRequest
    function dayOf(iso) { var d = new Date(iso), n = new Date(), y = new Date(n.getTime() - 86400000); return d.toDateString() === n.toDateString() ? "Today" : d.toDateString() === y.toDateString() ? "Yesterday" : Qt.formatDateTime(d, "dddd d MMM") }
    readonly property var curTask: { for (var i = 0; i < tasks.length; i++) if (tasks[i].id === pickTask) return tasks[i]; return toStart[0] || tasks[0] || null }
    readonly property var curNote: { for (var i = 0; i < notes.length; i++) if (notes[i].id === pickNote) return notes[i]; return notes[0] || null }
    readonly property var curChat: { for (var i = 0; i < chats.length; i++) if (chats[i].id === pickChat) return chats[i]; return chats[0] || null }
    onCurChatChanged: if (curChat && !previewOnly) program.openConversation(curChat.id)

    function when(iso) {
        if (!iso) return ""
        var d = new Date(iso), now = new Date()
        if (d.toDateString() === now.toDateString()) return "today at " + Qt.formatDateTime(d, "HH:mm")
        var tomorrow = new Date(now.getTime() + 86400000)
        if (d.toDateString() === tomorrow.toDateString()) return "tomorrow at " + Qt.formatDateTime(d, "HH:mm")
        return Qt.formatDateTime(d, "dddd d MMM") + " at " + Qt.formatDateTime(d, "HH:mm")
    }
    function ago(iso) {
        if (!iso) return ""
        var m = Math.round((Date.now() - new Date(iso)) / 60000)
        return m < 1 ? "just now" : m < 60 ? m + " min ago" : m < 1440 ? Math.round(m / 60) + " h ago" : m < 2880 ? "yesterday" : m < 10080 ? Qt.formatDateTime(new Date(iso), "dddd")
             : m < 20160 ? "last week" : Qt.formatDateTime(new Date(iso), "d MMM")
    }
    function up(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : "" }
    function daysFrom(iso) { var a = new Date(iso), b = new Date(); a.setHours(0, 0, 0, 0); b.setHours(0, 0, 0, 0); return Math.round((a - b) / 86400000) }
    function inDays(iso) { var n = daysFrom(iso); return n < 0 ? "" : n === 0 ? "today" : n === 1 ? "tomorrow" : "in " + n + " days" }
    // near days by name, as a person says them: today at 07:58, yesterday at 15:20, Sunday at 02:14, Friday 31 Oct, last week
    function dayAt(iso) {
        if (!iso) return ""
        var n = -daysFrom(iso), hm = Qt.formatDateTime(new Date(iso), "HH:mm")
        return n === 0 ? "today at " + hm : n === 1 ? "yesterday at " + hm : n < 3 ? Qt.formatDateTime(new Date(iso), "dddd") + " at " + hm
             : n < 7 ? Qt.formatDateTime(new Date(iso), "dddd d MMM") : n < 14 ? "last week" : Qt.formatDateTime(new Date(iso), "d MMM")
    }
    function startedWord(t) { return t.started_at ? "started " + Qt.formatDateTime(new Date(t.started_at), "dddd") : "started" }
    function short(iso) { return daysFrom(iso) === 0 ? Qt.formatDateTime(new Date(iso), "HH:mm") : Qt.formatDateTime(new Date(iso), "d MMM") }
    function initials(n) { var p = String(n || "IT").split(/[ .]+/).filter(function (x) { return x }); return (p.length > 1 ? p[0][0] + p[1][0] : String(n || "IT").slice(0, 2)).toUpperCase() }
    function noteLine(a) { return (a.from ? a.from + " · " : "") + dayAt(a.at) + (a.read_at ? " · you read it at " + Qt.formatDateTime(new Date(a.read_at), "HH:mm") : "") }
    function askNow() { win.asking = true; win.tab = "messages" }
    // a sign of the work, marked as what it is: a folder (a path), several files (a count), a file (a name)
    function signKind(s) { return s.program ? "window" : /[\\/]/.test(s.name) ? "folder" : /^(about |\d+ )/i.test(s.name) ? "files" : "file" }
    function kindWord(k) { return k === "emergency" ? "Emergency" : k === "warning" ? "Warning" : "Announcement" }
    function kindColor(k) { return k === "emergency" ? bad : k === "warning" ? warn : dim }
    function kindFill(k) { return k === "emergency" ? Qt.rgba(200 / 255, 51 / 255, 31 / 255, 0.14) : k === "warning" ? Qt.rgba(181 / 255, 129 / 255, 5 / 255, 0.16) : soft2 }
    function details() {
        var m = mach, s = m.storage || {}
        return ["Name: " + (m.name || ""), "Department: " + (m.department || "none"), "IP address: " + (m.address || "unknown"), "Windows: " + (m.windows || ""), "Falcon: " + (m.falcon || view.version || ""),
                "Signed in as: " + (m.account || "nobody"), "Signed in: " + (m.signed_in_at ? when(m.signed_in_at) : "unknown"),
                "Last restart: " + (m.restarted_at ? when(m.restarted_at) : "unknown"), "Storage: " + (s.free_gb !== undefined ? s.free_gb + " GB free of " + s.total_gb + " GB" : "unknown"),
                "Connection: " + (live ? "connected" : "not connected")].join("\n")
    }
    // what was new when the list was opened stays marked new while it is read
    property int seenAtOpen: 0
    function openNotes() { seenAtOpen = program.seenAlert; program.markAnnouncementsSeen() }
    onTabChanged: if (tab === "announcements") openNotes()
    onVisibleChanged: if (visible && tab === "announcements") openNotes()
    onClosing: function (close) { close.accepted = false; win.hide() }
    Component.onCompleted: if (previewOnly && tab === "announcements") openNotes()

    Item {
        anchors.fill: parent

        // --- header: Falcon, whether this is live, today -------------------------------------------------------------------------------
        Row {
            x: win.side; y: 27; spacing: 12
            Rectangle { width: 38; height: 38; radius: 8; color: win.accent
                        Text { anchors.centerIn: parent; text: "F"; color: "#ffffff"; font.family: win.sans; font.pixelSize: 19; font.weight: Font.DemiBold } }
            Column { anchors.verticalCenter: parent.verticalCenter; spacing: 2
                     Text { text: "Falcon"; color: win.ink; font.family: win.sans; font.pixelSize: 17; font.weight: Font.DemiBold }
                     Text { objectName: "programState"; font.family: win.sans; font.pixelSize: 13; color: win.live ? win.faint : win.warn
                            text: program.away ? "Not reaching this machine's Falcon service. Showing what was last known."
                                : win.view.connected === false ? "Not connected. Showing what was known " + (win.view.as_of ? "at " + Qt.formatDateTime(new Date(win.view.as_of), "HH:mm") + ", " + win.ago(win.view.as_of) : "earlier") + "."
                                : "Connected" } }
        }
        Text { anchors.right: parent.right; anchors.rightMargin: win.side; y: 38; text: Qt.formatDate(new Date(), "dddd d MMM"); color: win.faint; font.family: win.sans; font.pixelSize: 13 }

        // --- tabs: Today gathers what needs you; each other tab holds that whole list ------------------------------------------------------
        Item {
            x: win.side; y: 90; width: parent.width - 2 * win.side; height: 38
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: win.line }
            Row {
                height: parent.height; spacing: 25
                Repeater {
                    model: [{ id: "today", label: "Today", n: 0 }, { id: "tasks", label: "Tasks", n: win.toStart.length }, { id: "messages", label: "Messages", n: win.unread },
                            { id: "announcements", label: "Announcements", n: win.fresh }, { id: "machine", label: "My machine", n: 0 }]
                    delegate: Item {
                        required property var modelData
                        width: lbl.implicitWidth + (cnt.visible ? cnt.width + 6 : 0); height: 38
                        Text { id: lbl; y: 7; text: modelData.label
                               color: win.tab === modelData.id ? win.ink : win.faint; font.family: win.sans; font.pixelSize: 15; font.weight: win.tab === modelData.id ? Font.DemiBold : Font.Normal }
                        Rectangle { id: cnt; visible: modelData.n > 0 && win.tab !== modelData.id; y: 8; x: lbl.implicitWidth + 6
                                    width: Math.max(19, cl.implicitWidth + 12); height: 19; radius: 10; color: win.accent
                                    Text { id: cl; anchors.centerIn: parent; text: modelData.n; color: "#ffffff"; font.family: win.sans; font.pixelSize: 12; font.weight: Font.DemiBold } }
                        Rectangle { visible: win.tab === modelData.id; anchors.bottom: parent.bottom; width: parent.width; height: 3; color: win.accent }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: win.tab = modelData.id; objectName: "tab_" + modelData.id }
                    }
                }
            }
        }

        // --- the page ---------------------------------------------------------------------------------------------------------------------
        Item {
            id: page
            x: win.side; y: 156
            width: parent.width - 2 * win.side
            height: parent.height - 156 - 28

            // TODAY: three columns side by side, most urgent first, and one quiet line about this machine at the foot
            Item {
                visible: win.tab === "today"
                anchors.fill: parent
                Row {
                    id: cols
                    width: parent.width; height: parent.height - foot.height - 8
                    spacing: 36
                    clip: true
                    readonly property real cw: (width - 72) / 3
                    Column {
                        objectName: "todayTasks"
                        width: cols.cw; spacing: 10
                        ColHead { title: "Your tasks"; n: win.toStart.length ? win.toStart.length + " to start" : ""; more: win.tasks.length ? "All " + win.tasks.length : "All"; onAll: win.tab = "tasks" }
                        Repeater {
                            model: win.toStart.slice(0, 2).concat(win.started.slice(0, 1))
                            delegate: Card {
                                required property var modelData
                                dim: modelData.started
                                title: modelData.title
                                text1: "From " + modelData.from + (modelData.started ? " · " + win.startedWord(modelData) : "")
                                text2: modelData.due ? "Due " + win.when(modelData.due) : "No deadline · an IT Admin closes it when it is checked"
                                text2Color: modelData.due && !modelData.started ? win.warn : win.faint
                                act: modelData.started ? "" : "Start"
                                actOk: win.live
                                onActed: program.startTask(modelData.id)
                                onPicked: { win.pickTask = modelData.id; win.tab = "tasks" }
                            }
                        }
                        Text { visible: !win.live && win.toStart.length > 0; width: parent.width; wrapMode: Text.WordWrap; text: "Start waits until you are connected again."; color: win.faint; font.family: win.sans; font.pixelSize: 13 }
                        Quiet { visible: win.tasks.length === 0; text: "Nothing is assigned to you right now." }
                    }
                    Column {
                        objectName: "todayMessages"
                        width: cols.cw; spacing: 10
                        ColHead { title: "Messages"; n: win.unread ? win.unread + " new" : ""; ask: true; onAll: win.tab = "messages"; onAsked: win.askNow() }
                        Repeater {
                            model: win.chats.slice(0, 3)
                            delegate: Card {
                                required property var modelData
                                dim: !modelData.unread
                                title: modelData.with
                                text1: modelData.last
                                text1Lines: 3
                                text2: win.up(win.dayAt(modelData.at)) + (modelData.from === "You" ? " · you replied" : "")
                                act: modelData.unread ? "Reply" : ""
                                actLink: true
                                actOk: win.live
                                onActed: { win.pickChat = modelData.id; win.tab = "messages" }
                                onPicked: { win.pickChat = modelData.id; win.tab = "messages" }
                            }
                        }
                        Quiet { visible: win.chats.length === 0; text: "No messages. Your IT Admins write to you here." }
                    }
                    Column {
                        objectName: "todayNotes"
                        width: cols.cw; spacing: 10
                        ColHead { title: "Announcements"; n: win.fresh ? win.fresh + " new" : ""; onAll: win.tab = "announcements" }
                        Repeater {
                            model: win.notes.slice(0, 3)
                            delegate: Card {
                                required property var modelData
                                dim: modelData.id <= program.seenAlert
                                title: modelData.title || modelData.body.slice(0, 60)
                                text1: modelData.id > program.seenAlert && modelData.title ? modelData.body : ""
                                text1Lines: 2
                                text2: (modelData.from ? modelData.from + " · " : "") + win.ago(modelData.at)
                                onPicked: { win.pickNote = modelData.id; win.tab = "announcements" }
                            }
                        }
                        Quiet { visible: win.notes.length === 0; text: "No announcements yet." }
                    }
                }
                Item {
                    id: foot
                    anchors.bottom: parent.bottom
                    width: parent.width; height: 28
                    Rectangle { width: parent.width; height: 1; color: win.line }
                    Row { y: 10; spacing: 27
                        Text { text: (win.mach.name || "") + (win.mach.department ? " · " + win.mach.department : ""); color: win.faint; font.family: win.sans; font.pixelSize: 13 }
                        Text { text: "Falcon " + (win.mach.falcon || win.view.version || ""); color: win.faint; font.family: win.sans; font.pixelSize: 13 }
                        Text { text: win.view.held_by ? win.view.held_by + " is using this machine" : "Nobody else is using this machine"; color: win.faint; font.family: win.sans; font.pixelSize: 13 } }
                }
            }

            // TASKS: every task, picked on the left; the picked one as its window showed it, with Start
            Row {
                visible: win.tab === "tasks"
                anchors.fill: parent
                spacing: 36
                Flickable {
                    width: (parent.width - 36) * 0.444; height: parent.height
                    contentHeight: tl.height; clip: true; boundsBehavior: Flickable.StopAtBounds
                    Column {
                        id: tl
                        width: parent.width; spacing: 10
                        Sec { visible: win.toStart.length > 0; text: "TO START" }
                        Repeater { model: win.toStart
                            delegate: Card { required property var modelData; objectName: "task_" + modelData.id; sel: win.curTask && win.curTask.id === modelData.id
                                title: modelData.title; text1: "From " + modelData.from; text2: modelData.due ? "Due " + win.when(modelData.due) : "No deadline"; text2Color: modelData.due ? win.warn : win.faint
                                onPicked: win.pickTask = modelData.id } }
                        Sec { visible: win.started.length > 0; text: "STARTED" }
                        Repeater { model: win.started
                            delegate: Card { required property var modelData; sel: win.curTask && win.curTask.id === modelData.id
                                title: modelData.title; text1: "From " + modelData.from + " · " + win.startedWord(modelData); text2: modelData.due ? "Due " + win.when(modelData.due) : "No deadline"
                                onPicked: win.pickTask = modelData.id } }
                        Sec { visible: win.closed.length > 0; text: "CLOSED THIS MONTH" }
                        Repeater { model: win.closed
                            delegate: Card { required property var modelData; dim: true; still: true; title: modelData.title
                                text2: "Closed by " + modelData.closed_by + " on " + Qt.formatDateTime(new Date(modelData.closed_at), "d MMM") } }
                        Quiet { visible: win.tasks.length === 0; text: "Nothing is assigned to you right now." }
                    }
                }
                Item {
                    width: (parent.width - 36) * 0.556; height: parent.height
                    visible: win.curTask !== null
                    Flickable {
                        width: parent.width; height: parent.height - 46
                        contentHeight: td.height; clip: true; boundsBehavior: Flickable.StopAtBounds
                        Column {
                            id: td
                            width: parent.width; spacing: 10
                            Row { spacing: 12
                                Av { name: win.curTask ? win.curTask.from : "" }
                                Column { anchors.verticalCenter: parent.verticalCenter; spacing: 1
                                    Text { text: win.curTask ? "A task from " + win.curTask.from : ""; color: win.ink; font.family: win.sans; font.pixelSize: 17; font.weight: Font.DemiBold }
                                    Text { visible: text !== ""; text: win.curTask && win.curTask.given ? "Given " + win.when(win.curTask.given) : ""; color: win.faint; font.family: win.sans; font.pixelSize: 13 } } }
                            Text { width: parent.width; wrapMode: Text.WordWrap; text: win.curTask ? win.curTask.title : ""; color: win.ink; font.family: win.sans; font.pixelSize: 24; font.weight: Font.DemiBold }
                            Text { width: parent.width; wrapMode: Text.WordWrap; visible: text !== ""; color: win.dim; font.family: win.sans; font.pixelSize: 15; lineHeight: 1.15
                                   text: win.curTask && win.curTask.description && win.curTask.description !== win.curTask.title ? win.curTask.description : "" }
                            Text { text: win.curTask ? (win.curTask.due ? "Due " + win.when(win.curTask.due) + (win.inDays(win.curTask.due) ? " · " + win.inDays(win.curTask.due) : "") : "No deadline") : ""; color: win.curTask && win.curTask.due ? win.warn : win.faint
                                   font.family: win.sans; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Sec { visible: sg.count > 0; topPadding: 8; text: "WHAT WILL SHOW THE WORK IS HAPPENING" }
                            Column { width: parent.width; spacing: 5
                                Repeater { id: sg; model: win.curTask ? win.curTask.signs || [] : []
                                    delegate: Rectangle {
                                        required property var modelData
                                        readonly property string what: win.signKind(modelData)
                                        width: td.width; height: 32; radius: 7; color: win.soft
                                        W.Glyph { x: 10; anchors.verticalCenter: parent.verticalCenter; name: parent.what; size: 17; color: win.faint }
                                        Text { x: 42; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 120; elide: Text.ElideRight; text: modelData.name; color: win.ink
                                               font.family: parent.what === "files" || parent.what === "window" ? win.sans : "IBM Plex Mono"; font.pixelSize: parent.what === "files" || parent.what === "window" ? 14 : 13 }
                                        Text { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; color: win.faint; font.family: win.sans; font.pixelSize: 13
                                               text: modelData.seen ? "changed " + Qt.formatDateTime(new Date(modelData.seen), "HH:mm") : "not yet" }
                                    } } }
                        }
                    }
                    Item { anchors.bottom: parent.bottom; width: parent.width; height: 36
                        Text { anchors.verticalCenter: parent.verticalCenter; width: parent.width - 120; wrapMode: Text.WordWrap; color: !win.live && win.curTask && !win.curTask.started ? win.warn : win.faint; font.family: win.sans; font.pixelSize: 13
                               text: !win.live && win.curTask && !win.curTask.started ? "Start waits until you are connected again." : "An IT Admin closes it when the work is checked." }
                        Act { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: !!win.curTask && !win.curTask.started; text: "Start"; primary: true; ok: win.live; objectName: "start_task"
                              onClicked: program.startTask(win.curTask.id) } }
                }
            }

            // MESSAGES: one conversation per Admin who wrote; the person replies, and asks IT to start one
            Row {
                visible: win.tab === "messages"
                anchors.fill: parent
                spacing: 36
                Item {
                    width: (parent.width - 36) * 0.41; height: parent.height
                    Column {
                        width: parent.width; spacing: 10
                        Item { width: parent.width; height: 34
                            Text { anchors.verticalCenter: parent.verticalCenter; text: "Conversations"; color: win.ink; font.family: win.sans; font.pixelSize: 17; font.weight: Font.DemiBold }
                            Act { objectName: "askIT"; anchors.right: parent.right; text: "Ask IT"; primary: !win.myRequest; ok: win.live && !win.myRequest; tip: win.myRequest ? "One request at a time" : !win.live ? "Asking waits until you are connected again" : ""
                                  onClicked: win.asking = true } }
                        Card {
                            objectName: "myRequest"
                            visible: !!win.myRequest
                            still: true
                            dashColor: Qt.rgba(36 / 255, 89 / 255, 214 / 255, 0.55)
                            kind: "Your request · waiting for IT"
                            title: win.myRequest ? win.myRequest.line : ""
                            text2: win.myRequest ? "Sent " + win.when(win.myRequest.at) + " · every IT Admin can see it" : ""
                        }
                        Repeater { model: win.chats
                            delegate: Card { required property var modelData; sel: !win.asking && win.curChat && win.curChat.id === modelData.id
                                avatar: modelData.with; title: modelData.with; pill: modelData.unread ? modelData.unread + " new" : ""; side: win.short(modelData.at)
                                text2: (modelData.from_request ? "From your request · " : "") + (modelData.from ? modelData.from + ": " : "") + modelData.last
                                text2Lines: 2
                                onPicked: { win.asking = false; win.pickChat = modelData.id } } }
                        Quiet { visible: win.chats.length === 0 && !win.myRequest; text: "No messages yet. When an IT Admin writes to you, it is here." }
                    }
                    Text { visible: !!win.myRequest; anchors.bottom: parent.bottom; width: parent.width; wrapMode: Text.WordWrap; text: "One request at a time: Ask IT comes back once this one is accepted or closed."; color: win.faint; font.family: win.sans; font.pixelSize: 13 }
                }
                Item {
                    objectName: "askForm"
                    width: (parent.width - 36) * 0.59; height: parent.height
                    visible: win.asking
                    Column {
                        width: parent.width; spacing: 10
                        Text { text: "Ask IT"; color: win.ink; font.family: win.sans; font.pixelSize: 24; font.weight: Font.DemiBold }
                        Text { width: parent.width; wrapMode: Text.WordWrap; text: "Say in one line what you need. Every IT Admin sees it, and the conversation opens here when one of them accepts."; color: win.dim; font.family: win.sans; font.pixelSize: 15; lineHeight: 1.15 }
                        Sec { topPadding: 8; text: "WHAT DO YOU NEED?" }
                        Rectangle { width: parent.width; height: 41; radius: 10; color: win.pane; border.width: 1; border.color: win.edge
                            TextInput { id: askBox; objectName: "askBox"; x: 14; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 28; clip: true; font.family: win.sans; font.pixelSize: 14; color: win.ink
                                        text: win.askLine; onTextEdited: win.askLine = text; onAccepted: askSend.clicked() } }
                    }
                    Item {
                        anchors.bottom: parent.bottom; width: parent.width; height: 36
                        Text { anchors.verticalCenter: parent.verticalCenter; text: "You can have one request open at a time."; color: win.faint; font.family: win.sans; font.pixelSize: 13 }
                        Row { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                            Act { text: "Cancel"; onClicked: win.asking = false }
                            Act { id: askSend; objectName: "sendRequest"; text: "Send request"; primary: true; ok: win.live && win.askLine.trim() !== ""
                                  onClicked: { program.talk(win.askLine.trim()); win.sentRequest = { line: win.askLine.trim(), at: new Date().toISOString() }; win.askLine = ""; win.asking = false } } }
                    }
                }
                Item {
                    width: (parent.width - 36) * 0.59; height: parent.height
                    visible: win.curChat !== null && !win.asking
                    Flickable {
                        id: th
                        width: parent.width; height: parent.height - comp.height - 12
                        contentHeight: Math.max(msgs.height, height); clip: true; boundsBehavior: Flickable.StopAtBounds
                        onContentHeightChanged: contentY = Math.max(0, contentHeight - height)
                        Column {
                            id: msgs
                            y: Math.max(0, th.height - height)                       // the newest sits just over the reply box
                            width: parent.width; spacing: 9
                            Repeater {
                                model: (program.conversation && program.conversation.messages) || []
                                delegate: Item {
                                    required property var modelData
                                    required property int index
                                    readonly property var all: (program.conversation && program.conversation.messages) || []
                                    readonly property bool newDay: index === 0 || win.dayOf(all[index - 1].at) !== win.dayOf(modelData.at)
                                    width: msgs.width; height: bub.y + bub.height
                                    Text { visible: parent.newDay; width: parent.width; horizontalAlignment: Text.AlignHCenter; text: win.dayOf(modelData.at); color: win.faintest; font.family: win.sans; font.pixelSize: 12 }
                                    Rectangle {
                                        id: bub
                                        y: parent.newDay ? 25 : 0
                                        x: modelData.mine ? parent.width - width : 0
                                        width: Math.min(parent.width * 0.78, bt.implicitWidth + 28); height: bt.implicitHeight + bs.implicitHeight + 23; radius: 14
                                        color: modelData.mine ? "#ebf0fb" : win.soft2          // solid: the corner below is drawn over it
                                        // the corner towards who said it stays sharper
                                        Rectangle { x: modelData.mine ? parent.width - 14 : 0; anchors.bottom: parent.bottom; width: 14; height: 14; radius: 3; color: parent.color }
                                        Text { id: bt; x: 14; y: 10; width: Math.min(implicitWidth, msgs.width * 0.78 - 28); wrapMode: Text.WordWrap; text: modelData.body + (modelData.file ? "\nFile: " + modelData.file.name : "")
                                               color: win.ink; font.family: win.sans; font.pixelSize: 14; lineHeight: 1.1 }
                                        Text { id: bs; x: 14; anchors.top: bt.bottom; anchors.topMargin: 3; text: Qt.formatDateTime(new Date(modelData.at), "HH:mm"); color: win.faint; font.family: win.sans; font.pixelSize: 11 }
                                    }
                                }
                            }
                        }
                    }
                    Row {
                        id: comp
                        anchors.bottom: parent.bottom; width: parent.width; spacing: 12
                        Rectangle {
                            width: parent.width - sendB.width - 12; height: 41; radius: 10; color: win.pane; border.width: 1; border.color: win.edge
                            TextInput { id: ti; objectName: "replyBox"; x: 14; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 28; clip: true
                                        font.family: win.sans; font.pixelSize: 14; color: win.ink; text: win.draft; onTextEdited: win.draft = text
                                        enabled: win.live; onAccepted: if (win.draft.trim()) sendB.clicked() }
                            Text { visible: ti.text === ""; x: 14; anchors.verticalCenter: parent.verticalCenter; color: win.faint; font.family: win.sans; font.pixelSize: 14
                                   text: !win.live ? "Replying waits until you are connected again" : win.curChat ? "Write a reply to " + win.curChat.with : "" }
                        }
                        Act { id: sendB; objectName: "sendReply"; anchors.verticalCenter: parent.verticalCenter; text: "Send"; primary: true; ok: win.live && win.draft.trim() !== ""
                              onClicked: { program.reply(win.curChat.id, win.draft.trim()); win.draft = "" } }
                    }
                }
            }

            // ANNOUNCEMENTS: every one, newest first; the picked one in full
            Row {
                visible: win.tab === "announcements"
                anchors.fill: parent
                spacing: 36
                Flickable {
                    width: (parent.width - 36) * 0.432; height: parent.height
                    contentHeight: al.height; clip: true; boundsBehavior: Flickable.StopAtBounds
                    Column {
                        id: al
                        width: parent.width; spacing: 10
                        Repeater { model: win.notes
                            delegate: Card { required property var modelData; objectName: "note_" + modelData.id; sel: win.curNote && win.curNote.id === modelData.id
                                dim: modelData.kind !== "emergency" && win.daysFrom(modelData.at) < -6
                                tag: win.kindWord(modelData.kind); tagColor: win.kindColor(modelData.kind); tagFill: win.kindFill(modelData.kind); tagNew: modelData.id > win.seenAtOpen
                                title: modelData.title || modelData.body.slice(0, 60); text2: win.noteLine(modelData)
                                onPicked: win.pickNote = modelData.id } }
                        Quiet { visible: win.notes.length === 0; text: "No announcements yet." }
                    }
                }
                Column {
                    width: (parent.width - 36) * 0.568
                    visible: win.curNote !== null
                    spacing: 8
                    Tag { text: win.curNote ? win.kindWord(win.curNote.kind) : ""; ink: win.curNote ? win.kindColor(win.curNote.kind) : win.dim; fill: win.curNote ? win.kindFill(win.curNote.kind) : win.soft2 }
                    Text { width: parent.width; wrapMode: Text.WordWrap; visible: text !== ""; text: win.curNote ? win.curNote.title : ""; color: win.ink; font.family: win.sans; font.pixelSize: 24; font.weight: Font.DemiBold }
                    Text { text: win.curNote ? (win.curNote.from ? "From " + win.curNote.from + " · " : "") + win.dayAt(win.curNote.at) : ""; color: win.faint; font.family: win.sans; font.pixelSize: 13 }
                    Text { width: parent.width; wrapMode: Text.WordWrap; text: win.curNote ? win.curNote.body : ""; color: win.dim; font.family: win.sans; font.pixelSize: 15; lineHeight: 1.15 }
                }
            }

            // MY MACHINE: what IT asks for on the phone, and one click to copy it
            Item {
                visible: win.tab === "machine"
                anchors.fill: parent
                Row {
                    width: parent.width; spacing: 36
                    Facts {
                        width: (parent.width - 36) / 2
                        title: "THIS MACHINE"
                        rows: [["Name", win.mach.name || "—"], ["Department", win.mach.department || "—"], ["IP address", win.mach.address || "—", true], ["Windows", win.mach.windows || "—"],
                               ["Falcon", (win.mach.falcon || win.view.version || "—") + (win.mach.up_to_date ? " · up to date" : "")]]
                    }
                    Facts {
                        width: (parent.width - 36) / 2
                        title: "YOU, TODAY"
                        readonly property var s: win.mach.storage || null
                        rows: [["Signed in as", win.mach.account || "—", true], ["Signed in", win.mach.signed_in_at ? win.up(win.dayAt(win.mach.signed_in_at)) : "—"],
                               ["Last restart", win.mach.restarted_at ? win.up(win.dayAt(win.mach.restarted_at)) : "—"],
                               ["Storage (C:)", s ? s.free_gb + " GB free of " + s.total_gb + " GB" : "—"],
                               ["Connection", win.live ? "Connected to your organisation" + (win.mach.connected_since ? " since " + Qt.formatDateTime(new Date(win.mach.connected_since), "HH:mm") : "") : "Not connected right now"]]
                        meter: s ? s.used_percent : -1
                    }
                }
                Item {
                    anchors.bottom: parent.bottom
                    width: parent.width; height: 36
                    Text { anchors.verticalCenter: parent.verticalCenter; text: (win.view.admins || []).length ? "Your IT Admins: " + win.view.admins.map(function (a) { return a.name }).join(", ") : ""; color: win.dim; font.family: win.sans; font.pixelSize: 13 }
                    Act { objectName: "copyDetails"; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "Copy these details"; onClicked: { program.copyText(win.details()); copied.visible = true; copiedT.restart() } }
                    Text { id: copied; visible: false; anchors.right: parent.right; anchors.rightMargin: 176; anchors.verticalCenter: parent.verticalCenter; text: "Copied"; color: win.faint; font.family: win.sans; font.pixelSize: 13 }
                    Timer { id: copiedT; interval: 2500; onTriggered: copied.visible = false }
                }
            }
        }
    }

    // a quiet note in the corner for something new; it goes by itself and never takes the keyboard
    Connections {
        target: program
        function onToastArrived(t) { if (/^q/.test(String(t.id))) win.sentRequest = null; toasts.push(t); toastWin.next() }
    }
    property var toasts: []
    Window {
        id: toastWin
        objectName: "toast"
        flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        width: 386; height: tcard.height + 16
        x: Screen.width - width - 20; y: Screen.height - height - 70
        color: "transparent"
        visible: false
        property var cur: null
        function next() {
            if (visible || win.toasts.length === 0 || previewOnly) return
            cur = win.toasts.shift()
            visible = true
            hide.restart()
        }
        Timer { id: hide; interval: 9000; onTriggered: { program.ack([toastWin.cur.id]); toastWin.visible = false; toastWin.cur = null; toastWin.next() } }
        Rectangle {
            id: tcard
            x: 8; y: 8; width: parent.width - 16; height: tcol.height + 30; radius: 14; color: win.pane; border.width: 1; border.color: win.edge
            Column { id: tcol; x: 16; y: 15; width: parent.width - 32; spacing: 4
                     Item { width: parent.width; height: 18
                         Text { text: toastWin.cur ? (toastWin.cur.kind === "task" ? "A task is waiting · Falcon" : "New from IT · Falcon") : ""; color: win.faint; font.family: win.sans; font.pixelSize: 13 }
                         Text { anchors.right: parent.right; text: "now"; color: win.faint; font.family: win.sans; font.pixelSize: 13 } }
                     Text { width: parent.width; wrapMode: Text.WordWrap; text: toastWin.cur ? toastWin.cur.title : ""; color: win.ink; font.family: win.sans; font.pixelSize: 17; font.weight: Font.DemiBold }
                     Text { width: parent.width; wrapMode: Text.WordWrap; visible: text !== ""; text: toastWin.cur ? toastWin.cur.text : ""; color: win.warn; font.family: win.sans; font.pixelSize: 13 }
                     Text { topPadding: 4; text: "Open in Falcon"; color: win.accent; font.family: win.sans; font.pixelSize: 14 } }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: { win.tab = toastWin.cur && toastWin.cur.kind === "task" ? "tasks" : toastWin.cur && toastWin.cur.kind === "message" ? "messages" : "announcements"; hide.triggered(); win.show(); win.raise() } }
        }
    }

    // --- the pieces ------------------------------------------------------------------------------------------------------------------------
    component ColHead: Item {
        id: ch
        property string title: ""
        property string n: ""
        property string more: "All"
        property bool ask: false
        signal all()
        signal asked()
        width: parent ? parent.width : 300
        height: 28
        Row { anchors.verticalCenter: parent.verticalCenter; spacing: 8
              Text { text: ch.title; color: win.ink; font.family: win.sans; font.pixelSize: 17; font.weight: Font.DemiBold }
              Rectangle { visible: ch.n !== ""; anchors.verticalCenter: parent.verticalCenter; width: nt.implicitWidth + 15; height: 18; radius: 9; color: win.accent
                          Text { id: nt; anchors.centerIn: parent; text: ch.n; color: "#ffffff"; font.family: win.sans; font.pixelSize: 12; font.weight: Font.DemiBold } } }
        Row { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 4
              Text { visible: ch.ask; text: "Ask IT"; color: win.accent; font.family: win.sans; font.pixelSize: 14; opacity: win.live && !win.myRequest ? 1 : 0.45
                     MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: if (win.live && !win.myRequest) ch.asked() } }
              Text { visible: ch.ask; text: "·"; color: win.accent; font.family: win.sans; font.pixelSize: 14 }
              Text { text: ch.more; color: win.accent; font.family: win.sans; font.pixelSize: 14
                     MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: ch.all() } } }
    }
    component Av: Rectangle {
        property string name: ""
        width: 41; height: 41; radius: 21; color: Qt.rgba(36 / 255, 89 / 255, 214 / 255, 0.16)
        Text { anchors.centerIn: parent; text: win.initials(parent.name); color: win.accent; font.family: win.sans; font.pixelSize: 14; font.weight: Font.DemiBold }
    }
    component Tag: Rectangle {
        id: tg
        property string text: ""
        property color ink: win.dim
        property color fill: win.soft2
        width: tt.implicitWidth + 15; height: 19; radius: 4; color: fill
        Text { id: tt; anchors.centerIn: parent; text: tg.text; color: tg.ink; font.family: win.sans; font.pixelSize: 12; font.weight: Font.DemiBold }
    }
    component Card: Rectangle {
        id: card
        property string kind: ""                // one accent line above the title (your request)
        property string tag: ""
        property color tagColor: win.dim
        property color tagFill: win.soft2
        property bool tagNew: false
        property string avatar: ""
        property string pill: ""
        property string side: ""
        property string title: ""
        property string text1: ""
        property int text1Lines: 3
        property string text2: ""
        property int text2Lines: 3
        property color text2Color: win.faint
        property string act: ""
        property bool actLink: false
        property bool actOk: true
        property bool dim: false
        property bool sel: false
        property bool still: false
        property color dashColor: "transparent"
        readonly property bool dashed: (dim && !sel) || dashColor.a > 0
        signal picked()
        signal acted()
        width: parent ? parent.width : 300
        height: Math.max(cc.height, avatar !== "" ? 41 : 0) + 28
        radius: 11
        color: sel ? win.accentSoft : dashed ? "transparent" : win.pane
        // a card already seen or started: no fill, a dashed edge (the concept's c-card dim)
        border.width: dashed ? 0 : 1
        border.color: sel ? Qt.rgba(36 / 255, 89 / 255, 214 / 255, 0.55) : win.line
        Canvas {
            visible: card.dashed
            anchors.fill: parent
            onPaint: { var g = getContext("2d"); g.reset(); g.strokeStyle = card.dashColor.a > 0 ? card.dashColor : win.line; g.lineWidth = 1; g.setLineDash([4, 3])
                       var r = card.radius, x = 0.5, y = 0.5, w = width - 1, h = height - 1
                       g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); g.stroke() }
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
        }
        MouseArea { anchors.fill: parent; enabled: !card.still; cursorShape: Qt.PointingHandCursor; onClicked: card.picked() }
        Av { visible: card.avatar !== ""; x: 16; y: 14; name: card.avatar }
        Column {
            id: cc
            x: card.avatar !== "" ? 69 : 16; y: 14; width: parent.width - x - 16 - (ab.visible ? ab.width + 12 : 0) - (sd.visible ? sd.implicitWidth + 10 : 0); spacing: 4
            Row { visible: card.tag !== ""; spacing: 6
                  Tag { text: card.tag; ink: card.tagColor; fill: card.tagFill }
                  Rectangle { visible: card.tagNew; anchors.verticalCenter: parent.verticalCenter; width: nw.implicitWidth + 15; height: 18; radius: 9; color: win.accent
                              Text { id: nw; anchors.centerIn: parent; text: "new"; color: "#ffffff"; font.family: win.sans; font.pixelSize: 12; font.weight: Font.DemiBold } } }
            Text { visible: card.kind !== ""; text: card.kind; color: win.accent; font.family: win.sans; font.pixelSize: 13; font.weight: Font.DemiBold }
            Row { width: parent.width; spacing: 8
                  Text { width: Math.min(implicitWidth, parent.width - (pl.visible ? pl.width + 8 : 0)); wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight; text: card.title; color: card.dim ? win.dim : win.ink; font.family: win.sans; font.pixelSize: 17; font.weight: card.dim ? Font.Medium : Font.DemiBold }
                  Rectangle { id: pl; visible: card.pill !== ""; y: 3; width: pt.implicitWidth + 15; height: 18; radius: 9; color: win.accent
                              Text { id: pt; anchors.centerIn: parent; text: card.pill; color: "#ffffff"; font.family: win.sans; font.pixelSize: 12; font.weight: Font.DemiBold } } }
            Text { visible: card.text1 !== ""; width: parent.width; wrapMode: Text.WordWrap; maximumLineCount: card.text1Lines; elide: Text.ElideRight; text: card.text1; color: win.dim; font.family: win.sans; font.pixelSize: 15; lineHeight: 1.12 }
            Text { visible: card.text2 !== ""; width: parent.width; wrapMode: Text.WordWrap; maximumLineCount: card.text2Lines; elide: Text.ElideRight; text: card.text2; color: card.text2Color; font.family: win.sans; font.pixelSize: 13 }
        }
        Text { id: sd; visible: card.side !== ""; anchors.right: parent.right; anchors.rightMargin: 16; y: 15; text: card.side; color: win.faint; font.family: win.sans; font.pixelSize: 13 }
        Act { id: ab; visible: card.act !== ""; anchors.right: parent.right; anchors.rightMargin: 16; y: 14; text: card.act; primary: !card.actLink; link: card.actLink; ok: card.actOk; onClicked: card.acted() }
    }
    component Act: Rectangle {
        id: act
        property string text: ""
        property bool primary: false
        property bool link: false
        property bool ok: true
        property string tip: ""
        signal clicked()
        width: link ? lt.implicitWidth : lt.implicitWidth + 36
        height: link ? lt.implicitHeight : 34
        radius: 7
        color: link ? "transparent" : primary ? win.accent : win.pane
        border.width: link || primary ? 0 : 1
        border.color: win.edge
        opacity: ok ? 1 : 0.45
        Text { id: lt; anchors.centerIn: parent; text: act.text; color: act.link ? win.accent : act.primary ? "#ffffff" : win.ink; font.family: win.sans; font.pixelSize: 14; font.weight: act.link ? Font.Normal : Font.Medium }
        MouseArea { id: am; anchors.fill: parent; hoverEnabled: true; cursorShape: act.ok ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: if (act.ok) act.clicked() }
        ToolTip.visible: act.tip !== "" && am.containsMouse
        ToolTip.text: act.tip
    }
    component Sec: Text { color: win.faintest; font.family: win.sans; font.pixelSize: 12; font.weight: Font.DemiBold; font.letterSpacing: 0.7; topPadding: 4 }
    component Quiet: Text { width: parent ? parent.width : 300; wrapMode: Text.WordWrap; color: win.faint; font.family: win.sans; font.pixelSize: 14; topPadding: 6 }
    component Facts: Column {
        id: fx
        property string title: ""
        property var rows: []
        property real meter: -1
        spacing: 11
        Sec { text: fx.title; topPadding: 8; bottomPadding: 3 }
        Repeater {
            model: fx.rows
            delegate: Item {
                required property var modelData
                readonly property bool bar: modelData[0] === "Storage (C:)" && fx.meter >= 0
                width: fx.width; height: vl.y + vl.implicitHeight
                Text { text: modelData[0]; color: win.faint; font.family: win.sans; font.pixelSize: 14 }
                Rectangle { visible: parent.bar; x: 99; y: 3; width: parent.width - 99; height: 10; radius: 5; color: win.soft2
                            Rectangle { width: parent.width * Math.max(0, fx.meter) / 100; height: 10; radius: 5; color: fx.meter >= 90 ? win.bad : Qt.rgba(36 / 255, 89 / 255, 214 / 255, 0.8) } }
                Text { id: vl; x: 99; y: parent.bar ? 19 : 0; width: parent.width - 99; text: modelData[1]; color: win.ink; wrapMode: Text.WrapAnywhere; font.family: modelData[2] ? "IBM Plex Mono" : win.sans; font.pixelSize: modelData[2] ? 13 : 14; font.weight: Font.Medium }
            }
        }
    }
}
