import QtQuick
import "."

// WHAT NEEDS A PERSON, PER AREA, for the menu -- and the few facts every page shares: how many
// departments there are, and the name of the only one when there is one. Fetched on connect, on the
// pushes that change them, and every 30 seconds.
Item {
    id: root
    property real at: Time.now               // when the counts were last read: the top bar's "Live · Ns ago"

    function refresh() {
        if (!falcon.isConnected) return
        at = Time.now
        var me = falcon.accountId

        falcon.call("hierarchy.tree", {}, function (ok, r) {
            if (!ok) return
            var ds = r.departments || [], machines = 0, held = 0
            for (var i = 0; i < ds.length; i++) {
                var ws = ds[i].workers || []
                machines += ws.length
                for (var k = 0; k < ws.length; k++)
                    if (ws[k].session && ws[k].session.occupied_via && ws[k].session.occupied_via !== "native") held++
            }
            Nav.departments = ds.length
            Nav.deptName = ds.length === 1 ? ds[0].name : ""
            Nav.count("machines", machines)
        })
        // conversations with something unread (version 1, chat.list): the count pulses until they are read
        falcon.call("chat.list", {}, function (ok, r) {
            var n = ok ? (r.conversations || []).filter(function (c) { return c.unread > 0 }).length : 0
            Nav.count("messages", n, true, n > 0)
        })
        falcon.call("resource.violations", {}, function (ok, r) {
            var open = 0
            if (ok) { var vs = r.violations || []; for (var i = 0; i < vs.length; i++) if (!vs[i].resolved_at) open++ }
            Nav.count("restricted", open, true)
            Nav.count("issues", open, true)
        })
        falcon.call("task.list", {}, function (ok, r) {
            var n = 0
            if (ok) { var ts = r.tasks || []; for (var i = 0; i < ts.length; i++) if (ts[i].status !== "completed") n++ }
            Nav.count("tasks", n)
        })
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onScopeChanged() { root.refresh() }
        function onPushReceived(type, payload) {
            if (/^(chat|assistance|task|resource|session|hierarchy|reports|pc\.presence|enroll)/.test(type)) refresh.restart()
        }
    }
    Timer { id: refresh; interval: 300; onTriggered: root.refresh() }
    Timer { interval: 30000; running: falcon.isConnected; repeat: true; onTriggered: root.refresh() }
    Component.onCompleted: if (falcon.isConnected) refresh()
}
