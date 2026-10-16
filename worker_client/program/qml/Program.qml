import QtQuick
import QtQuick.Controls
import QtQuick.Window
import "../../windows/qml" as W

// THE FALCON PROGRAM ON A WORKER'S MACHINE. One small window: Today, Tasks, Announcements, My machine. Plain words, calm, its own look -- not the console's.
// Good news is grey (nothing here is green); the accent is for the one thing you can do. It shows what the Worker service on this machine knows, and
// says when that is not live.
Window {
    id: win
    objectName: "program"
    title: "Falcon"
    width: 540
    height: 640
    minimumWidth: 420
    minimumHeight: 460
    visible: false
    color: ground

    readonly property color pane: "#ffffff"
    readonly property color ground: "#f5f6f8"
    readonly property color line: "#eceef1"
    readonly property color edge: "#d9d9d9"
    readonly property color ink: Qt.rgba(0, 0, 0, 0.88)
    readonly property color dim: Qt.rgba(0, 0, 0, 0.55)
    readonly property color faint: Qt.rgba(0, 0, 0, 0.35)
    readonly property color accent: "#1677ff"
    readonly property color warn: "#ad6800"
    readonly property color warnSoft: "#fffbe6"
    readonly property color bad: "#cf1322"
    readonly property string sans: Qt.platform.os === "windows" ? "Segoe UI" : Qt.platform.os === "osx" ? "Helvetica Neue" : "DejaVu Sans"

    property string tab: startTab || "today"
    readonly property var view: program.view || ({})
    readonly property var tasks: view.tasks || []
    readonly property var notes: (view.announcements || [])
    readonly property var admins: view.admins || []
    readonly property int waiting: tasks.filter(function (t) { return !t.started }).length
    readonly property int fresh: notes.filter(function (a) { return a.id > program.seenAlert }).length
    property string askedNote: ""

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
    onTabChanged: if (tab === "announcements") program.markAnnouncementsSeen()
    onVisibleChanged: if (visible && tab === "announcements") program.markAnnouncementsSeen()
    onClosing: function (close) { close.accepted = false; win.hide() }
    Component.onCompleted: if (previewOnly && tab === "announcements") program.markAnnouncementsSeen()

    Column {
        anchors.fill: parent
        spacing: 0

        // --- header: who it is, and whether this is live ---------------------------------------------------------------------------------------
        Rectangle {
            width: parent.width; height: 64; color: win.pane
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: win.line }
            Row {
                x: 20; anchors.verticalCenter: parent.verticalCenter; spacing: 12
                Rectangle { width: 30; height: 30; radius: 7; color: win.accent
                            Text { anchors.centerIn: parent; text: "F"; color: "#ffffff"; font.family: win.sans; font.pixelSize: 17; font.bold: true } }
                Column { anchors.verticalCenter: parent.verticalCenter; spacing: 1
                         Text { text: "Falcon"; color: win.ink; font.family: win.sans; font.pixelSize: 16; font.bold: true }
                         Text { objectName: "programState"; font.family: win.sans; font.pixelSize: 12; color: win.view.connected === false || program.away ? win.warn : win.dim
                                text: program.away ? "Not reaching this machine's Falcon service. Showing what was last known."
                                    : win.view.connected === false ? "Not connected. Showing what was known " + (win.view.as_of ? win.ago(win.view.as_of) : "earlier") + "."
                                    : "Connected" } }
            }
        }

        // --- tabs -------------------------------------------------------------------------------------------------------------------------------
        Rectangle {
            width: parent.width; height: 44; color: win.pane
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: win.line }
            Row {
                x: 12; height: parent.height; spacing: 4
                Repeater {
                    model: [{ id: "today", label: "Today", n: 0 }, { id: "tasks", label: "Tasks", n: win.waiting },
                            { id: "announcements", label: "Announcements", n: win.fresh }, { id: "machine", label: "My machine", n: 0 }]
                    delegate: Item {
                        required property var modelData
                        width: lbl.implicitWidth + (cnt.visible ? cnt.width + 6 : 0) + 24; height: 44
                        Text { id: lbl; x: 12; anchors.verticalCenter: parent.verticalCenter; text: modelData.label
                               color: win.tab === modelData.id ? win.ink : win.dim; font.family: win.sans; font.pixelSize: 14; font.bold: win.tab === modelData.id }
                        Rectangle { id: cnt; visible: modelData.n > 0; anchors.verticalCenter: parent.verticalCenter; x: lbl.x + lbl.implicitWidth + 6
                                    width: Math.max(18, cl.implicitWidth + 10); height: 18; radius: 9; color: win.accent
                                    Text { id: cl; anchors.centerIn: parent; text: modelData.n; color: "#ffffff"; font.family: win.sans; font.pixelSize: 11; font.bold: true } }
                        Rectangle { visible: win.tab === modelData.id; anchors.bottom: parent.bottom; x: 12; width: parent.width - 24; height: 2; color: win.accent }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: win.tab = modelData.id; objectName: "tab_" + modelData.id }
                    }
                }
            }
        }

        // --- the page ---------------------------------------------------------------------------------------------------------------------------
        Flickable {
            id: page
            width: parent.width
            height: parent.height - 64 - 44
            contentWidth: width
            contentHeight: body.height + 40
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: page.contentHeight > page.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff }

            Column {
                id: body
                x: 20; y: 20
                width: page.width - 40
                spacing: 12

                // TODAY
                Column {
                    visible: win.tab === "today"; width: parent.width; spacing: 12
                    Card {
                        visible: !!win.view.held_by
                        Row { spacing: 10
                              W.Glyph { name: "shield"; size: 18; color: win.dim; anchors.verticalCenter: parent.verticalCenter }
                              Text { text: win.view.held_by + " is using this machine. You can use it again when they leave."; color: win.ink
                                     font.family: win.sans; font.pixelSize: 14; wrapMode: Text.WordWrap; width: body.width - 80; anchors.verticalCenter: parent.verticalCenter } }
                    }
                    Card {
                        visible: win.waiting > 0
                        objectName: "todayTasks"
                        Column { spacing: 6; width: parent.width
                                 Text { text: win.waiting === 1 ? "One task is waiting for you to start" : win.waiting + " tasks are waiting for you to start"; color: win.ink
                                        font.family: win.sans; font.pixelSize: 15; font.bold: true }
                                 Text { property var next: win.tasks.filter(function (t) { return !t.started })[0]
                                        visible: !!next; width: parent.width; wrapMode: Text.WordWrap; color: win.dim; font.family: win.sans; font.pixelSize: 13
                                        text: next ? next.title + (next.due ? " · due " + win.when(next.due) : "") : "" }
                                 Link2 { text: "See your tasks"; onClicked: win.tab = "tasks" } }
                    }
                    Card {
                        visible: win.fresh > 0
                        objectName: "todayNotes"
                        Column { spacing: 6; width: parent.width
                                 Text { text: win.fresh === 1 ? "One new announcement" : win.fresh + " new announcements"; color: win.ink; font.family: win.sans; font.pixelSize: 15; font.bold: true }
                                 Text { property var latest: win.notes.filter(function (a) { return a.id > program.seenAlert })[0]
                                        visible: !!latest; width: parent.width; wrapMode: Text.WordWrap; color: win.dim; font.family: win.sans; font.pixelSize: 13
                                        text: latest ? (latest.title || latest.body.slice(0, 90)) : "" }
                                 Link2 { text: "Read it"; onClicked: win.tab = "announcements" } }
                    }
                    Card {
                        visible: win.waiting === 0 && win.fresh === 0 && !win.view.held_by
                        Text { text: "Nothing needs you right now."; color: win.dim; font.family: win.sans; font.pixelSize: 14 }
                    }
                }

                // TASKS
                Column {
                    visible: win.tab === "tasks"; width: parent.width; spacing: 12
                    Card { visible: win.tasks.length === 0; Text { text: "Nothing is assigned to you right now."; color: win.dim; font.family: win.sans; font.pixelSize: 14 } }
                    Repeater {
                        model: win.tasks
                        delegate: Card {
                            required property var modelData
                            objectName: "task_" + modelData.id
                            Column { width: parent.width; spacing: 6
                                     Text { width: parent.width; wrapMode: Text.WordWrap; text: modelData.title; color: win.ink; font.family: win.sans; font.pixelSize: 15; font.bold: true }
                                     Text { width: parent.width; wrapMode: Text.WordWrap; visible: text !== ""; color: win.dim; font.family: win.sans; font.pixelSize: 13
                                            text: modelData.description && modelData.description !== modelData.title ? modelData.description : "" }
                                     Row { spacing: 10
                                           Text { text: "From " + modelData.from + (modelData.due ? " · due " + win.when(modelData.due) : " · no deadline"); color: win.dim
                                                  font.family: win.sans; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } }
                                     Item { width: parent.width; height: 34
                                            Text { anchors.verticalCenter: parent.verticalCenter; color: win.faint; font.family: win.sans; font.pixelSize: 12
                                                   text: modelData.started ? "Started" : "Your Admin closes it when the work is checked." }
                                            Rectangle { visible: !modelData.started; anchors.right: parent.right; width: 90; height: 32; radius: 6; color: win.accent
                                                        Text { anchors.centerIn: parent; text: "Start"; color: "#ffffff"; font.family: win.sans; font.pixelSize: 13; font.bold: true }
                                                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; objectName: "start_" + modelData.id; onClicked: program.startTask(modelData.id) } } } }
                        }
                    }
                }

                // ANNOUNCEMENTS
                Column {
                    visible: win.tab === "announcements"; width: parent.width; spacing: 12
                    Card { visible: win.notes.length === 0; Text { text: "No announcements yet."; color: win.dim; font.family: win.sans; font.pixelSize: 14 } }
                    Repeater {
                        model: win.notes
                        delegate: Card {
                            required property var modelData
                            objectName: "note_" + modelData.id
                            edgeColor: modelData.kind === "emergency" ? win.bad : win.line
                            Column { width: parent.width; spacing: 6
                                     Row { spacing: 8
                                           W.Glyph { visible: modelData.kind !== "announcement"; name: "warn"; size: 15; color: modelData.kind === "emergency" ? win.bad : win.warn; anchors.verticalCenter: parent.verticalCenter }
                                           Text { text: modelData.kind === "emergency" ? "Emergency" : modelData.kind === "warning" ? "Warning" : "Announcement"
                                                  color: modelData.kind === "emergency" ? win.bad : modelData.kind === "warning" ? win.warn : win.dim; font.family: win.sans; font.pixelSize: 12; font.bold: true
                                                  anchors.verticalCenter: parent.verticalCenter }
                                           Text { text: (modelData.from ? "from " + modelData.from + " · " : "") + win.ago(modelData.at); color: win.faint; font.family: win.sans; font.pixelSize: 12
                                                  anchors.verticalCenter: parent.verticalCenter } }
                                     Text { visible: !!modelData.title; width: parent.width; wrapMode: Text.WordWrap; text: modelData.title; color: win.ink; font.family: win.sans; font.pixelSize: 15; font.bold: true }
                                     Text { width: parent.width; wrapMode: Text.WordWrap; text: modelData.body; color: win.ink; font.family: win.sans; font.pixelSize: 14 } }
                        }
                    }
                }

                // MY MACHINE
                Column {
                    visible: win.tab === "machine"; width: parent.width; spacing: 12
                    Card {
                        Column { width: parent.width; spacing: 8
                                 Text { text: win.admins.length === 1 ? "Your Admin" : "Your Admins"; color: win.dim; font.family: win.sans; font.pixelSize: 12; font.bold: true }
                                 Text { visible: win.admins.length === 0; text: "There is no Admin to ask yet."; color: win.dim; font.family: win.sans; font.pixelSize: 14 }
                                 Repeater {
                                     model: win.admins
                                     delegate: Item {
                                         required property var modelData
                                         width: parent.width; height: 40
                                         Row { spacing: 10; anchors.verticalCenter: parent.verticalCenter
                                               W.Glyph { name: "user"; size: 18; color: win.dim; anchors.verticalCenter: parent.verticalCenter }
                                               Text { text: modelData.name; color: win.ink; font.family: win.sans; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter } }
                                         Rectangle { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: 130; height: 30; radius: 6; color: win.pane
                                                     border.width: 1; border.color: win.edge
                                                     Text { anchors.centerIn: parent; text: "Ask for help"; color: win.ink; font.family: win.sans; font.pixelSize: 13 }
                                                     MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; objectName: "ask_" + modelData.account_id
                                                                 onClicked: { program.ask(modelData.account_id, modelData.name); win.askedNote = "Asked " + modelData.name + ". They will write to you when they can." } } }
                                     }
                                 }
                                 Text { visible: win.askedNote !== ""; width: parent.width; wrapMode: Text.WordWrap; text: win.askedNote; color: win.dim; font.family: win.sans; font.pixelSize: 13 } }
                    }
                    Card {
                        Column { width: parent.width; spacing: 6
                                 Text { text: "This machine"; color: win.dim; font.family: win.sans; font.pixelSize: 12; font.bold: true }
                                 Text { text: "Falcon " + (win.view.version || ""); color: win.ink; font.family: win.sans; font.pixelSize: 14; visible: !!win.view.version }
                                 Text { text: program.away ? "Not reaching the Falcon service on this machine." : win.view.connected === false ? "Not connected to your organisation right now." : "Connected to your organisation."
                                        color: win.dim; font.family: win.sans; font.pixelSize: 13 } }
                    }
                }
            }
        }
    }

    // a quiet note in the corner for something new; it goes by itself and never takes the keyboard
    Connections {
        target: program
        function onToastArrived(t) { toasts.push(t); toastWin.next() }
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
            x: 8; y: 8; width: parent.width - 16; height: tcol.height + 28; radius: 8; color: win.pane; border.width: 1; border.color: win.edge
            Column { id: tcol; x: 14; y: 14; width: parent.width - 28; spacing: 3
                     Text { text: toastWin.cur ? (toastWin.cur.kind === "task" ? "A task is waiting" : "New from your Admin") : ""; color: win.dim; font.family: win.sans; font.pixelSize: 12 }
                     Text { width: parent.width; wrapMode: Text.WordWrap; text: toastWin.cur ? toastWin.cur.title : ""; color: win.ink; font.family: win.sans; font.pixelSize: 14; font.bold: true }
                     Text { width: parent.width; wrapMode: Text.WordWrap; visible: text !== ""; text: toastWin.cur ? toastWin.cur.text : ""; color: win.dim; font.family: win.sans; font.pixelSize: 12 } }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: { win.tab = toastWin.cur && toastWin.cur.kind === "task" ? "tasks" : "announcements"; hide.triggered(); win.show(); win.raise() } }
        }
    }

    component Card: Rectangle {
        id: card
        default property alias content: inner.data
        property color edgeColor: win.line
        width: parent ? parent.width : 400
        height: inner.height + 32
        radius: 8
        color: win.pane
        border.width: 1
        border.color: card.edgeColor
        Item { id: inner; x: 16; y: 16; width: parent.width - 32; height: childrenRect.height }
    }
    component Link2: Text {
        signal clicked()
        color: win.accent; font.family: win.sans; font.pixelSize: 13
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: parent.clicked() }
    }
}
