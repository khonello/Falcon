pragma Singleton
import QtQuick
import "."

// THE STANDARD, AND WHAT WAS MEASURED AGAINST IT. A rule is a pattern: what should happen. A deviation is
// a departure from one, with an owner. The built-in rules are what Falcon already enforces, listed so every
// deviation points to one; rules the Super User sets need the Engine's rule store, which does not exist yet,
// so `canSet` is false and the editor says so.
QtObject {
    id: rules
    readonly property bool canSet: false
    readonly property string cannot: "Rules you set need the Engine's rule store, which is not built yet"

    readonly property var trig: ({
        file: "A copy of a restricted file appears where it is not allowed", second: "A second session starts on a machine already in use",
        cert: "A machine presents a certificate that does not match its name", help: "A worker pings for help",
        report: "A report is written for a department", version: "A new version is approved", outhours: "Someone enters a machine outside working hours",
        task: "A department task is given", seat: "A department loses its last Admin" })
    readonly property var exp: ({ answer: "An Admin answers the ping", addressed: "Someone marks the report addressed", updated: "The machine runs that version",
                                  seen: "An Admin marks it seen", appoint: "Another Admin is appointed" })
    readonly property var readings: ["Admin entries outside working hours", "Admin entries into other departments' machines", "Entries into one machine by the same Admin", "Failed sign-ins on one machine"]
    readonly property var whos: ({ everyone: "Everyone", workers: "Workers", admins: "Admins", machines: "Machines", depts: "Departments" })
    readonly property var whol: ({ everyone: "Everyone: workers, Admins and machines", workers: "Workers", admins: "Admins", machines: "Machines", depts: "Departments" })
    readonly property var units: ({ minutes: 1, hours: 60, days: 1440 })
    readonly property var shapes: ({
        never:  { w: "Must never happen", icon: "stop", d: "The first time it happens, it is a deviation." },
        follow: { w: "Must follow", icon: "fieldtime", d: "After one thing happens, another must follow in time." },
        limit:  { w: "Stay within a limit", icon: "linechart", d: "A count or rate that must not go over a line." } })
    readonly property var whoKind: ({ pc: ["PC", "desktop"], worker: ["Worker", "user"], admin: ["Admin", "safety"], dept: ["Department", "apartment"] })
    readonly property var outcomes: ({ open: ["Open", Theme.med], explained: ["Explained", Theme.ser1], accepted: ["Accepted", Theme.ok], escalated: ["Escalated", Theme.crit], dismissed: ["Dismissed", Theme.text4] })

    // Built into Falcon: always enforced. Seen, not edited.
    readonly property var builtin: [
        { id: "B-1", name: "Restricted files stay where they are", shape: "never", trigger: "file", locked: true, who: "everyone", resp: { report: true, admin: true } },
        { id: "B-2", name: "One session on a machine at a time", shape: "never", trigger: "second", locked: true, who: "everyone", resp: { report: false, admin: false } },
        { id: "B-3", name: "Machines run the approved version", shape: "follow", trigger: "version", expect: "updated", within: 2880, locked: true, who: "machines", resp: { report: true, admin: true } },
        { id: "B-4", name: "A machine's certificate matches its name", shape: "never", trigger: "cert", locked: true, who: "machines", resp: { report: true, admin: true } }
    ]
    readonly property var templates: [
        { id: "t-help", name: "Unanswered help request", d: "A worker pings; an Admin has an hour to answer.", state: { shape: "follow", trigger: "help", expect: "answer", within: { n: 1, unit: "hours" }, who: "admins" } },
        { id: "t-report", name: "Reports left waiting", d: "A report is written; someone has an hour to address it.", state: { shape: "follow", trigger: "report", expect: "addressed", within: { n: 1, unit: "hours" }, who: "admins" } },
        { id: "t-cross", name: "An Admin outside their department", d: "More than three entries into another department's machines in a week.", state: { shape: "limit", reading: readings[1], limit: { n: 3, per: "week" }, who: "admins" } },
        { id: "t-night", name: "Out-of-hours session", d: "Anyone entering a machine outside working hours.", state: { shape: "never", trigger: "outhours", who: "everyone" } },
        { id: "t-task", name: "Department task not seen", d: "A task is given; an Admin has four hours to mark it seen.", state: { shape: "follow", trigger: "task", expect: "seen", within: { n: 4, unit: "hours" }, who: "admins" } },
        { id: "t-repeat", name: "Repeated entries into one machine", d: "The same Admin entering one machine more than twice a day.", state: { shape: "limit", reading: readings[2], limit: { n: 2, per: "day" }, who: "admins" } }
    ]
    readonly property var all: builtin
    function byId(id) { for (var i = 0; i < all.length; i++) if (all[i].id === id) return all[i]; return { id: id, name: id, shape: "never", locked: false, who: "everyone", resp: {} } }

    function dur(m) { return m % 1440 === 0 ? (m / 1440) + " day" + (m === 1440 ? "" : "s") : m % 60 === 0 ? (m / 60) + " hour" + (m === 60 ? "" : "s") : m + " minutes" }
    function lc(t) { return t.charAt(0).toLowerCase() + t.slice(1) }
    function sentence(r) {
        return r.shape === "never" ? trig[r.trigger] + ": always a deviation."
             : r.shape === "follow" ? trig[r.trigger] + ", then " + lc(exp[r.expect]) + " within " + dur(r.within) + "."
             : r.reading + ": " + (r.limit.n === 0 ? "none" : "no more than " + r.limit.n) + " per " + r.limit.per + "."
    }
    function scope(r) { return r.who === "depts" ? "Every department" : whos[r.who] + ", " + (r.depts && r.depts !== "all" ? Theme.many(r.depts.length, "department") : "every department") }
    function blank() { return { name: "", shape: "follow", trigger: "help", expect: "answer", within: { n: 1, unit: "hours" }, reading: readings[0], limit: { n: 3, per: "week" },
                                who: "admins", depts: "all", resp: { report: true, admin: false, action: false, actionId: "" } } }
    function toPattern(r) {
        var b = blank(), w = r.within ? (r.within % 1440 === 0 ? { n: r.within / 1440, unit: "days" } : r.within % 60 === 0 ? { n: r.within / 60, unit: "hours" } : { n: r.within, unit: "minutes" }) : b.within
        return { name: r.name, shape: r.shape, trigger: r.trigger || b.trigger, expect: r.expect || b.expect, within: w, reading: r.reading || b.reading,
                 limit: r.limit ? Object.assign({}, r.limit) : b.limit, who: r.who, depts: r.depts || "all", resp: Object.assign({}, b.resp, r.resp || {}) }
    }

    // ---- deviations, as the Engine records them (deviation_log), read as records against a rule ----------
    // expectation -> the rule it departs from
    readonly property var ruleOfExpectation: ({ account_bound_to_one_pc: "B-4", hostname_mismatch: "B-4", restricted_copy: "B-1", resource_violation: "B-1",
                                               second_session: "B-2", update_stuck: "B-3", version_behind: "B-3" })
    function devRecord(d) {
        var det = d.detail || {}, m = Fleet.byPc[d.observed_pc_id], rid = ruleOfExpectation[d.expectation] || "B-4"
        var exp0 = det.expected_hostname || det.expected, got = det.announced_hostname || det.presented
        var host = m ? m.host : (exp0 || "a machine")
        var short = rid === "B-4" ? host + " presented another name" : String(d.expectation || "deviation").replace(/[._]/g, " ")
        return {
            id: String(d.id), raw: d, rule: rid, kind: "pc", sev: d.severity || (rid === "B-1" ? "high" : "medium"),
            who: host, whoSub: m ? (m.deptName || "") + (m.user ? " · " + m.user : "") : "", dept: m ? m.dept : null, host: m ? m.host : null, pc_id: d.observed_pc_id,
            at: d.detected_at, short: short.charAt(0).toUpperCase() + short.slice(1),
            expected: rid === "B-4" ? "The certificate names " + (exp0 || host) : (det.expected || byId(rid).name),
            happened: rid === "B-4" ? "The certificate names " + (got || "another name") : (det.presented || det.happened || "—"),
            out: d.outcome || (d.resolved_at ? "accepted" : "open"), note: d.outcome_note || d.resolution || "", by: d.resolved_by_name || "", when: d.resolved_at || null
        }
    }
}
