pragma Singleton

// THE ORGANISATION AS THIS CONSOLE SEES IT: departments, their Admins, their machines, and one word
// for each machine's health. Read once and shared, so the Overview, Machines, Departments, Registry
// and Rollout all say the same thing about the same machine. Refreshed on connect, on the pushes that
// change it, and every 30 seconds.
//
// HEALTH (the concept's five marks): the most serious thing open on the machine.
//   healthy (quiet grey) · warning ("worth a look", one amber dot) · high (red tint) · critical (solid red)
//   · offline (dashed: not checking in, so its health is unknown)
import QtQuick

QtObject {
    id: fleet

    property var depts: []          // [{id, name, admins: [...], machines: [...]}]
    // what was known the last time this account was connected (local, dated, read-only): pickers use it until the Engine has answered, or when it cannot
    property var cachedTree: []
    property real cachedAt: 0
    function loadCached() {
        if (typeof falcon.cacheGet !== "function") return
        var c = falcon.cacheGet("tree")
        cachedTree = (c && c.items) || []
        cachedAt = c && c.at ? c.at * 1000 : 0
    }
    // said under a picker whose names are not live: where they came from and how old they are. Empty when they are live.
    readonly property string asOf: {
        if (falcon.isConnected && loaded) return ""
        var when = loaded ? at : cachedAt
        if (!falcon.isConnected) return when ? "Not connected. Names as of " + Time.at(when) : "Not connected."
        return when ? "Names as of " + Time.at(when) + ", from the last time you were connected. Updating." : ""
    }
    function cachedPeople() {
        var out = []
        cachedTree.forEach(function (d) { (d.workers || []).forEach(function (w) { if (w.name && w.account_id) out.push({ name: w.name, sub: (w.hostname || "") + " · " + (d.name || ""), host: w.hostname || "", account: w.account_id }) }) })
        return out
    }
    function cachedMachines() {
        var out = []
        cachedTree.forEach(function (d) { (d.workers || []).forEach(function (w) { out.push({ host: w.hostname, sub: (w.name || "no user") + " · " + d.name + " · last known" }) }) })
        return out
    }
    property Connections remember: Connections {
        target: falcon
        function onConnected() { fleet.loadCached() }
    }
    property var machines: []       // [{pc_id, host, user, dept, deptName, online, seen, session, held, ver, behind, escalated, failures, status, note, issues}]
    property var byHost: ({})
    property var byPc: ({})
    property var violations: []
    property var pings: []
    property var deviations: []
    property string version: ""     // the current version
    property var rollout: null
    property real at: 0
    property bool loaded: false

    readonly property var order: ({ critical: 0, high: 1, warning: 2, offline: 3, healthy: 4 })
    readonly property var words: ({ healthy: "Healthy", warning: "Worth a look", high: "High", critical: "Critical", offline: "Offline" })
    // the mark a status draws
    function mark(status) {
        return status === "critical" ? "crit" : status === "high" ? "high" : status === "warning" ? "watch"
             : status === "offline" ? "offline" : "quiet"
    }
    function dept(id) { for (var i = 0; i < depts.length; i++) if (depts[i].id === id) return depts[i]; return null }
    function deptName(id) { var d = dept(id); return d ? d.name : "" }
    function byAccount(a) { for (var i = 0; i < machines.length; i++) if (machines[i].account === a) return machines[i]; return null }
    // an Admin's name by account, from the departments this console sees ("" when it is not one of them)
    function adminName(acc) { for (var i = 0; i < depts.length; i++) for (var j = 0; j < depts[i].admins.length; j++) if (depts[i].admins[j].account_id === acc) return depts[i].admins[j].name; return "" }
    function byUser(n) { for (var i = 0; i < machines.length; i++) if (machines[i].user === n) return machines[i]; return null }
    function inDept(id) { return machines.filter(function (m) { return m.dept === id }) }
    // every open issue, worst first then oldest first, each with its machine
    readonly property var sevOrder: ({ critical: 0, high: 1, warning: 2, medium: 2, low: 3 })
    readonly property var typeLabel: ({ file: "Restricted file", update: "Stuck update", help: "Help request", deviation: "Deviation", flow: "Flow blocked" })
    readonly property var issues: {
        var out = []
        for (var i = 0; i < machines.length; i++)
            for (var k = 0; k < machines[i].issues.length; k++) {
                var x = Object.assign({ host: machines[i].host, pc_id: machines[i].pc_id, dept: machines[i].dept }, machines[i].issues[k])
                out.push(x)
            }
        out.sort(function (a, b) { return fleet.sevOrder[a.sev] - fleet.sevOrder[b.sev] || (Time.ms(a.at) || 0) - (Time.ms(b.at) || 0) })
        return out
    }
    function sevWord(s) { return s === "critical" ? "Critical" : s === "high" ? "High" : s === "warning" || s === "medium" ? "Medium" : "Low" }
    function sevColor(s) { return s === "critical" ? Theme.crit : s === "high" ? Theme.high : s === "warning" || s === "medium" ? Theme.med : Theme.low }

    property var _parts: ({})
    property int _pending: 0
    function refresh() {
        if (!falcon.isConnected) return
        _parts = {}
        _pending = 8
        var take = function (key) {
            return function (ok, r) {
                var p = Object.assign({}, fleet._parts); p[key] = ok ? r : null; fleet._parts = p
                if (--fleet._pending === 0) fleet.build()
            }
        }
        falcon.call("hierarchy.tree", {}, take("tree"))
        falcon.call("resource.violations", {}, take("violations"))
        falcon.call("updates.rollout_health", {}, take("rollout"))
        falcon.call("assistance.ping_status", {}, take("pings"))
        falcon.call("audit.deviations", {}, take("deviations"))
        falcon.call("hierarchy.sessions_today", {}, take("sessions"))
        // the Engine's own records, when it has them: the machines with their agents, and the issues it raises and resolves
        falcon.call("machines.list", {}, take("machines"))
        falcon.call("issues.list", {}, take("issues"))
    }

    function build() {
        var tree = _parts.tree, ds = tree ? (tree.departments || []) : []
        var vio = _parts.violations ? (_parts.violations.violations || []) : []
        var ro = _parts.rollout, behind = ro ? (ro.pcs_behind || []) : []
        var pg = _parts.pings ? (_parts.pings.pings || []) : []
        var dv = _parts.deviations ? (_parts.deviations.deviations || []) : []
        // issues.list answered: its issues are the issues (raised and resolved by the Engine, with owners and plays);
        // otherwise they are read here from the records they come from, as before
        var eng = _parts.issues && _parts.issues.issues ? _parts.issues.issues : null
        engine = eng !== null
        summary = _parts.issues && _parts.issues.summary ? _parts.issues.summary : null
        var engBy = {}
        if (eng) eng.forEach(function (x) { if (x.state === "resolved") return; var k = x.pc_id === null || x.pc_id === undefined ? "none" : x.pc_id; (engBy[k] = engBy[k] || []).push(x) })
        var ml = _parts.machines && _parts.machines.machines ? _parts.machines.machines : []
        var agentBy = {}
        ml.forEach(function (x) { agentBy[x.pc_id] = x })
        var behindBy = {}
        for (var b = 0; b < behind.length; b++) behindBy[behind[b].pc_id] = behind[b]
        var pingBy = {}
        // one row per ping, oldest first: a person's first ping, and how many they sent
        for (var p = 0; p < pg.length; p++) { var nm = pg[p].from_name; if (pingBy[nm]) pingBy[nm].n++; else pingBy[nm] = { first: pg[p], n: 1 } }

        var outD = [], outM = [], bh = {}, bp = {}
        for (var i = 0; i < ds.length; i++) {
            var d = ds[i], ms = []
            var ws = d.workers || []
            for (var k = 0; k < ws.length; k++) {
                var w = ws[k], issues = []
                var ag = agentBy[w.pc_id]
                var online = ag ? !!ag.online : (w.online !== false && w.status !== "inactive")
                // an issue: {id, sev (critical|high|warning), type, title, subject, note, at, ref}
                for (var v = 0; v < vio.length; v++)
                    if (!vio[v].resolved_at && vio[v].found_on_pc_id === w.pc_id)
                        issues.push({ id: "V-" + vio[v].violation_id, sev: vio[v].resource_tag === "restricted" ? "critical" : "high", type: "file",
                                      title: "Restricted file copied where it isn't allowed", subject: vio[v].filename,
                                      note: "Copy of restricted " + vio[v].filename, at: vio[v].detected_at, ref: vio[v] })
                var be = behindBy[w.pc_id]
                if (be) issues.push(be.escalated
                    ? { id: "U-" + w.pc_id, sev: "high", type: "update", title: "Update past the escalation limit",
                        subject: (be.version || "behind") + " → " + (ro && ro.version ? ro.version.version_string : "current"),
                        note: "Update past the escalation limit", at: be.last_attempt_at, ref: be }
                    : { id: "U-" + w.pc_id, sev: "warning", type: "update", title: "One version behind",
                        subject: (be.version || "behind") + " → " + (ro && ro.version ? ro.version.version_string : "current"),
                        note: "A version behind" + (be.failures ? ", " + be.failures + " failed attempt" + (be.failures === 1 ? "" : "s") : ""),
                        at: be.last_attempt_at, ref: be })
                if (w.name && pingBy[w.name])
                    issues.push({ id: "P-" + pingBy[w.name].first.id, sev: "warning", type: "help", title: "Help request unanswered",
                                  subject: w.name + " · " + Theme.many(pingBy[w.name].n, "ping"),
                                  note: "Help request unanswered", at: pingBy[w.name].first.sent_at, ref: pingBy[w.name].first })
                for (var x = 0; x < dv.length; x++)
                    if (dv[x].observed_pc_id === w.pc_id) {
                        var what = String(dv[x].expectation || "deviation").replace(/[._]/g, " ")
                        issues.push({ id: "D-" + dv[x].id, sev: "warning", type: "deviation", title: what.charAt(0).toUpperCase() + what.slice(1),
                                      subject: dv[x].detail && (dv[x].detail.presented || dv[x].detail.announced_hostname) ? "presented " + (dv[x].detail.presented || dv[x].detail.announced_hostname) : "",
                                      note: what.charAt(0).toUpperCase() + what.slice(1), at: dv[x].detected_at, ref: dv[x] })
                    }
                if (eng) issues = (engBy[w.pc_id] || []).map(fleet.fromEngine)
                var worst = issues.slice().sort(function (a, c) { return fleet.order[a.sev] - fleet.order[c.sev] })[0]
                var status = !online ? "offline" : worst ? worst.sev : "healthy"
                var s = w.session
                var held = s && s.occupied_via && s.occupied_via !== "native" ? (s.occupant_name || "Someone") : ""
                var m = {
                    pc_id: w.pc_id, account: w.account_id, host: w.hostname || ("PC " + w.pc_id), user: w.name || "", dept: d.department_id, deptName: d.name,
                    online: online, seen: w.last_seen_at || null, session: s || null, held: held,
                    heldFrom: held && s.entered_at ? s.entered_at : null,
                    ip: ag ? ag.ip || "" : "", gen: ag ? ag.key_generation : null, os: ag ? ag.os || "" : "",
                    ver: ag && ag.version ? ag.version : be ? (be.version || "behind") : (ro && ro.version ? ro.version.version_string : ""),
                    behind: ag && ag.version ? !!ag.behind : !!be, escalated: be ? !!be.escalated : false, failures: be ? be.failures : 0, lastTry: be ? be.last_attempt_at : null,
                    status: status,
                    note: !online ? "Offline" + (w.last_seen_at ? " since " + Time.at(w.last_seen_at) : "") + (worst ? " · " + worst.note.toLowerCase() : "")
                                  : worst ? worst.note : (held ? "Session held by " + held : (w.name ? "" : "No one signed in")),
                    issues: issues
                }
                ms.push(m); outM.push(m); bh[m.host] = m; bp[m.pc_id] = m
            }
            outD.push({ id: d.department_id, name: d.name, admins: d.admins || [], machines: ms })
            for (var a = 0; a < (d.admins || []).length; a++)
                if (d.admins[a].account_id === falcon.accountId) Nav.myName = d.admins[a].name
        }
        if (tree && typeof falcon.cachePut === "function")      // only what a picker needs, not sessions or health
            falcon.cachePut("tree", ds.map(function (d) {
                return { department_id: d.department_id, name: d.name, admins: (d.admins || []).map(function (a) { return { account_id: a.account_id, name: a.name } }),
                         workers: (d.workers || []).map(function (w) { return { pc_id: w.pc_id, account_id: w.account_id, hostname: w.hostname, name: w.name } }) }
            }))
        depts = outD
        machines = outM
        byHost = bh
        byPc = bp
        violations = vio
        pings = pg
        deviations = dv
        rollout = ro
        version = ro && ro.version ? ro.version.version_string : ""
        sessionsToday = _parts.sessions ? (_parts.sessions.sessions || []) : []
        at = Time.now
        loaded = true
    }
    property var sessionsToday: []
    property bool engine: false            // the issues are the Engine's (issues.list), not read here
    property var summary: null             // issues.list's figures
    // an Engine issue as the rest of the console reads one; `ref` keeps the whole of it, `iid` its id
    function fromEngine(x) {
        return { id: "I-" + x.id, iid: x.id, code: x.code, sev: x.severity === "medium" ? "warning" : x.severity, type: x.type, title: x.title,
                 subject: x.subject || "", note: x.title, at: x.opened_at, ref: x, owner: x.owner, state: x.state, label: x.label, past: !!x.past_target,
                 escalated: !!x.escalated }
    }

    property Timer later: Timer { interval: 400; onTriggered: fleet.refresh() }
    property Timer every: Timer { interval: 30000; running: falcon.isConnected; repeat: true; onTriggered: fleet.refresh() }
    property Connections link: Connections {
        target: falcon
        function onConnected() { fleet.refresh() }
        function onScopeChanged() { fleet.refresh() }
        function onPushReceived(type, payload) {
            if (/^(session|hierarchy|pc\.presence|resource|update|assistance|enroll|issue|machine)/.test(type)) fleet.later.restart()
        }
    }
    Component.onCompleted: { loadCached(); if (falcon.isConnected) refresh() }
}
