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
        // a ping is "I need you": the count pulses until every one is answered
        falcon.call("assistance.channels", {}, function (ok, r) {
            var n = 0
            if (ok) {
                var cs = r.channels || []
                for (var i = 0; i < cs.length; i++) {
                    var c = cs[i]
                    if (c.closed_at) continue
                    var iAmHigher = c.superior_account_id === me
                    if ((c.turn === "superior" && iAmHigher) || (c.turn === "sender" && !iAmHigher)) n++
                }
            }
            falcon.call("assistance.ping_status", {}, function (ok2, r2) {
                // one row per ping: what waits is each person who pinged, not each ping
                var pings = ok2 ? (r2.pings || []).map(function (p) { return p.sender_account_id }).filter(function (v, i, a) { return a.indexOf(v) === i }).length : 0
                Nav.count("messages", n + pings, true, n + pings > 0)
            })
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
            if (/^(assistance|task|resource|session|hierarchy|reports|pc\.presence|enroll)/.test(type)) refresh.restart()
        }
    }
    Timer { id: refresh; interval: 300; onTriggered: root.refresh() }
    Timer { interval: 30000; running: falcon.isConnected; repeat: true; onTriggered: root.refresh() }
    Component.onCompleted: if (falcon.isConnected) refresh()
}
