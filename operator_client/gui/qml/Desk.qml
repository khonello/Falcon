pragma Singleton

// WHAT WAITS ON THE SUPER USER: reports nobody below them can take, and the decisions only they make --
// a department with no Admin, a version waiting at the gate, a department's task marked done. Each is an
// instance of a kind; the kind owns its picture and its wording. The queue is computed from the reports,
// the routing and the departments, never stored (UI-COMPONENTS, DecisionKind).
import QtQuick

QtObject {
    id: desk
    property var reports: []
    property var routing: []
    property var fixed: ["about_admin"]
    property var deptTasks: []
    property bool loaded: false

    readonly property var words: ({ resource_violation: "Restricted file", flow_failure: "Flow failed", listener_report: "Listener report",
                                    update_status: "Update stuck", deviation: "Deviation", about_admin: "About an Admin",
                                    directory_structure_conflict: "Folder conflict", cross_department_assistance: "Help across departments" })
    readonly property var icons: ({ resource_violation: "fileprotect", flow_failure: "branches", listener_report: "message", update_status: "cloudsync",
                                    deviation: "warn", about_admin: "eye", directory_structure_conflict: "folder", cross_department_assistance: "team" })
    readonly property var sevOf: ({ resource_violation: "high", update_status: "high", flow_failure: "medium", deviation: "medium", about_admin: "medium" })
    function word(c) { return words[c] || String(c).replace(/_/g, " ") }

    function refresh() {
        if (!falcon.isConnected || falcon.role !== "super_user" || falcon.traversing) return
        falcon.call("reports.list", {}, function (ok, r) { desk.reports = ok ? (r.reports || []) : []; desk.loaded = true })
        falcon.call("reports.routing_get", {}, function (ok, r) { if (ok) { desk.routing = r.routing || []; desk.fixed = r.fixed || ["about_admin"] } })
        falcon.call("task.dept_list", {}, function (ok, r) { desk.deptTasks = ok ? (r.tasks || []) : [] })
    }
    function routedTo(c) { return routing.filter(function (x) { return x.category === c }).map(function (x) { return x.routed_department_id }) }

    readonly property var queue: {
        var out = []
        // reports nobody below can take: one card per kind
        var mine = reports.filter(function (r) { return !r.addressed_at && (desk.fixed.indexOf(r.category) >= 0 || desk.routedTo(r.category).length === 0) })
        var cats = mine.map(function (r) { return r.category }).filter(function (v, i, a) { return a.indexOf(v) === i })
        cats.forEach(function (c) {
            var rs = mine.filter(function (r) { return r.category === c }), isFixed = desk.fixed.indexOf(c) >= 0
            var opts = [{ key: "mark", icon: "check", title: "Mark the ticked ones addressed", desc: "They stay in the record with your name and the time.", verb: "Mark addressed" }]
            if (!isFixed) opts.push({ key: "route", icon: "apartment", title: "Route " + desk.word(c).toLowerCase() + " to departments", desc: "Their Admins take these and every later one. You still receive every report.", verb: "Route it", need: "depts" })
            out.push({ id: "rep-" + c, kind: "reports", cat: c, reports: rs, sev: desk.sevOf[c] || "low", icon: desk.icons[c] || "filetext",
                       title: Theme.fmt(rs.length) + " " + desk.word(c).toLowerCase() + " report" + (rs.length === 1 ? "" : "s") + " only you can address",
                       short: desk.word(c) + " · " + Theme.fmt(rs.length), age: Time.age(rs[rs.length - 1].generated_at),
                       why: isFixed ? "Reports about an Admin are never routed: the department would be judging its own Admin. Only you see them."
                                    : desk.word(c) + " is not routed to any department, so these come to you. Route it and the departments' Admins take them.",
                       options: opts })
        })
        // a department with no Admin
        Fleet.depts.filter(function (d) { return !d.admins.length }).forEach(function (d) {
            out.push({ id: "seat-" + d.id, kind: "seat", dept: d.id, sev: "high", icon: "useradd", title: d.name + " has no Admin", short: d.name + " has no Admin", age: "",
                       why: Theme.many(d.machines.length, "machine") + " and every report from them have nobody below you. Only you can assign an Admin.",
                       options: [{ key: "pick", icon: "user", title: "Promote someone who works there", desc: "Gives them a console and a key, shown once. An Admin belongs to one department.",
                                   verb: "Pick them on Departments", go: ["departments", d.id] },
                                 { key: "new", icon: "useradd", title: "Provision a new Admin for " + d.name, desc: "A new account with its own workstation, from Registry.", verb: "Open Registry", go: ["registry", "acct"] }] })
        })
        // the version gate
        if (Fleet.machines.length && Fleet.version) {
            var bh = Fleet.machines.filter(function (m) { return m.behind })
            out.push({ id: "gate", kind: "gate", sev: "medium", icon: "cloudupload", title: bh.length ? "The next version waits at the gate" : "The next version can be approved",
                       short: bh.length ? "Next version · " + bh.length + " holding it" : "Approve the next version", age: "",
                       why: "A version is approved only when every machine runs the one before it. " + (bh.length ? Theme.many(bh.length, "machine") + (bh.length === 1 ? " still doesn't." : " still don't.") : "Every machine does."),
                       options: [{ key: "wait", icon: "clock", title: "Wait for the gate", desc: bh.length ? "Approve it once " + Theme.listNames(bh.map(function (m) { return m.host })) + " run " + Fleet.version + "." : "Nothing holds it.", verb: "Wait", waits: true },
                                 { key: "approve", icon: "cloudupload", title: "Approve the next version", desc: "Every machine is told to update, department by department.", verb: "Approve", need: "version",
                                   cannot: bh.length ? "The Engine refuses while any machine is behind" : "" }] })
        }
        // a department says its task is done
        deptTasks.filter(function (t) { return t.standing === "done" }).forEach(function (t) {
            var by = (t.admins || []).filter(function (a) { return a.state === "done" })[0]
            out.push({ id: "dtask-" + t.id, kind: "task", task: t, sev: Time.past(t.deadline_at) ? "medium" : "low", icon: "checksquare",
                       title: Fleet.deptName(t.department_id) + " says “" + t.title + "” is done", short: "Done: " + t.title, age: by && by.state_at ? Time.age(by.state_at) : "",
                       why: (by ? by.name + " marked it done" + (by.state_at ? " at " + Time.hhmm(by.state_at) : "") + ". " : "") + "Only you can call it complete.",
                       options: [{ key: "complete", icon: "check", title: "Complete", desc: "It leaves the list, recorded as complete with your name and the time.", verb: "Complete" },
                                 { key: "notyet", icon: "rollback", title: "Not done yet", desc: "It goes back as ongoing, with your note. Every Admin told sees it.", verb: "Send back", need: "message" }] })
        })
        var o = { critical: 0, high: 1, medium: 2, low: 3 }
        return out.sort(function (a, b) { return o[a.sev] - o[b.sev] })
    }

    property Timer later: Timer { interval: 400; onTriggered: desk.refresh() }
    property Connections link: Connections {
        target: falcon
        function onConnected() { desk.refresh() }
        function onScopeChanged() { desk.refresh() }
        function onPushReceived(type) { if (/^(report|task\.dept|update)/.test(type)) desk.later.restart() }
    }
    Component.onCompleted: refresh()
}
