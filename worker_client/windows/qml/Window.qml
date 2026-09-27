import QtQuick
import QtQuick.Controls
import QtQuick.Window

// THE WORKER'S WINDOWS (boards WR01, TK07). One of five, chosen by `kind`, filled from `spec`; `answer.give(...)`
// hands the person's answer back to the service. Blocked and locked cover the screen (dimmed, topmost) and stay until
// the service closes them; the others are a small card and go when answered.
//
// Plain words throughout: "R. Mensah is using this machine", never "traversal"; "you don't need to do anything".
Window {
    id: win

    readonly property bool covers: kind === "blocked" || kind === "locked"
    // the Operator Client's palette, as tokens (the Worker does not import it)
    readonly property color pane: "#1B2028"
    readonly property color ground: "#12151C"
    readonly property color line: "#2A313C"
    readonly property color ink: "#E8ECF2"
    readonly property color dim: "#A6B0BC"
    readonly property color faint: "#7D8896"
    readonly property color accent: "#8AA6E0"
    readonly property color ok: "#7FB396"
    readonly property color warn: "#D2A468"

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

    // a desktop behind, only for pictures of the window (--shot)
    Rectangle {
        anchors.fill: parent
        visible: backdrop
        gradient: Gradient { orientation: Gradient.Horizontal
                             GradientStop { position: 0; color: "#1E2B3A" }
                             GradientStop { position: 1; color: "#2B4A66" } }
    }
    // what covers the screen: their machine is still there, dimmed, not hidden
    Rectangle { anchors.fill: parent; visible: win.covers && !backdrop; color: Qt.rgba(0.05, 0.06, 0.09, 0.72) }

    Rectangle {
        id: card
        width: kind === "task" ? 460 : kind === "ask" ? 360 : 360
        height: body.implicitHeight + 44
        anchors.centerIn: win.covers || backdrop ? parent : undefined
        x: 24; y: 24
        radius: 16
        color: win.pane
        border.width: win.covers ? 1 : 0
        border.color: "#3B4450"

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
                Glyph { name: "shield"; size: 22; color: win.ink; anchors.horizontalCenter: parent.horizontalCenter }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: win.ink
                       font.pixelSize: 18; font.bold: true; text: (spec.occupant_name || "Your Admin") + " is using this machine" }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: win.dim; font.pixelSize: 13
                       text: "You can use it again when they leave" + (spec.deadline_at ? " — about " + win.minutesUntil(spec.deadline_at) + " minutes" : "")
                             + ". You don't need to do anything." }
            }

            // --- the screen, locked --------------------------------------------------------------------------
            Column {
                visible: kind === "locked"
                width: parent.width
                spacing: 10
                Glyph { name: "lock"; size: 22; color: win.ink; anchors.horizontalCenter: parent.horizontalCenter }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; color: win.ink; font.pixelSize: 18; font.bold: true
                       text: "Locked by your Admin" }
                Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: win.dim; font.pixelSize: 13
                       text: (spec.message ? spec.message + " " : "") + (spec.until ? "It unlocks by itself at " + Qt.formatDateTime(new Date(spec.until), "HH:mm") + "." : "") }
            }

            // --- a message from your Admin -------------------------------------------------------------------
            Column {
                visible: kind === "message"
                width: parent.width
                spacing: 10
                Row {
                    spacing: 8
                    Glyph { name: "bell"; size: 14; color: win.dim; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "From your Admin" + (spec.from ? ", " + spec.from : ""); color: win.dim; font.pixelSize: 12; font.bold: true }
                }
                Text { width: parent.width; wrapMode: Text.WordWrap; color: win.ink; font.pixelSize: 15; font.bold: true; text: spec.text || "" }
                Item { width: parent.width; height: 28
                       Act { anchors.right: parent.right; text: "OK"; flat: true; onClicked: answer.give({ seen: true }) } }
            }

            // --- asking for help -------------------------------------------------------------------------------
            Column {
                visible: kind === "ask"
                width: parent.width
                spacing: 10
                Row {
                    spacing: 8
                    Glyph { name: "ping"; size: 14; color: win.warn; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Ask " + (spec.to || "your Admin") + " for help"; color: win.ink; font.pixelSize: 14; font.bold: true }
                }
                Rectangle {
                    width: parent.width; height: 64; radius: 8; color: win.ground; border.width: 1; border.color: win.line
                    TextEdit { id: askText; anchors.fill: parent; anchors.margins: 10; wrapMode: TextEdit.Wrap; color: win.ink; font.pixelSize: 13
                               text: spec.draft || "" }
                    Text { visible: askText.text === ""; x: 10; y: 10; text: "What do you need?"; color: win.faint; font.pixelSize: 13 }
                }
                Item {
                    width: parent.width; height: 30
                    Text { anchors.verticalCenter: parent.verticalCenter; text: "One message, then wait for their reply."; color: win.faint; font.pixelSize: 11 }
                    Act { anchors.right: parent.right; text: "Send"; enabled: askText.text.trim() !== ""
                             onClicked: answer.give({ message: askText.text.trim() }) }
                }
            }

            // --- a task given to you (TK07): Start, never Complete ----------------------------------------------
            Column {
                visible: kind === "task"
                width: parent.width
                spacing: 10
                Item {
                    width: parent.width; height: 20
                    Row { spacing: 8
                          Glyph { name: "tasks"; size: 15; color: win.dim; anchors.verticalCenter: parent.verticalCenter }
                          Text { text: "A task from " + (spec.from || "your Admin"); color: win.dim; font.pixelSize: 13; font.bold: true } }
                    Glyph { anchors.right: parent.right; name: "x"; size: 14; color: win.faint
                            TapHandler { onTapped: answer.give({ later: true }) } }
                }
                Text { width: parent.width; wrapMode: Text.WordWrap; color: win.ink; font.pixelSize: 20; font.bold: true; text: spec.title || "" }
                Text { width: parent.width; wrapMode: Text.WordWrap; color: win.dim; font.pixelSize: 13; text: spec.description || "" }
                Row {
                    visible: !!spec.due
                    spacing: 7
                    Glyph { name: "clock"; size: 13; color: win.warn; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: "Due " + win.when(spec.due); color: win.warn; font.pixelSize: 13; font.bold: true }
                }
                Rectangle { width: parent.width; height: 1; color: win.line; visible: (spec.signs || []).length > 0 }
                Text { visible: (spec.signs || []).length > 0; text: "What will show the work is happening"; color: win.dim; font.pixelSize: 12; font.bold: true }
                Repeater {
                    model: spec.signs || []
                    delegate: Item {
                        required property var modelData
                        width: parent.width; height: modelData.hint ? 44 : 34
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: win.line }
                        Glyph { id: sg; anchors.verticalCenter: parent.verticalCenter; name: modelData.program ? "window" : "file"; size: 14; color: win.dim }
                        Column {
                            anchors.left: sg.right; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter
                            Text { text: modelData.name; color: win.ink; font.pixelSize: 13 }
                            Text { visible: !!modelData.hint; text: modelData.hint || ""; color: win.faint; font.pixelSize: 11 }
                        }
                        Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 12; font.bold: true
                               text: modelData.seen ? "changed " + Qt.formatDateTime(new Date(modelData.seen), "HH:mm") : "not yet"
                               color: modelData.seen ? win.ok : win.faint }
                    }
                }
                Item { width: 1; height: 8 }
                Item {
                    width: parent.width; height: 34
                    Text { anchors.verticalCenter: parent.verticalCenter; color: win.faint; font.pixelSize: 12
                           text: (spec.from || "Your Admin") + " closes it when the work is checked." }
                    Act { anchors.right: parent.right; visible: !spec.started; text: "Start"; onClicked: answer.give({ start: true }) }
                    Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: !!spec.started
                           text: "Started"; color: win.ok; font.pixelSize: 13; font.bold: true }
                }
            }
        }
    }

    // a quiet button: the act named, on a soft tone
    component Act: Rectangle {
        id: act
        property string text: ""
        property bool flat: false
        signal clicked()
        width: actLabel.implicitWidth + 28; height: 32; radius: 8
        opacity: enabled ? 1 : 0.4
        color: flat ? "transparent" : Qt.rgba(0.541, 0.651, 0.878, 0.16)
        anchors.verticalCenter: parent ? parent.verticalCenter : undefined
        Row { anchors.centerIn: parent; spacing: 6
              Glyph { visible: act.text === "Start"; name: "play"; size: 12; color: win.accent; anchors.verticalCenter: parent.verticalCenter }
              Text { id: actLabel; text: act.text; color: act.flat ? win.dim : win.accent; font.pixelSize: 13; font.bold: true } }
        MouseArea { anchors.fill: parent; enabled: act.enabled; cursorShape: Qt.PointingHandCursor; onClicked: act.clicked() }
    }
}
