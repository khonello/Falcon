import QtQuick
import "."

// ROLLOUT, at both levels. A version is approved only when every machine runs the one before it, so the page
// is the machines holding the next one back: the list, the machine beside it, and how many run the current
// version, day by day, under both. Read from rollout.gate: each machine's attempts, last error, next try and
// escalation; who was left out and why; the version waiting; adoption since the current one was approved.
// Leaving a machine out (with a reason) and approving are the Super User's; an Admin retries their own.
Page {
    id: page
    objectName: "rolloutView"

    property string sel: Nav.sub ? String(Nav.sub) : ""
    property int dept: 0
    property var gate: null
    property string reason: ""

    function load() { if (falcon.isConnected) falcon.call("rollout.gate", {}, function (ok, r) { page.gate = ok ? r : null }) }
    Component.onCompleted: load()
    Connections { target: falcon
                  function onConnected() { page.load() }
                  function onPushReceived(type) { if (/^update/.test(type)) again.restart() } }
    Timer { id: again; interval: 400; onTriggered: page.load() }

    readonly property string cur: gate && gate.current ? gate.current.version : (Fleet.version || "—")
    readonly property string nextV: gate && gate.next ? gate.next.version : ""
    readonly property var holding: gate ? gate.holding || [] : []
    readonly property var strip: gate ? gate.strip || {} : {}
    readonly property var rows: holding.map(function (h) { var m = Fleet.byPc[h.pc_id] || {}; return Object.assign({ host: h.hostname, user: m.user || "", deptName: h.department_name || m.deptName || "" }, h) })
        .filter(function (x) { return (!page.dept || x.department_id === page.dept) && (x.host + " " + x.user + " " + x.deptName).toLowerCase().indexOf(list.query.toLowerCase()) >= 0 })
    readonly property var m: { for (var i = 0; i < rows.length; i++) if (rows[i].host === sel) return rows[i]; return rows.length ? rows[0] : null }
    readonly property var depts: Fleet.depts.filter(function (d) { return d.machines.length }).map(function (d) {
        return { d: d, n: d.machines.length, ok: d.machines.filter(function (x) { return !x.behind }).length }
    }).sort(function (a, b) { return a.ok / a.n - b.ok / b.n })
    function times(n) { return n === 1 ? "once" : n === 2 ? "twice" : n + " times" }

    Confirm { id: confirm; page: page }
    function retry(x) {
        falcon.call("updates.retry", { pc_id: x.pc_id, when: "now" }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not retried"); return }
            Msg.ok(r.when === "now" ? x.host + " is trying now" : x.host + " tries " + r.when); page.load()
        })
    }
    function leaveOut() {
        var x = m
        falcon.call("updates.leave_out", { pc_id: x.pc_id, reason: reason.trim() }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not left out"); return }
            Msg.ok(x.host + " is left out of the gate · recorded"); reason = ""; leave.close(); page.load()
        })
    }
    function takeBack(x) {
        falcon.call("updates.take_back", { pc_id: x.pc_id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not changed"); return }
            Msg.ok(x.host + " holds the gate again"); page.load()
        })
    }
    function approve() {
        confirm.ask({ title: "Approve " + nextV + "?", ok: "Approve", text: "Every machine is told to update, department by department. The record notes that you approved it." },
                    function () { falcon.call("updates.approve", { version: page.nextV }, function (ok, r) {
                        if (!ok) { Msg.failed(r && r.message ? r.message : "Not approved"); return }
                        Msg.ok("Approved " + page.nextV); page.load(); Fleet.refresh() }) })
    }

    Drawer {
        id: leave
        page: page
        width: 420
        title: page.m ? "Leave " + page.m.host + " out of the gate" : ""
        note: page.reason.trim() === "" ? "Say why. It is recorded with the approval." : ""
        footer: [ Btn { text: "Cancel"; onClicked: leave.close() },
                  Btn { kind: "primary"; text: "Leave it out"; enabled: page.reason.trim() !== ""; onClicked: page.leaveOut() } ]
        Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text2
              text: (page.nextV ? page.nextV : "The next version") + " can then be approved without waiting for it. It keeps trying to update; you can put it back in the gate." }
        TextArea2 { width: parent.width; text: page.reason; placeholder: "Why can it wait?"; onEdited: function (t) { page.reason = t } }
    }

    Strip {
        width: parent.width
        items: [
            { label: "Current version", value: page.cur, delta: page.gate && page.gate.current ? "approved " + Time.day(page.gate.current.approved_at) + " by " + (page.gate.current.approved_by === "You" ? "you" : page.gate.current.approved_by || "the Super User") : "" },
            { label: "Running it", value: Theme.fmt(page.strip.running || 0), unit: "/ " + Theme.fmt(page.strip.total || 0), delta: page.strip.pct !== undefined && page.strip.pct !== null ? page.strip.pct + "% of machines" : "" },
            { label: "Holding " + (page.nextV || "the next one") + " back", value: Theme.fmt(page.strip.holding || 0), dc: page.strip.holding ? Theme.crit : Theme.ok,
              delta: page.strip.holding ? (Nav.boss ? (page.nextV ? page.nextV + " is ready and waits on them" : "the next version waits on them") : "from this department")
                                        : (Nav.boss ? (page.nextV ? page.nextV + " can be approved" : "the next version can be approved") : "none from this department") },
            { label: "Failed installs, 7 days", value: Theme.fmt(page.strip.failed_installs || 0),
              delta: (page.strip.failed_hosts || []).length ? page.strip.failed_hosts.map(function (f) { return f.hostname + " " + page.times(f.n) }).join(", ") : "none" }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            title: "Holding the gate"
            sub: "not yet on " + page.cur + " · click one to see it on the right"
            placeholder: "Filter by machine or department"
            tools: Select {
                visible: Nav.boss
                width: 170
                small: true
                popupWidth: 240
                value: page.dept
                options: [{ value: 0, label: "Every department" }].concat(page.depts.map(function (x) { return { value: x.d.id, label: x.d.name + " · " + Math.round(x.ok / x.n * 100) + "% on " + page.cur } }))
                onPicked: function (v) { page.dept = v }
            }
            rows: page.rows
            rowKey: "host"
            pick: page.m ? page.m.host : null
            onPicked: function (k) { page.sel = k }
            icon: "desktop"
            nameTitle: "Machine"
            nameMono: true
            nameText: function (x) { return x.host }
            nameLine: function (x) { return (x.user || "No one signed in") + " · " + x.deptName }
            cols: [{ title: "Running", width: 100, text: function (x) { return x.running || "—" } },
                   { title: "Last error", width: 230, text: function (x) { return x.last_error || "—" } },
                   { title: "Next try", width: 190, text: function (x) { return x.state === "left_out" ? "Left out of the gate" : x.next_try } }]
            now: function (x) { return x.state === "escalated" ? ["Escalated to " + (x.escalated_to || "you"), "bad"] : x.state === "offline" ? ["Offline", "bad"] : x.state === "left_out" ? ["Left out", "wait"] : ["Retrying", "wait"] }
            showEmpty: page.gate !== null && page.holding.length === 0
            emptyIcon: "check"
            emptyTitle: "Every machine runs " + page.cur
            emptyText: "Nothing holds the next version back." + (Nav.boss ? " Approve it when it is ready." : "")
        }
        SidePanel {
            width: (parent.width - 14) * 4 / 12
            showEmpty: page.m === null
            emptyIcon: "desktop"
            emptyText: "Pick a machine in the list."
            title: page.m ? page.m.host : ""
            sub: page.m && page.sel === page.m.host ? "the one you picked" : "the first in the list · click another"
            facts: page.m ? [["Running", page.m.running || "—"], ["Should run", page.m.should_run || page.cur],
                             ["Attempts", String(page.m.attempts || 0) + (page.m.last_attempt_at ? ", last " + Time.at(page.m.last_attempt_at) : "")],
                             ["Last error", page.m.last_error || "None recorded"],
                             ["Escalated", page.m.escalated_at ? Time.at(page.m.escalated_at) + ", to " + (page.m.escalated_to || "you") : "No", page.m.escalated_at ? Theme.crit : null],
                             ["Next try", page.m.state === "left_out" ? "Left out of the gate" : page.m.next_try], ["Department", page.m.deptName]]
                             .concat(page.m.left_out ? [["Left out", page.m.left_out.reason + " · " + Time.day(page.m.left_out.at)]] : []) : []
            actions: [
                Btn { visible: Nav.boss && page.m !== null && page.m.state !== "left_out"; text: "Leave it out of the gate"; onClicked: { page.reason = ""; leave.open() } },
                Btn { visible: Nav.boss && page.m !== null && page.m.state === "left_out"; text: "Put it back in the gate"; onClicked: page.takeBack(page.m) },
                Btn { kind: "primary"; text: "Retry now"; enabled: page.m !== null && page.m.online; tip: page.m && !page.m.online ? "It is offline: it tries when it is back" : ""; onClicked: page.retry(page.m) }
            ]
        }
    }

    Panel {
        width: parent.width
        title: "Machines on " + page.cur
        sub: "since it was approved · the gap to the goal is the machines holding " + (page.nextV || "the next version") + " back"
        extra: [
            Txt { visible: !Nav.boss; text: "The Super User approves the next version once every machine runs " + page.cur; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter },
            Btn { visible: Nav.boss; small: true; kind: "primary"; text: page.nextV ? "Approve " + page.nextV : "No version waiting"; enabled: !!(page.gate && page.gate.can_approve)
                  tip: !page.nextV ? "A version is staged by the packaging pipeline before it can be approved." : page.strip.holding ? "A version is approved only when every machine runs the one before it." : ""
                  onClicked: page.approve() }
        ]
        Column {
            width: parent.width
            spacing: 8
            Empty { visible: !!page.gate && !(page.gate.adoption && page.gate.adoption.length); width: parent.width; h: 160; icon: "cloudupload"; title: "No version approved yet"; text: "How many machines run the current version, day by day." }
            Adoption { visible: !!(page.gate && page.gate.adoption && page.gate.adoption.length > 0); width: parent.width; height: 200
                       days: page.gate ? page.gate.adoption || [] : []; goal: page.strip.total || 0; version: page.cur }
            Txt { visible: page.holding.length > 0; width: parent.width; color: Theme.text2; wrapMode: Text.WordWrap; elide: Text.ElideNone
                  text: Theme.many(page.holding.length, "machine") + (page.holding.length === 1 ? " is" : " are") + " still on older versions: "
                        + page.holding.map(function (h) { return h.hostname + " on " + (h.running || "an older one") }).join(", ") + ". The gap between the line and the goal is them." }
        }
    }
}
