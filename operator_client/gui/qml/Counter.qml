import QtQuick
import "."

// WHAT NEEDS A PERSON, PER AREA, for the menu -- and the few facts every page shares: the
// department this console is for, how many departments there are, the tasks given to this Admin
// that are not seen yet. Fetched on connect, on the pushes that change them, and every 30 seconds.
Item {
    id: root
    property real at: Time.now               // when the counts were last read: the top bar's "Live · Ns ago"
    property var unseenTasks: []              // department tasks given to this Admin, not yet marked seen

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
            Nav.deptName = !Nav.boss && ds.length === 1 ? ds[0].name : ""
            Nav.count(Nav.boss ? "registry" : "machines", Nav.boss ? 0 : machines)
            Nav.count(Nav.boss ? "access" : "sessions", held)
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
            if (!Nav.boss) Nav.count("issues", open, true)
        })
        falcon.call("task.dept_list", {}, function (ok, r) {
            if (!ok) { root.unseenTasks = []; return }
            var ts = r.tasks || [], unseen = [], done = 0
            for (var i = 0; i < ts.length; i++) {
                if (ts[i].standing === "done") done++
                if (ts[i].my_state === "told" && ts[i].standing !== "complete") unseen.push(ts[i])
            }
            root.unseenTasks = unseen
            if (Nav.boss) Nav.count("tasks", done, true)
        })
        if (!Nav.boss)
            falcon.call("task.list", {}, function (ok, r) {
                var n = 0
                if (ok) { var ts = r.tasks || []; for (var i = 0; i < ts.length; i++) if (ts[i].status !== "completed") n++ }
                Nav.count("tasks", n)
            })
        if (Nav.boss) {
            falcon.call("audit.deviations", {}, function (ok, r) {
                var ds = ok ? (r.deviations || []) : []
                Nav.count("accountability", ds.length, true)
            })
            // what waits on the Super User: reports nobody below can take
            falcon.call("reports.list", {}, function (ok, r) {
                var n = 0
                if (ok) { var rs = r.reports || []; for (var i = 0; i < rs.length; i++) if (!rs[i].addressed_at) n++ }
                Nav.count("overview", Desk.queue.length, true)
            })
        }
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onScopeChanged() { root.refresh() }
        function onPushReceived(type, payload) {
            if (/^(assistance|task\.dept|resource|session|hierarchy|reports|pc\.presence|enroll)/.test(type)) refresh.restart()
        }
    }
    Connections {
        target: Nav
        function onBossChanged() { root.refresh() }
    }
    Connections {
        target: Desk
        function onQueueChanged() { if (Nav.boss) Nav.count("overview", Desk.queue.length, true) }
    }
    Timer { id: refresh; interval: 300; onTriggered: root.refresh() }
    Timer { interval: 30000; running: falcon.isConnected; repeat: true; onTriggered: root.refresh() }
    Component.onCompleted: if (falcon.isConnected) refresh()
}
