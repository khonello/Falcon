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
    height: cur ? 42 : 0
    visible: cur !== null
    color: Theme.mix(Theme.accent, Theme.surface, 0.10)
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.mix(Theme.accent, Theme.border, 0.4) }

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
        Check { checked: false; anchors.verticalCenter: parent.verticalCenter; onToggled: root.done() }
        Txt { text: root.cur && root.cur.overdue ? "Past its date" : "Due soon"; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
        Txt { text: root.cur ? root.cur.text : ""; anchors.verticalCenter: parent.verticalCenter; width: Math.min(implicitWidth, root.width - 520) }
        Txt {
            text: root.cur ? "due " + Time.hhmm(root.cur.due_at) : ""
            mono: true
            color: root.cur && root.cur.overdue ? Theme.crit : Theme.med
            anchors.verticalCenter: parent.verticalCenter
            elide: Text.ElideNone
        }
    }
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8
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
