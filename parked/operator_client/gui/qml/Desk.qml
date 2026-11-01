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
    property var proposals: []       // what Detective suggests that is the Super User's to answer: a follow-up on a case sent up (pausing a flow or marking a folder is the Admin's)
    property var restricted: []      // flows waiting for the person who restricted something to say it may be carried (flow.restricted_waiting)
    property var handover: null      // handover.status: machines asking to become the Super User's
    property bool loaded: false

    readonly property var words: ({ resource_violation: "Restricted file", flow_failure: "Flow failed",
                                    update_status: "Update stuck", deviation: "Deviation", about_admin: "About an Admin" })
    readonly property var icons: ({ resource_violation: "fileprotect", flow_failure: "branches", update_status: "cloudsync",
                                    deviation: "warn", about_admin: "eye" })
    readonly property var sevOf: ({ resource_violation: "high", update_status: "high", flow_failure: "medium", deviation: "medium", about_admin: "medium" })
    function word(c) { return words[c] || String(c).replace(/_/g, " ") }

    function refresh() {
        if (!falcon.isConnected || falcon.role !== "super_user" || falcon.traversing) return
        falcon.call("reports.list", {}, function (ok, r) { desk.reports = ok ? (r.reports || []) : []; desk.loaded = true })
        falcon.call("reports.routing_get", {}, function (ok, r) { if (ok) { desk.routing = r.routing || []; desk.fixed = r.fixed || ["about_admin"] } })
        falcon.call("task.dept_list", {}, function (ok, r) { desk.deptTasks = ok ? (r.tasks || []) : [] })
        falcon.call("proposals.list", {}, function (ok, r) { desk.proposals = ok && r ? (r.proposals || []).filter(function (p) { return p.kind === "follow_up_task" }) : [] })
        falcon.call("flow.restricted_waiting", {}, function (ok, r) { desk.restricted = ok && r ? (r.waiting || []) : [] })
        falcon.call("handover.status", {}, function (ok, r) { desk.handover = ok ? r : null })
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
        // what Detective suggests to the other features: said, never done, until you say so
        proposals.forEach(function (p) {
            var yes = p.kind === "pause_flow" ? ["Pause the flow", "Pauses it now, as your act. Resume it from Flows when it is safe.", "Pause"]
                    : p.kind === "mark_folder" ? ["Show me where to mark it", "Marks are made on the machine they are on, from the Restricted page. This tells you which folder.", "Show me"]
                    : ["Give me the words for a task", "The wording for a task to the department's Admin. You give it on the Tasks page.", "Show me"]
            out.push({ id: "prop-" + p.id, kind: "proposal", p: p, sev: p.kind === "pause_flow" ? "high" : "medium", icon: p.kind === "pause_flow" ? "branches" : p.kind === "mark_folder" ? "fileprotect" : "checksquare",
                       title: p.title, short: "Detective: " + (p.kind === "pause_flow" ? "pause a flow?" : p.kind === "mark_folder" ? "mark a folder?" : "a follow-up?"), age: Time.age(p.created_at),
                       why: "Detective sees this and the other features cannot. It only suggests: nothing happens until you say so.",
                       options: [{ key: "yes", icon: "check", title: yes[0], desc: yes[1], verb: yes[2] },
                                 { key: "no", icon: "close", title: "Not now", desc: "It is dismissed and not suggested again while the cause stands.", verb: "Dismiss" }] })
        })
        // a flow that wants to carry something restricted, and this person made the restriction
        restricted.forEach(function (c) {
            out.push({ id: "rc-" + c.id, kind: "restricted", c: c, sev: "medium", icon: "lock", title: "Flow " + c.flow_id + " wants to carry " + c.name + ", which is restricted",
                       short: "Restricted: " + c.name, age: Time.age(c.asked_at),
                       why: "The flow is paused. It goes on only if you allow it, and you can take that back any time from the Flows page. " + (c.sample_path ? "It met it at " + c.sample_path + "." : ""),
                       options: [{ key: "yes", icon: "check", title: "Allow this flow", desc: "Its destination folders become a place this content may be, until you take it back.", verb: "Allow" },
                                 { key: "no", icon: "pause", title: "Keep it paused", desc: "Nothing moves. It asks again if someone tries to resume it.", verb: "Keep paused" }] })
        })
        // a machine asking to become the Super User's
        if (handover && handover.waiting) handover.waiting.forEach(function (w) {
            out.push({ id: "ho-" + w.id, kind: "handover", w: w, sev: "high", icon: "desktop", title: w.hostname + " is asking to become your machine", short: "Move to " + w.hostname, age: Time.age(w.created_at),
                       why: "Only someone in front of it can see the code. Typing it on the Registry page moves the Super User there; this machine then stops being the Super User's.",
                       options: [{ key: "go", icon: "login", title: "Type its code on the Registry", desc: "Under Asking to join.", verb: "Open Registry", go: ["registry", "ask"] },
                                 { key: "refuse", icon: "close", title: "Refuse it", desc: "It is told no, and the window stays as it was.", verb: "Refuse" }] })
        })
        var o = { critical: 0, high: 1, medium: 2, low: 3 }
        return out.sort(function (a, b) { return o[a.sev] - o[b.sev] })
    }

    property Timer later: Timer { interval: 400; onTriggered: desk.refresh() }
    property Connections link: Connections {
        target: falcon
        function onConnected() { desk.refresh() }
        function onScopeChanged() { desk.refresh() }
        function onPushReceived(type) { if (/^(report|task\.dept|update|proposal|flow\.restricted|enroll|handover)/.test(type)) desk.later.restart() }
    }
    Component.onCompleted: refresh()
}
