import QtQuick
import "."

// YOUR TO-DO, WHEN ITS TIME COMES (ENGINE-GAPS #17): one line across the top of the console for the to-do most past its
// date, or due within the hour, from `todo.list`'s strip. Done ticks it off; Not now hides it until it changes or the
// console restarts. Only the Admin who wrote it ever sees it.
Rectangle {
    id: root
    objectName: "todoStrip"
    property var strip: []
    property var snoozed: ({})
    readonly property var cur: {
        var xs = strip.filter(function (t) { return !snoozed[t.id] })
        xs.sort(function (a, b) { return new Date(a.due_at) - new Date(b.due_at) })
        return xs.length ? xs[0] : null
    }
    width: parent ? parent.width : 800
    // the concept's .newtask: 9px 20px around a small button's 24, a hairline under it at a third of the accent, on the
    // accent's soft tint over the page
    height: cur ? 43 : 0
    visible: cur !== null
    color: Theme.bg
    Rectangle { anchors.fill: parent; color: Theme.accentSoft }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.alpha(Theme.accent, 0.35) }
    readonly property var waiting: strip.filter(function (t) { return !snoozed[t.id] })

    function load() {
        if (!falcon.isConnected) return
        falcon.call("todo.list", {}, function (ok, r) { if (ok) root.strip = r.strip || [] })
    }
    Component.onCompleted: load()
    Connections {
        target: falcon
        function onConnected() { root.load() }
        function onPushReceived(type, payload) { if (type === "todo.changed") root.load() }
    }
    Timer { interval: 60000; running: true; repeat: true; onTriggered: root.load() }

    Row {
        x: 20
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        Icon { name: "checksquarefilled"; size: 15; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter }
        Txt { text: !root.cur ? "" : root.cur.overdue ? "Past its date" : Time.sameDay(Time.ms(root.cur.due_at), Time.now) ? "Due today" : "Due tomorrow"; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
        Txt { text: root.cur ? root.cur.text : ""; anchors.verticalCenter: parent.verticalCenter; width: Math.min(implicitWidth, root.width - 600) }
        Txt {
            text: root.cur ? "due " + Time.hhmm(root.cur.due_at) : ""
            mono: true
            color: root.cur && root.cur.overdue ? Theme.crit : Theme.text
            anchors.verticalCenter: parent.verticalCenter
            elide: Text.ElideNone
        }
        Txt {
            visible: root.waiting.length > 1
            text: "and " + Theme.fmt(root.waiting.length - 1) + " more"
            color: Theme.text3
            anchors.verticalCenter: parent.verticalCenter
            elide: Text.ElideNone
        }
    }
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        Btn { objectName: "todoNotNow"; text: "Not now"; small: true; onClicked: { var s = Object.assign({}, root.snoozed); s[root.cur.id] = true; root.snoozed = s } }
        Btn { objectName: "todoDone"; text: "Done"; small: true; kind: "primary"; onClicked: root.done() }
    }
    function done() {
        if (!cur) return
        var t = cur
        falcon.call("todo.done", { todo_id: t.id, done: true }, function (ok, r) {
            if (ok) { Msg.ok("Done · " + t.text); root.load() } else Msg.failed(r.message || "Could not tick it off")
        })
    }
}
