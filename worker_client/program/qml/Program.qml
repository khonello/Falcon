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
    height: 660
    minimumWidth: 860
    minimumHeight: 560
    visible: false
    color: ground
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
    property string tab: startTab || "today"
    readonly property var view: program.view || ({})
    readonly property bool live: !program.away && view.connected !== false
    readonly property var tasks: view.tasks || []
    readonly property var notes: view.announcements || []
    readonly property var chats: view.messages || []
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
        return m < 1 ? "just now" : m < 60 ? m + " min ago" : m < 1440 ? Math.round(m / 60) + " h ago" : Qt.formatDateTime(new Date(iso), "d MMM")
    }
    function kindWord(k) { return k === "emergency" ? "Emergency" : k === "warning" ? "Warning" : "Announcement" }
    function kindColor(k) { return k === "emergency" ? bad : k === "warning" ? warn : dim }
    function details() {
        var m = mach, s = m.storage || {}
        return ["Name: " + (m.name || ""), "IP address: " + (m.address || "unknown"), "Windows: " + (m.windows || ""), "Falcon: " + (m.falcon || view.version || ""),
                "Signed in as: " + (m.account || "nobody"), "Signed in: " + (m.signed_in_at ? when(m.signed_in_at) : "unknown"),
                "Last restart: " + (m.restarted_at ? when(m.restarted_at) : "unknown"), "Storage: " + (s.free_gb !== undefined ? s.free_gb + " GB free of " + s.total_gb + " GB" : "unknown"),
                "Connection: " + (live ? "connected" : "not connected")].join("\n")
    }
    onTabChanged: if (tab === "announcements") program.markAnnouncementsSeen()
    onVisibleChanged: if (visible && tab === "announcements") program.markAnnouncementsSeen()
    onClosing: function (close) { close.accepted = false; win.hide() }
    Component.onCompleted: if (previewOnly && tab === "announcements") program.markAnnouncementsSeen()

    Column {
        anchors.fill: parent
        spacing: 0

        // --- header: Falcon, whether this is live, today -------------------------------------------------------------------------------
        Rectangle {
            width: parent.width; height: 62; color: win.pane
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: win.line }
            Row {
                x: 22; anchors.verticalCenter: parent.verticalCenter; spacing: 12
                Rectangle { width: 30; height: 30; radius: 7; color: win.accent
                            Text { anchors.centerIn: parent; text: "F"; color: "#ffffff"; font.family: win.sans; font.pixelSize: 16; font.weight: Font.DemiBold } }
                Column { anchors.verticalCenter: parent.verticalCenter; spacing: 1
                         Text { text: "Falcon"; color: win.ink; font.family: win.sans; font.pixelSize: 15; font.weight: Font.DemiBold }
                         Text { objectName: "programState"; font.family: win.sans; font.pixelSize: 12; color: win.live ? win.faint : win.warn
                                text: program.away ? "Not reaching this machine's Falcon service. Showing what was last known."
                                    : win.view.connected === false ? "Not connected. Showing what was known " + (win.view.as_of ? win.ago(win.view.as_of) : "earlier") + "."
                                    : "Connected" } }
            }
            Text { anchors.right: parent.right; anchors.rightMargin: 22; anchors.verticalCenter: parent.verticalCenter; text: Qt.formatDate(new Date(), "dddd d MMM")
                   color: win.faint; font.family: win.sans; font.pixelSize: 12 }
        }

        // --- tabs: Today gathers what needs you; each other tab holds that whole list ------------------------------------------------------
        Rectangle {
            width: parent.width; height: 44; color: win.pane
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: win.line }
            Row {
                x: 14; height: parent.height; spacing: 4
                Repeater {
                    model: [{ id: "today", label: "Today", n: 0 }, { id: "tasks", label: "Tasks", n: win.toStart.length }, { id: "messages", label: "Messages", n: win.unread },
                            { id: "announcements", label: "Announcements", n: win.fresh }, { id: "machine", label: "My machine", n: 0 }]
                    delegate: Item {
                        required property var modelData
                        width: lbl.implicitWidth + (cnt.visible ? cnt.width + 6 : 0) + 24; height: 44
                        Text { id: lbl; x: 12; anchors.verticalCenter: parent.verticalCenter; text: modelData.label
                               color: win.tab === modelData.id ? win.ink : win.faint; font.family: win.sans; font.pixelSize: 14; font.weight: win.tab === modelData.id ? Font.DemiBold : Font.Normal }
                        Rectangle { id: cnt; visible: modelData.n > 0 && win.tab !== modelData.id; anchors.verticalCenter: parent.verticalCenter; x: lbl.x + lbl.implicitWidth + 6
                                    width: Math.max(18, cl.implicitWidth + 10); height: 18; radius: 9; color: win.accent
                                    Text { id: cl; anchors.centerIn: parent; text: modelData.n; color: "#ffffff"; font.family: win.sans; font.pixelSize: 11; font.weight: Font.DemiBold } }
                        Rectangle { visible: win.tab === modelData.id; anchors.bottom: parent.bottom; x: 12; width: parent.width - 24; height: 2; color: win.accent }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: win.tab = modelData.id; objectName: "tab_" + modelData.id }
                    }
                }
            }
        }

        // --- the page ---------------------------------------------------------------------------------------------------------------------
        Item {
            id: page
            width: parent.width
            height: parent.height - 62 - 44
            readonly property real pad: 20

            // TODAY: three columns side by side, most urgent first, and one quiet line about this machine at the foot
            Item {
                visible: win.tab === "today"
                anchors.fill: parent; anchors.margins: page.pad
                Row {
                    id: cols
                    width: parent.width; height: parent.height - foot.height - 12
                    spacing: 16
                    readonly property real cw: (width - 32) / 3
                    Column {
                        objectName: "todayTasks"
                        width: cols.cw; spacing: 8
                        ColHead { title: "Your tasks"; n: win.toStart.length ? win.toStart.length + " to start" : ""; onAll: win.tab = "tasks" }
                        Repeater {
                            model: win.toStart.slice(0, 2).concat(win.started.slice(0, 1))
                            delegate: Card {
                                required property var modelData
                                dim: modelData.started
                                title: modelData.title
                                text1: "From " + modelData.from + (modelData.started ? " · started" : "")
                                text2: modelData.due ? "Due " + win.when(modelData.due) : "No deadline"
                                text2Color: modelData.due && !modelData.started ? win.warn : win.faint
                                act: modelData.started ? "" : "Start"
                                actOk: win.live
                                onActed: program.startTask(modelData.id)
                                onPicked: { win.pickTask = modelData.id; win.tab = "tasks" }
                            }
                        }
                        Text { visible: !win.live && win.toStart.length > 0; width: parent.width; wrapMode: Text.WordWrap; text: "Start waits until you are connected again."; color: win.warn; font.family: win.sans; font.pixelSize: 12 }
                        Quiet { visible: win.tasks.length === 0; text: "Nothing is assigned to you right now." }
                    }
                    Column {
                        objectName: "todayMessages"
                        width: cols.cw; spacing: 8
                        ColHead { title: "Messages"; n: win.unread ? win.unread + " new" : ""; onAll: win.tab = "messages" }
                        Repeater {
                            model: win.chats.slice(0, 3)
                            delegate: Card {
                                required property var modelData
                                dim: !modelData.unread
                                title: modelData.with
                                text1: modelData.last
                                text2: win.ago(modelData.at) + (modelData.unread ? "" : " · read")
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
                        width: cols.cw; spacing: 8
                        ColHead { title: "Announcements"; n: win.fresh ? win.fresh + " new" : ""; onAll: win.tab = "announcements" }
                        Repeater {
                            model: win.notes.slice(0, 3)
                            delegate: Card {
                                required property var modelData
                                dim: modelData.id <= program.seenAlert
                                title: modelData.title || modelData.body.slice(0, 60)
                                text1: modelData.title ? modelData.body : ""
                                text2: (modelData.from ? modelData.from + " · " : "") + win.ago(modelData.at)
                                edgeColor: modelData.kind === "emergency" ? win.bad : win.line
                                onPicked: { win.pickNote = modelData.id; win.tab = "announcements" }
                            }
                        }
                        Quiet { visible: win.notes.length === 0; text: "No announcements yet." }
                    }
                }
                Rectangle {
                    id: foot
                    anchors.bottom: parent.bottom
                    width: parent.width; height: 34; color: "transparent"
                    Rectangle { width: parent.width; height: 1; color: win.line }
                    Row { y: 12; spacing: 24
                        Text { text: (win.mach.name || "") ; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                        Text { text: "Falcon " + (win.mach.falcon || win.view.version || ""); color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                        Text { text: win.view.held_by ? win.view.held_by + " is using this machine" : "Nobody else is using this machine"; color: win.faint; font.family: win.sans; font.pixelSize: 12 } }
                }
            }

            // TASKS: every task, picked on the left; the picked one as its window showed it, with Start
            Row {
                visible: win.tab === "tasks"
                anchors.fill: parent; anchors.margins: page.pad
                spacing: 16
                Flickable {
                    width: (parent.width - 16) * 0.44; height: parent.height
                    contentHeight: tl.height; clip: true; boundsBehavior: Flickable.StopAtBounds
                    Column {
                        id: tl
                        width: parent.width; spacing: 8
                        Sec { visible: win.toStart.length > 0; text: "TO START" }
                        Repeater { model: win.toStart
                            delegate: Card { required property var modelData; objectName: "task_" + modelData.id; sel: win.curTask && win.curTask.id === modelData.id
                                title: modelData.title; text1: "From " + modelData.from; text2: modelData.due ? "Due " + win.when(modelData.due) : "No deadline"; text2Color: modelData.due ? win.warn : win.faint
                                onPicked: win.pickTask = modelData.id } }
                        Sec { visible: win.started.length > 0; text: "STARTED" }
                        Repeater { model: win.started
                            delegate: Card { required property var modelData; sel: win.curTask && win.curTask.id === modelData.id
                                title: modelData.title; text1: "From " + modelData.from + " · started"; text2: modelData.due ? "Due " + win.when(modelData.due) : "No deadline"
                                onPicked: win.pickTask = modelData.id } }
                        Quiet { visible: win.tasks.length === 0; text: "Nothing is assigned to you right now." }
                    }
                }
                Rectangle {
                    width: (parent.width - 16) * 0.56; height: Math.min(parent.height, td.height + 40)
                    radius: 10; color: win.pane; border.width: 1; border.color: win.line
                    visible: win.curTask !== null
                    Column {
                        id: td
                        x: 20; y: 20; width: parent.width - 40; spacing: 10
                        Text { text: win.curTask ? "A task from " + win.curTask.from : ""; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                        Text { width: parent.width; wrapMode: Text.WordWrap; text: win.curTask ? win.curTask.title : ""; color: win.ink; font.family: win.sans; font.pixelSize: 20; font.weight: Font.DemiBold }
                        Text { width: parent.width; wrapMode: Text.WordWrap; visible: text !== ""; color: win.dim; font.family: win.sans; font.pixelSize: 14; lineHeight: 1.2
                               text: win.curTask && win.curTask.description && win.curTask.description !== win.curTask.title ? win.curTask.description : "" }
                        Text { text: win.curTask ? (win.curTask.due ? "Due " + win.when(win.curTask.due) : "No deadline") : ""; color: win.curTask && win.curTask.due ? win.warn : win.faint
                               font.family: win.sans; font.pixelSize: 14; font.weight: Font.DemiBold }
                        Text { width: parent.width; wrapMode: Text.WordWrap; text: "Falcon notices the work by itself. You do not have to report anything."; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                        Rectangle { width: parent.width; height: 1; color: win.line }
                        Item { width: parent.width; height: 34
                            Text { anchors.verticalCenter: parent.verticalCenter; width: parent.width - 120; wrapMode: Text.WordWrap; color: win.faint; font.family: win.sans; font.pixelSize: 12
                                   text: win.curTask ? (win.curTask.started ? "Started. " : "") + "An IT Admin checks the work and closes the task." : "" }
                            Act { anchors.right: parent.right; visible: win.curTask && !win.curTask.started; text: "Start"; primary: true; ok: win.live; objectName: "start_task"
                                  onClicked: program.startTask(win.curTask.id) } }
                        Text { visible: !win.live && win.curTask && !win.curTask.started; text: "Start waits until you are connected again."; color: win.warn; font.family: win.sans; font.pixelSize: 12 }
                    }
                }
            }

            // MESSAGES: one conversation per Admin who wrote; the person replies, and asks IT to start one
            Row {
                visible: win.tab === "messages"
                anchors.fill: parent; anchors.margins: page.pad
                spacing: 16
                Column {
                    width: (parent.width - 16) * 0.4; spacing: 8
                    Item { width: parent.width; height: 32
                        Text { anchors.verticalCenter: parent.verticalCenter; text: "Conversations"; color: win.ink; font.family: win.sans; font.pixelSize: 14; font.weight: Font.DemiBold }
                        Act { objectName: "askIT"; anchors.right: parent.right; text: "Ask IT"; primary: win.asking; ok: win.live && !win.myRequest; tip: win.myRequest ? "One request at a time" : !win.live ? "Asking waits until you are connected again" : ""
                              onClicked: win.asking = true } }
                    Rectangle {
                        objectName: "myRequest"
                        visible: !!win.myRequest
                        width: parent.width; height: rq.height + 24; radius: 10; color: win.accentSoft; border.width: 1; border.color: win.line
                        Column { id: rq; x: 14; y: 12; width: parent.width - 28; spacing: 3
                            Text { text: "Your request · waiting for IT"; color: win.accent; font.family: win.sans; font.pixelSize: 12; font.weight: Font.DemiBold }
                            Text { width: parent.width; wrapMode: Text.WordWrap; text: win.myRequest ? win.myRequest.line : ""; color: win.ink; font.family: win.sans; font.pixelSize: 13; font.weight: Font.DemiBold }
                            Text { text: win.myRequest ? "Sent at " + Qt.formatDateTime(new Date(win.myRequest.at), "HH:mm") + " · every IT Admin can see it" : ""; color: win.faint; font.family: win.sans; font.pixelSize: 12 } }
                    }
                    Repeater { model: win.chats
                        delegate: Card { required property var modelData; sel: win.curChat && win.curChat.id === modelData.id
                            title: modelData.with + (modelData.unread ? "  ·  " + modelData.unread + " new" : ""); text1: (modelData.from ? modelData.from + ": " : "") + modelData.last; text2: win.ago(modelData.at)
                            onPicked: { win.asking = false; win.pickChat = modelData.id } } }
                    Quiet { visible: win.chats.length === 0 && !win.myRequest; text: "No messages yet. When an IT Admin writes to you, it is here." }
                    Text { visible: !!win.myRequest; width: parent.width; wrapMode: Text.WordWrap; text: "One request at a time: Ask IT comes back once this one is accepted or closed."; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                }
                Rectangle {
                    objectName: "askForm"
                    width: (parent.width - 16) * 0.6; height: parent.height
                    radius: 10; color: win.pane; border.width: 1; border.color: win.line
                    visible: win.asking
                    Column {
                        x: 18; y: 16; width: parent.width - 36; spacing: 10
                        Text { text: "Ask IT"; color: win.ink; font.family: win.sans; font.pixelSize: 18; font.weight: Font.DemiBold }
                        Text { width: parent.width; wrapMode: Text.WordWrap; text: "Say in one line what you need. Every IT Admin sees it, and the conversation opens here when one of them accepts."; color: win.dim; font.family: win.sans; font.pixelSize: 13 }
                        Text { topPadding: 6; text: "What do you need?"; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                        Rectangle { width: parent.width; height: 38; radius: 8; color: win.soft; border.width: 1; border.color: win.edge
                            TextInput { id: askBox; objectName: "askBox"; x: 14; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 28; clip: true; font.family: win.sans; font.pixelSize: 13; color: win.ink
                                        text: win.askLine; onTextEdited: win.askLine = text; onAccepted: askSend.clicked() } }
                    }
                    Item {
                        x: 18; anchors.bottom: parent.bottom; anchors.bottomMargin: 16; width: parent.width - 36; height: 32
                        Text { anchors.verticalCenter: parent.verticalCenter; text: "You can have one request open at a time."; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                        Row { anchors.right: parent.right; spacing: 8
                            Act { text: "Cancel"; onClicked: win.asking = false }
                            Act { id: askSend; objectName: "sendRequest"; text: "Send request"; primary: true; ok: win.live && win.askLine.trim() !== ""
                                  onClicked: { program.talk(win.askLine.trim()); win.sentRequest = { line: win.askLine.trim(), at: new Date().toISOString() }; win.askLine = ""; win.asking = false } } }
                    }
                }
                Rectangle {
                    width: (parent.width - 16) * 0.6; height: parent.height
                    radius: 10; color: win.pane; border.width: 1; border.color: win.line
                    visible: win.curChat !== null && !win.asking
                    Text { x: 18; y: 14; text: win.curChat ? win.curChat.with : ""; color: win.ink; font.family: win.sans; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Flickable {
                        id: th
                        x: 18; y: 46; width: parent.width - 36; height: parent.height - 46 - comp.height - 30
                        contentHeight: msgs.height; clip: true; boundsBehavior: Flickable.StopAtBounds
                        onContentHeightChanged: contentY = Math.max(0, contentHeight - height)
                        Column {
                            id: msgs
                            width: parent.width; spacing: 8
                            Repeater {
                                model: (program.conversation && program.conversation.messages) || []
                                delegate: Item {
                                    required property var modelData
                                    required property int index
                                    readonly property var all: (program.conversation && program.conversation.messages) || []
                                    readonly property bool newDay: index === 0 || win.dayOf(all[index - 1].at) !== win.dayOf(modelData.at)
                                    width: msgs.width; height: bub.y + bub.height
                                    Text { visible: parent.newDay; width: parent.width; horizontalAlignment: Text.AlignHCenter; text: win.dayOf(modelData.at); color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                                    Rectangle {
                                        id: bub
                                        y: parent.newDay ? 24 : 0
                                        x: modelData.mine ? parent.width - width : 0
                                        width: Math.min(parent.width * 0.8, bt.implicitWidth + 24); height: bt.implicitHeight + bs.implicitHeight + 18; radius: 12
                                        color: modelData.mine ? win.accentSoft : win.soft2
                                        Text { id: bt; x: 12; y: 8; width: Math.min(implicitWidth, msgs.width * 0.8 - 24); wrapMode: Text.WordWrap; text: modelData.body + (modelData.file ? "\nFile: " + modelData.file.name : "")
                                               color: win.ink; font.family: win.sans; font.pixelSize: 13 }
                                        Text { id: bs; x: 12; anchors.top: bt.bottom; anchors.topMargin: 2; text: Qt.formatDateTime(new Date(modelData.at), "HH:mm"); color: win.faint; font.family: win.sans; font.pixelSize: 11 }
                                    }
                                }
                            }
                        }
                    }
                    Row {
                        id: comp
                        x: 18; anchors.bottom: parent.bottom; anchors.bottomMargin: 16; width: parent.width - 36; spacing: 8
                        Rectangle {
                            width: parent.width - sendB.width - 8; height: 38; radius: 19; color: win.soft; border.width: 1; border.color: win.edge
                            TextInput { id: ti; objectName: "replyBox"; x: 16; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 32; clip: true
                                        font.family: win.sans; font.pixelSize: 13; color: win.ink; text: win.draft; onTextEdited: win.draft = text
                                        enabled: win.live; onAccepted: if (win.draft.trim()) sendB.clicked() }
                            Text { visible: ti.text === ""; x: 16; anchors.verticalCenter: parent.verticalCenter; color: win.faint; font.family: win.sans; font.pixelSize: 13
                                   text: !win.live ? "Replying waits until you are connected again" : win.curChat ? "Write a reply to " + win.curChat.with : "" }
                        }
                        Act { id: sendB; objectName: "sendReply"; text: "Send"; primary: true; ok: win.live && win.draft.trim() !== ""
                              onClicked: { program.reply(win.curChat.id, win.draft.trim()); win.draft = "" } }
                    }
                }
            }

            // ANNOUNCEMENTS: every one, newest first; the picked one in full
            Row {
                visible: win.tab === "announcements"
                anchors.fill: parent; anchors.margins: page.pad
                spacing: 16
                Flickable {
                    width: (parent.width - 16) * 0.42; height: parent.height
                    contentHeight: al.height; clip: true; boundsBehavior: Flickable.StopAtBounds
                    Column {
                        id: al
                        width: parent.width; spacing: 8
                        Repeater { model: win.notes
                            delegate: Card { required property var modelData; objectName: "note_" + modelData.id; sel: win.curNote && win.curNote.id === modelData.id
                                kind: win.kindWord(modelData.kind); kindColor: win.kindColor(modelData.kind); edgeColor: modelData.kind === "emergency" ? win.bad : win.line
                                title: modelData.title || modelData.body.slice(0, 60); text2: (modelData.from ? modelData.from + " · " : "") + win.ago(modelData.at)
                                onPicked: win.pickNote = modelData.id } }
                        Quiet { visible: win.notes.length === 0; text: "No announcements yet." }
                    }
                }
                Rectangle {
                    width: (parent.width - 16) * 0.58; height: Math.min(parent.height, na.height + 40)
                    radius: 10; color: win.pane; border.width: 1; border.color: win.curNote && win.curNote.kind === "emergency" ? win.bad : win.line
                    visible: win.curNote !== null
                    Column {
                        id: na
                        x: 20; y: 20; width: parent.width - 40; spacing: 10
                        Text { text: win.curNote ? win.kindWord(win.curNote.kind) : ""; color: win.curNote ? win.kindColor(win.curNote.kind) : win.dim; font.family: win.sans; font.pixelSize: 12; font.weight: Font.DemiBold }
                        Text { width: parent.width; wrapMode: Text.WordWrap; visible: text !== ""; text: win.curNote ? win.curNote.title : ""; color: win.ink; font.family: win.sans; font.pixelSize: 20; font.weight: Font.DemiBold }
                        Text { text: win.curNote ? (win.curNote.from ? "From " + win.curNote.from + " · " : "") + win.ago(win.curNote.at) : ""; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                        Text { width: parent.width; wrapMode: Text.WordWrap; text: win.curNote ? win.curNote.body : ""; color: win.ink; font.family: win.sans; font.pixelSize: 14; lineHeight: 1.25 }
                    }
                }
            }

            // MY MACHINE: what IT asks for on the phone, and one click to copy it
            Column {
                visible: win.tab === "machine"
                anchors.fill: parent; anchors.margins: page.pad
                spacing: 16
                Row {
                    width: parent.width; spacing: 16
                    Facts {
                        width: (parent.width - 16) / 2
                        title: "THIS MACHINE"
                        rows: [["Name", win.mach.name || "—"], ["IP address", win.mach.address || "—"], ["Windows", win.mach.windows || "—"], ["Falcon", win.mach.falcon || win.view.version || "—"]]
                    }
                    Facts {
                        width: (parent.width - 16) / 2
                        title: "YOU, TODAY"
                        readonly property var s: win.mach.storage || null
                        rows: [["Signed in as", win.mach.account || "—"], ["Signed in", win.mach.signed_in_at ? win.when(win.mach.signed_in_at) : "—"],
                               ["Last restart", win.mach.restarted_at ? win.when(win.mach.restarted_at) : "—"],
                               ["Storage (C:)", s ? s.free_gb + " GB free of " + s.total_gb + " GB" : "—"],
                               ["Connection", win.live ? "Connected to your organisation" : "Not connected right now"]]
                        meter: s ? s.used_percent : -1
                    }
                }
                Item {
                    width: parent.width; height: 40
                    Rectangle { width: parent.width; height: 1; color: win.line }
                    Text { y: 14; text: (win.view.admins || []).length ? "Your IT Admins: " + win.view.admins.map(function (a) { return a.name }).join(", ") : ""; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                    Act { objectName: "copyDetails"; anchors.right: parent.right; y: 8; text: "Copy these details"; onClicked: { program.copyText(win.details()); copied.visible = true; copiedT.restart() } }
                    Text { id: copied; visible: false; anchors.right: parent.right; anchors.rightMargin: 170; y: 15; text: "Copied"; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
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
        width: 340; height: tcard.height + 16
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
            x: 8; y: 8; width: parent.width - 16; height: tcol.height + 28; radius: 10; color: win.pane; border.width: 1; border.color: win.edge
            Column { id: tcol; x: 14; y: 14; width: parent.width - 28; spacing: 3
                     Text { text: toastWin.cur ? (toastWin.cur.kind === "task" ? "A task is waiting · Falcon" : "New from IT · Falcon") : ""; color: win.faint; font.family: win.sans; font.pixelSize: 12 }
                     Text { width: parent.width; wrapMode: Text.WordWrap; text: toastWin.cur ? toastWin.cur.title : ""; color: win.ink; font.family: win.sans; font.pixelSize: 14; font.weight: Font.DemiBold }
                     Text { width: parent.width; wrapMode: Text.WordWrap; visible: text !== ""; text: toastWin.cur ? toastWin.cur.text : ""; color: win.warn; font.family: win.sans; font.pixelSize: 12 }
                     Text { text: "Open in Falcon"; color: win.accent; font.family: win.sans; font.pixelSize: 12 } }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: { win.tab = toastWin.cur && toastWin.cur.kind === "task" ? "tasks" : toastWin.cur && toastWin.cur.kind === "message" ? "messages" : "announcements"; hide.triggered(); win.show(); win.raise() } }
        }
    }

    // --- the pieces ------------------------------------------------------------------------------------------------------------------------
    component ColHead: Item {
        id: ch
        property string title: ""
        property string n: ""
        signal all()
        width: parent ? parent.width : 300
        height: 28
        Row { anchors.verticalCenter: parent.verticalCenter; spacing: 8
              Text { text: ch.title; color: win.ink; font.family: win.sans; font.pixelSize: 15; font.weight: Font.DemiBold }
              Rectangle { visible: ch.n !== ""; anchors.verticalCenter: parent.verticalCenter; width: nt.implicitWidth + 14; height: 18; radius: 9; color: win.accent
                          Text { id: nt; anchors.centerIn: parent; text: ch.n; color: "#ffffff"; font.family: win.sans; font.pixelSize: 11; font.weight: Font.DemiBold } } }
        Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "All"; color: win.accent; font.family: win.sans; font.pixelSize: 13
               MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: ch.all() } }
    }
    component Card: Rectangle {
        id: card
        property string kind: ""
        property color kindColor: win.dim
        property string title: ""
        property string text1: ""
        property string text2: ""
        property color text2Color: win.faint
        property string act: ""
        property bool actLink: false
        property bool actOk: true
        property bool dim: false
        property bool sel: false
        property color edgeColor: win.line
        signal picked()
        signal acted()
        width: parent ? parent.width : 300
        height: cc.height + 26
        radius: 10
        color: sel ? win.accentSoft : dim ? "transparent" : win.pane
        // a card already seen or started: no fill, a dashed edge (the concept's c-card dim)
        border.width: dim && !sel ? 0 : 1
        border.color: sel ? Qt.rgba(36 / 255, 89 / 255, 214 / 255, 0.45) : card.edgeColor
        Canvas {
            visible: card.dim && !card.sel
            anchors.fill: parent
            onPaint: { var g = getContext("2d"); g.reset(); g.strokeStyle = card.edgeColor; g.lineWidth = 1; g.setLineDash([4, 3])
                       var r = card.radius, x = 0.5, y = 0.5, w = width - 1, h = height - 1
                       g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); g.stroke() }
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
        }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: card.picked() }
        Column {
            id: cc
            x: 14; y: 13; width: parent.width - 28 - (ab.visible ? ab.width + 10 : 0); spacing: 3
            Text { visible: card.kind !== ""; text: card.kind; color: card.kindColor; font.family: win.sans; font.pixelSize: 11; font.weight: Font.DemiBold }
            Text { width: parent.width; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight; text: card.title; color: card.dim ? win.dim : win.ink; font.family: win.sans; font.pixelSize: 14; font.weight: card.dim ? Font.Medium : Font.DemiBold }
            Text { visible: card.text1 !== ""; width: parent.width; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight; text: card.text1; color: win.dim; font.family: win.sans; font.pixelSize: 13 }
            Text { visible: card.text2 !== ""; width: parent.width; text: card.text2; color: card.text2Color; font.family: win.sans; font.pixelSize: 12 }
        }
        Act { id: ab; visible: card.act !== ""; anchors.right: parent.right; anchors.rightMargin: 12; y: 12; text: card.act; primary: !card.actLink; link: card.actLink; ok: card.actOk; onClicked: card.acted() }
    }
    component Act: Rectangle {
        id: act
        property string text: ""
        property bool primary: false
        property bool link: false
        property bool ok: true
        property string tip: ""
        signal clicked()
        width: link ? lt.implicitWidth : lt.implicitWidth + 28
        height: 32
        radius: 7
        color: link ? "transparent" : primary ? win.accent : win.pane
        border.width: link || primary ? 0 : 1
        border.color: win.edge
        opacity: ok ? 1 : 0.45
        Text { id: lt; anchors.centerIn: parent; text: act.text; color: act.link ? win.accent : act.primary ? "#ffffff" : win.ink; font.family: win.sans; font.pixelSize: 13; font.weight: act.primary ? Font.DemiBold : Font.Normal }
        MouseArea { id: am; anchors.fill: parent; hoverEnabled: true; cursorShape: act.ok ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: if (act.ok) act.clicked() }
        ToolTip.visible: act.tip !== "" && am.containsMouse
        ToolTip.text: act.tip
    }
    component Sec: Text { color: win.faintest; font.family: win.sans; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.6; topPadding: 4 }
    component Quiet: Text { width: parent ? parent.width : 300; wrapMode: Text.WordWrap; color: win.faint; font.family: win.sans; font.pixelSize: 13; topPadding: 6 }
    component Facts: Rectangle {
        id: fx
        property string title: ""
        property var rows: []
        property real meter: -1
        height: fc.height + 32
        radius: 10; color: win.pane; border.width: 1; border.color: win.line
        Column {
            id: fc
            x: 16; y: 16; width: parent.width - 32; spacing: 10
            Text { text: fx.title; color: win.faintest; font.family: win.sans; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.6 }
            Repeater {
                model: fx.rows
                delegate: Column {
                    required property var modelData
                    width: fc.width; spacing: 4
                    Row { width: parent.width
                        Text { width: 140; text: modelData[0]; color: win.faint; font.family: win.sans; font.pixelSize: 13 }
                        Text { width: parent.width - 140; text: modelData[1]; color: win.ink; font.family: win.sans; font.pixelSize: 13; wrapMode: Text.WrapAnywhere } }
                    Rectangle { visible: modelData[0] === "Storage (C:)" && fx.meter >= 0; x: 140; width: parent.width - 140; height: 6; radius: 3; color: win.soft2
                                Rectangle { width: parent.width * Math.max(0, fx.meter) / 100; height: 6; radius: 3; color: fx.meter >= 90 ? win.bad : win.accent } }
                }
            }
        }
    }
}
