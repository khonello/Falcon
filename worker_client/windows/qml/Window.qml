import QtQuick
import QtQuick.Controls
import QtQuick.Window

// THE WORKER'S WINDOWS. One of five, chosen by `kind`, filled from `spec`; `answer.give(...)` hands the person's
// answer back to the service. Blocked and locked cover the screen (dimmed, topmost) and stay until the service closes
// them; the others are a small card and go when answered.
//
// Plain words throughout: "R. Mensah is using this machine", never "traversal"; "you don't need to do anything".
//
// The palette is the console's (docs/UI.md), written out rather than imported -- the Worker package does not depend on
// the Operator Client. Two consequences of those rules matter here: good news is grey, so nothing on these windows is
// green, and the accent is for the act you can take, never for status.
Window {
    id: win

    readonly property bool covers: kind === "blocked" || kind === "locked"

    readonly property color pane: "#ffffff"
    readonly property color ground: "#fafafa"
    readonly property color line: "#f0f0f0"
    readonly property color edge: "#d9d9d9"
    readonly property color ink: Qt.rgba(0, 0, 0, 0.88)
    readonly property color dim: Qt.rgba(0, 0, 0, 0.45)
    readonly property color faint: Qt.rgba(0, 0, 0, 0.25)
    readonly property color accent: "#1677ff"
    readonly property color warn: "#ad6800"
    readonly property color warnSoft: "#fffbe6"
    readonly property string sans: Qt.platform.os === "windows" ? "Segoe UI"
                                   : Qt.platform.os === "osx" ? "Helvetica Neue" : "DejaVu Sans"

    visible: true
    color: "transparent"
    title: "Falcon"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | (covers ? Qt.WindowDoesNotAcceptFocus : 0)
    width: backdrop ? 1440 : covers ? Screen.width : card.width + 48
    height: backdrop ? 900 : covers ? Screen.height : card.height + 48
    x: backdrop || covers ? 0 : Screen.width - width - 24
    y: backdrop || covers ? 0 : Screen.height - height - 64

    function when(iso) {
        if (!iso) return ""
        var d = new Date(iso), now = new Date()
        var day = d.toDateString() === now.toDateString() ? "today" : Qt.formatDateTime(d, "dddd")
        return day + " at " + Qt.formatDateTime(d, "HH:mm")
    }
    function minutesUntil(iso) { return iso ? Math.max(1, Math.round((new Date(iso) - Date.now()) / 60000)) : 0 }
    // said the way a person says it: "a minute", not "1 minutes"
    function howLong(iso) {
        var n = minutesUntil(iso)
        return n === 1 ? "about a minute" : "about " + n + " minutes"
    }

    // a desktop behind, only for pictures of the window (--shot)
    Rectangle {
        anchors.fill: parent
        visible: backdrop
        gradient: Gradient { orientation: Gradient.Horizontal
                             GradientStop { position: 0; color: "#1E2B3A" }
                             GradientStop { position: 1; color: "#2B4A66" } }
    }
    // what covers the screen: their machine is still there, dimmed, not hidden. This one stays dark, because it is
    // their own desktop being covered -- not a surface of ours.
    Rectangle { anchors.fill: parent; visible: win.covers && !backdrop; color: Qt.rgba(0, 0, 0, 0.55) }

    Rectangle {
        id: card
        width: kind === "task" ? 460 : 360
        height: body.implicitHeight + 44
        anchors.centerIn: win.covers || backdrop ? parent : undefined
        x: 24; y: 24
        radius: 8
        color: win.pane
        border.width: 1
        border.color: win.line

        Column {
            id: body
            x: 22; y: 22
            width: parent.width - 44
            spacing: 10

            // --- someone is using your machine --------------------------------------------------------------
            Column {
                visible: kind === "blocked"
                width: parent.width
                spacing: 10
                Glyph { name: "shield"; size: 22; color: win.dim; anchors.horizontalCenter: parent.horizontalCenter }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: win.ink
                       font.family: win.sans; font.pixelSize: 18; font.bold: true
                       text: (spec.occupant_name || "Your Admin") + " is using this machine" }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: win.dim
                       font.family: win.sans; font.pixelSize: 13
                       text: "You can use it again when they leave" + (spec.deadline_at ? ", " + win.howLong(spec.deadline_at) : "")
                             + ". You don't need to do anything." }
            }

            // --- the screen, locked --------------------------------------------------------------------------
            Column {
                visible: kind === "locked"
                width: parent.width
                spacing: 10
                Glyph { name: "lock"; size: 22; color: win.dim; anchors.horizontalCenter: parent.horizontalCenter }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; color: win.ink
                       font.family: win.sans; font.pixelSize: 18; font.bold: true; text: "Locked by your Admin" }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: win.dim
                       font.family: win.sans; font.pixelSize: 13
                       text: (spec.message ? spec.message + " " : "") + (spec.until ? "It unlocks by itself at " + Qt.formatDateTime(new Date(spec.until), "HH:mm") + "." : "") }
            }

            // --- a message from your Admin -------------------------------------------------------------------
            Column {
                visible: kind === "message"
                width: parent.width
                spacing: 10
                Row {
                    spacing: 8
                    Glyph { name: "bell"; size: 14; color: win.faint; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "From your Admin" + (spec.from ? ", " + spec.from : ""); color: win.dim
                           font.family: win.sans; font.pixelSize: 12 }
                }
                Text { width: parent.width; wrapMode: Text.WordWrap; color: win.ink
                       font.family: win.sans; font.pixelSize: 15; font.bold: true; text: spec.text || "" }
                Item { width: parent.width; height: 32
                       Act { anchors.right: parent.right; text: "OK"; primary: true; onClicked: answer.give({ seen: true }) } }
            }

            // --- asking for help -------------------------------------------------------------------------------
            Column {
                visible: kind === "ask"
                width: parent.width
                spacing: 10
                Row {
                    spacing: 8
                    Glyph { name: "ping"; size: 14; color: win.dim; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: spec.admins && spec.admins.length > 1 ? "Ask for help" : "Ask " + (spec.to || "your Admin") + " for help"
                           color: win.ink; font.family: win.sans; font.pixelSize: 14; font.bold: true }
                }
                // A ping carries no message: it says "I need you". Whoever you ask sees it, answers, and writes first.
                Text { width: parent.width; wrapMode: Text.WordWrap; color: win.dim; font.family: win.sans; font.pixelSize: 13
                       text: "They will see that you need them, and write to you when they can. You do not have to say anything now." }
                Flow {
                    width: parent.width; spacing: 8
                    Repeater {
                        model: spec.admins || []
                        Act { text: (spec.admins.length > 1 ? "Ask " : "Ask ") + modelData.name; primary: spec.admins.length === 1
                              onClicked: answer.give({ to: modelData.account_id }) }
                    }
                }
            }

            // --- a task given to you: Start, never Complete -------------------------------------------------------
            Column {
                visible: kind === "task"
                width: parent.width
                spacing: 10
                Item {
                    width: parent.width; height: 20
                    Row { spacing: 8
                          Glyph { name: "tasks"; size: 15; color: win.faint; anchors.verticalCenter: parent.verticalCenter }
                          Text { text: "A task from " + (spec.from || "your Admin"); color: win.dim
                                 font.family: win.sans; font.pixelSize: 13 } }
                    Glyph { anchors.right: parent.right; name: "x"; size: 14; color: win.faint
                            TapHandler { onTapped: answer.give({ later: true }) } }
                }
                Text { width: parent.width; wrapMode: Text.WordWrap; color: win.ink
                       font.family: win.sans; font.pixelSize: 20; font.bold: true; text: spec.title || "" }
                Text { width: parent.width; wrapMode: Text.WordWrap; color: win.dim
                       font.family: win.sans; font.pixelSize: 13; text: spec.description || "" }
                Rectangle {
                    visible: !!spec.due
                    width: dueRow.implicitWidth + 20; height: 26; radius: 4; color: win.warnSoft
                    border.width: 1; border.color: "#ffe58f"
                    Row { id: dueRow; anchors.centerIn: parent; spacing: 7
                          Glyph { name: "clock"; size: 13; color: win.warn; anchors.verticalCenter: parent.verticalCenter }
                          Text { text: "Due " + win.when(spec.due); color: win.warn
                                 font.family: win.sans; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } }
                }
                Rectangle { width: parent.width; height: 1; color: win.line; visible: (spec.signs || []).length > 0 }
                Text { visible: (spec.signs || []).length > 0; text: "What will show the work is happening"
                       color: win.dim; font.family: win.sans; font.pixelSize: 12 }
                Repeater {
                    model: spec.signs || []
                    delegate: Item {
                        required property var modelData
                        width: parent.width; height: modelData.hint ? 44 : 34
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: win.line }
                        Glyph { id: sg; anchors.verticalCenter: parent.verticalCenter
                                name: modelData.program ? "window" : "file"; size: 14; color: win.faint }
                        Column {
                            anchors.left: sg.right; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter
                            Text { text: modelData.name; color: win.ink; font.family: win.sans; font.pixelSize: 13 }
                            Text { visible: !!modelData.hint; text: modelData.hint || ""; color: win.faint
                                   font.family: win.sans; font.pixelSize: 11 }
                        }
                        // good news is grey: a sign that has been seen is simply stated, never celebrated
                        Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                               font.family: win.sans; font.pixelSize: 12
                               text: modelData.seen ? "changed " + Qt.formatDateTime(new Date(modelData.seen), "HH:mm") : "not yet"
                               color: modelData.seen ? win.dim : win.faint }
                    }
                }
                Item { width: 1; height: 8 }
                Item {
                    width: parent.width; height: 34
                    Text { anchors.verticalCenter: parent.verticalCenter; color: win.faint
                           font.family: win.sans; font.pixelSize: 12
                           text: (spec.from || "Your Admin") + " closes it when the work is checked." }
                    Act { anchors.right: parent.right; visible: !spec.started; text: "Start"; primary: true
                          onClicked: answer.give({ start: true }) }
                    Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: !!spec.started
                           text: "Started"; color: win.dim; font.family: win.sans; font.pixelSize: 13 }
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
        width: actLabel.implicitWidth + (act.text === "Start" ? 44 : 32); height: 32; radius: 6
        opacity: enabled ? 1 : 0.45
        color: primary ? (hov.pressed ? Qt.darker(win.accent, 1.15) : hov.containsMouse ? Qt.lighter(win.accent, 1.12) : win.accent)
                       : hov.containsMouse ? win.ground : win.pane
        border.width: primary ? 0 : 1
        border.color: hov.containsMouse ? win.accent : win.edge
        anchors.verticalCenter: parent ? parent.verticalCenter : undefined
        Row { anchors.centerIn: parent; spacing: 6
              Glyph { visible: act.text === "Start"; name: "play"; size: 12
                      color: act.primary ? "#ffffff" : win.ink; anchors.verticalCenter: parent.verticalCenter }
              Text { id: actLabel; text: act.text; color: act.primary ? "#ffffff" : win.ink
                     font.family: win.sans; font.pixelSize: 13; font.bold: act.primary
                     anchors.verticalCenter: parent.verticalCenter } }
        MouseArea { id: hov; anchors.fill: parent; enabled: act.enabled; hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor; onClicked: act.clicked() }
    }
}
