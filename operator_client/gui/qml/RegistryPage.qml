import QtQuick
import "."

// REGISTRY: machines and accounts, each with a key made here, and what was refused at the door. A machine
// asking to join (enroll.request) waits here too, until someone types the code it shows.
//
// From the Engine's registry (registry.accounts, registry.refused, registry.block / unblock): the refused are grouped
// by who tried and from where, each with why and what to do; an address can be blocked at the door.
Page {
    id: page
    objectName: "registryView"

    // the Admin's Registry is their department's machines and people, and who is asking to join; the Super User's is only what the Engine keeps for them
    property string tab: typeof Nav.sub === "string" && Nav.sub === "ask" ? "ask" : Nav.boss ? "door" : typeof Nav.sub === "string" && Nav.sub.indexOf("acct:") === 0 ? "acct" : "pc"
    property var sel: typeof Nav.sub === "string" && Nav.sub ? Nav.sub : null
    property var list: []          // machines.list, when the Engine has it
    property var refused: []       // registry.refused, this week
    property var accounts: []      // registry.accounts
    property var asks: []          // enroll.list
    property string code: ""
    property var handover: null    // handover.status (the Super User only): is a move to another machine open, and who is waiting

    function openHandover(on) {
        falcon.call(on ? "handover.open" : "handover.cancel", {}, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not done"); return }
            Msg.ok(on ? "Open for ten minutes · one new machine may ask" : "Closed")
            page.load()
        })
    }

    function load() {
        if (!falcon.isConnected) return
        if (Nav.boss) falcon.call("handover.status", {}, function (ok, r) { page.handover = ok ? r : null })
        falcon.call("machines.list", {}, function (ok, r) { page.list = ok ? (r.machines || []) : [] })
        falcon.call("registry.refused", { days: 7 }, function (ok, r) { page.refused = ok ? (r.refused || []) : [] })
        falcon.call("registry.accounts", {}, function (ok, r) { page.accounts = ok ? (r.accounts || []) : [] })
        falcon.call("enroll.list", {}, function (ok, r) { page.asks = ok ? (r.requests || []) : [] })
    }
    Component.onCompleted: load()
    Connections { target: falcon
                  function onConnected() { page.load() }
                  function onPushReceived(type, payload) { if (type === "enroll.requested" || type === "machines.changed") page.load() } }

    readonly property var info: { var o = {}; list.forEach(function (x) { o[x.pc_id] = x }); return o }
    readonly property var rows: Fleet.machines.map(function (m) { var x = page.info[m.pc_id] || {}
        return { id: m.host, m: m, gen: x.key_generation || null, ip: x.ip || "", ver: x.version || m.ver || "", seen: x.last_seen_at || m.seen } })
        .filter(function (y) { return (y.m.host + " " + y.m.user + " " + y.m.deptName).toLowerCase().indexOf(lp.query.toLowerCase()) >= 0 })
    readonly property var wsGen: { var o = {}; list.forEach(function (x) { if (x.owner) o[x.owner.account_id] = x }); return o }
    // the Super User and every Admin, as registry.accounts says them; the tree's, while it has not answered
    readonly property var accts: accounts.length ? accounts.map(function (a) {
            return { id: "acct:" + a.account_id, account: a.account_id, name: a.name, you: a.you, role: a.role === "super_user" ? "Super User" : a.role === "admin" ? "Admin" : "Worker",
                     dept: a.department_name || "Head office", deptId: a.department_id, ws: a.workstation || "", pc_id: a.pc_id, gen: a.key_generation, now: a.now }
        })
        : !Nav.boss ? [] : [{ id: "acct:me", account: falcon.accountId, name: "You", you: true, role: "Super User", dept: "Head office", ws: page.wsGen[falcon.accountId] ? page.wsGen[falcon.accountId].hostname : "", pc_id: page.wsGen[falcon.accountId] ? page.wsGen[falcon.accountId].pc_id : (falcon.pcId || null), gen: page.wsGen[falcon.accountId] ? page.wsGen[falcon.accountId].key_generation : null, now: "Signed in now" }]
        .concat([].concat.apply([], Fleet.depts.map(function (d) { return d.admins.map(function (a) {
            var w = page.wsGen[a.account_id]
            return { id: "acct:" + a.account_id, account: a.account_id, name: a.name, role: "Admin", dept: d.name, deptId: d.id, ws: a.hostname || (w ? w.hostname : ""), pc_id: w ? w.pc_id : a.pc_id,
                     gen: w ? w.key_generation : null, now: a.session && a.session.occupied_via === "traversal" ? "Inside a machine" : a.online ? "At their desk" : "Not signed in" } }) })))
    // refused: one row per who tried and from where (registry.refused), with why and what to do (`advice`)
    readonly property var doors: refused.map(function (g) {
        return { id: g.id, host: g.host || g.address, ip: g.address, client: g.client_id || "", why: g.why, tries: g.tries, last: Time.ms(g.last), tone: g.tone,
                 say: g.say, advice: g.advice, blocked: !!g.blocked, kind: g.kind, pc_id: g.pc_id, machine: g.machine,
                 now: g.blocked ? "Blocked at the door" : g.tone === "bad" ? "Someone may have its name" : g.kind === "unknown" ? "Waiting to be registered" : g.kind === "old_key" ? "Has the old key" : "Refused" }
    })
    function block(y, on) {
        var go = function () {
            falcon.call(on ? "registry.block" : "registry.unblock", on ? { address: y.ip, reason: y.why } : { address: y.ip }, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Not changed"); return }
                Msg.ok((on ? "Blocked " : "Unblocked ") + y.ip + " · recorded"); page.load()
            })
        }
        if (on) confirm.ask({ title: "Block " + y.ip + "?", text: "Every connection from it is turned away before it can say who it is. The tries are still counted. A connection already open stays until it ends.",
                              ok: "Block it", danger: true }, go)
        else go()
    }
    function demote(a) {
        confirm.ask({ title: a.name + " stops being an Admin?", text: "They keep their account as a worker on the same machine, which gets a new key. The issues they owned go back to the department.",
                      ok: "Stop being an Admin", danger: true }, function () {
            falcon.call("hierarchy.admin_demote", { account_id: a.account }, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Not changed"); return }
                Msg.ok(a.name + " is a worker now · recorded"); page.load(); Fleet.refresh()
            })
        })
    }
    readonly property var cur: {
        var src = tab === "acct" ? accts : tab === "door" ? doors : tab === "ask" ? asks.map(function (a) { return Object.assign({ id: "ask:" + a.id }, a) }) : rows
        for (var i = 0; i < src.length; i++) if (src[i].id === sel) return src[i]
        return src.length ? src[0] : null
    }
    readonly property int off: Fleet.machines.filter(function (m) { return !m.online }).length
    readonly property var tabs: (Nav.boss ? [{ value: "door", label: "Refused · " + doors.length }]
                                           : [{ value: "pc", label: "Machines" }, { value: "acct", label: "People · " + accts.length }])
                                .concat(asks.length ? [{ value: "ask", label: "Asking to join · " + asks.length }] : [])
    onCurChanged: code = ""

    function rekey(name, pcId) {
        confirm.ask({ title: "Make a new key for " + name + "?", text: "The old key stops working at once. Whatever uses it has to be given the new one, which is shown once.",
                      ok: "Make a new key", cancel: "Keep the old one", danger: true }, function () { keys.ask({ mode: "rekey", subject: name, pc_id: pcId }) })
    }

    Confirm { id: confirm; page: page }
    KeyDrawer { id: keys; page: page; onDone: { page.load(); Fleet.refresh() } }

    // moving the Super User to a dedicated machine: allow ONE new machine to ask for ten minutes; it shows a code, which is typed below (under "Asking to join")
    Rectangle {
        objectName: "handoverCard"
        visible: Nav.boss
        width: parent.width
        height: 56
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.border
        Column {
            x: 14
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 330
            spacing: 2
            Txt { text: "Move the Super User to another machine"; font.weight: Font.Medium; width: parent.width }
            Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                  text: page.handover && page.handover.open ? "Open: one new machine may ask now" + (page.handover.waiting && page.handover.waiting.length ? " · " + Theme.many(page.handover.waiting.length, "machine") + " waiting under Asking to join" : "")
                                                              : "Closed. Opening it lets ONE new machine ask for ten minutes; nothing moves until you type the code it shows. Your account, names, tasks and history stay." }
        }
        Btn { anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter; objectName: "handoverToggle"
              kind: page.handover && page.handover.open ? "normal" : "primary"; text: page.handover && page.handover.open ? "Close it" : "Let a new machine ask"
              onClicked: page.openHandover(!(page.handover && page.handover.open)) }
    }

    PageTabs { options: Nav.boss ? [{ value: "departments", label: "Departments" }, { value: "registry", label: "Refused connections" }]
                                 : [{ value: "machines", label: "Machines" }, { value: "registry", label: "Registry" }]; current: "registry" }

    Strip {
        width: parent.width
        items: [
            { label: "Machines", value: Theme.fmt(Fleet.machines.length), delta: Theme.many(Fleet.depts.length, "department") },
            { label: "Checking in", value: Theme.fmt(Fleet.machines.length - page.off), unit: "/ " + Theme.fmt(Fleet.machines.length),
              delta: page.off ? Theme.fmt(page.off) + " not checking in" : "every one", dc: page.off ? Theme.crit : undefined },
            { label: "People", value: Theme.fmt(page.accts.length), delta: "in this department" },
            { label: "Asking to join", value: Theme.fmt(page.asks.length), delta: page.asks.length ? "type the code it shows" : "nobody", dc: page.asks.length ? Theme.med : undefined }
        ].slice(Nav.boss ? 3 : 0, Nav.boss ? 4 : 4).concat(Nav.boss ? [{ label: "Refused this week", value: Theme.fmt(page.doors.length),
              delta: page.doors.length ? Theme.fmt(page.doors.reduce(function (t, y) { return t + y.tries }, 0)) + " tries without a valid key" : "nothing tried without a key",
              dc: page.doors.some(function (y) { return y.tone === "bad" }) ? Theme.crit : undefined }] : [])
    }

    Row {
        width: parent.width
        spacing: 14
        Item {
            width: (parent.width - 14) * 8 / 12
            height: lp.height
            ListPanel {
                id: lp
                visible: page.tab === "pc"
                width: parent.width
                title: "Machines"
                sub: "each has a key made here · click one to see it on the right"
                tools: Segmented { value: page.tab; options: page.tabs; onPicked: function (v) { page.tab = v; page.sel = null } }
                placeholder: "Filter by machine, person or department"
                actionLabel: "Register a PC"
                onAction: keys.ask({ mode: "pc" })
                rows: page.rows
                pick: page.cur ? page.cur.id : null
                onPicked: function (k) { page.sel = k }
                icon: "desktop"
                nameTitle: "Machine"
                nameText: function (y) { return y.m.host }
                nameLine: function (y) { return (y.m.user || "No one signed in") + " · " + y.m.deptName }
                cols: [{ title: "Version", width: 100, text: function (y) { return y.ver || "—" } },
                       { title: "Key", width: 90, text: function (y) { return y.gen ? "no. " + y.gen : "—" } },
                       { title: "Last seen", width: 120, text: function (y) { return y.m.online ? "now" : Time.ago(y.seen) } }]
                now: function (y) { return !y.m.online ? ["Not checking in", "bad"] : y.m.behind ? ["A version behind", "wait"] : ["Checking in", "good"] }
                showEmpty: Fleet.loaded && Fleet.machines.length === 0
                emptyIcon: "desktop"; emptyTitle: "No machines yet"; emptyAct: "Register a PC"
                emptyText: "Register a PC to give it a department and a key. It shows up here and in its department."
                onEmptyAction: keys.ask({ mode: "pc" })
            }
            ListPanel {
                visible: page.tab === "acct"
                width: parent.width
                title: "Accounts"
                sub: "your department's people · click one to see it on the right"
                tools: Segmented { value: page.tab; options: page.tabs; onPicked: function (v) { page.tab = v; page.sel = null } }
                rows: page.accts
                pick: page.cur ? page.cur.id : null
                onPicked: function (k) { page.sel = k }
                icon: "user"
                nameTitle: "Account"
                nameText: function (y) { return y.name }
                nameLine: function (y) { return y.role + " · " + y.dept }
                cols: [{ title: "Workstation", width: 130, text: function (y) { return y.ws || "—" } }, { title: "Key", width: 80, text: function (y) { return y.gen ? "no. " + y.gen : "—" } }]
                now: function (y) { return [y.now, "good"] }
            }
            ListPanel {
                visible: page.tab === "door"
                width: parent.width
                title: "Refused connections"
                sub: "tried this week without a valid key · click one to see it on the right"
                tools: Segmented { value: page.tab; options: page.tabs; onPicked: function (v) { page.tab = v; page.sel = null } }
                rows: page.doors
                pick: page.cur ? page.cur.id : null
                onPicked: function (k) { page.sel = k }
                icon: "stop"
                nameTitle: "Who tried"
                nameText: function (y) { return y.host }
                nameLine: function (y) { return y.ip || y.client }
                nameMono: false
                cols: [{ title: "Refused because", width: 180, text: function (y) { return y.why.charAt(0).toUpperCase() + y.why.slice(1) } },
                       { title: "Tries", width: 70, text: function (y) { return Theme.fmt(y.tries) } },
                       { title: "Last try", width: 120, text: function (y) { return Time.atDay(y.last) } }]
                now: function (y) { return [y.now, y.tone] }
                showEmpty: page.doors.length === 0
                emptyIcon: "safety"; emptyTitle: "Nothing was refused this week"
                emptyText: "A machine that tries to connect without a valid key is turned away and shows here."
            }
            ListPanel {
                visible: page.tab === "ask"
                width: parent.width
                title: "Asking to join"
                sub: "a machine that asked for a key · type the code it shows to let it in"
                tools: Segmented { value: page.tab; options: page.tabs; onPicked: function (v) { page.tab = v; page.sel = null } }
                rows: page.asks.map(function (a) { return Object.assign({ id: "ask:" + a.id }, a) })
                pick: page.cur ? page.cur.id : null
                onPicked: function (k) { page.sel = k }
                icon: "desktop"
                nameTitle: "Machine"
                nameText: function (y) { return y.hostname }
                nameLine: function (y) { return (y.os || "") + (y.peer ? " · " + y.peer : "") }
                cols: [{ title: "Wants to be", width: 120, text: function (y) { return y.requested_level === "super_user" ? "the Super User's" : y.requested_level === "admin" ? "an Admin" : "a worker PC" } },
                       { title: "Department", width: 130, text: function (y) { return Fleet.deptName(y.requested_department_id) || "Not said" } },
                       { title: "Asked", width: 120, text: function (y) { return Time.atDay(y.created_at) } }]
                now: function (y) { return ["Waiting for you", "wait"] }
            }
        }
        SidePanel {
            width: (parent.width - 14) * 4 / 12
            showEmpty: page.cur === null
            emptyIcon: "desktop"
            emptyText: "Pick something in the list."
            title: !page.cur ? "" : page.tab === "pc" ? page.cur.m.host : page.tab === "acct" ? page.cur.name : page.tab === "door" ? page.cur.host : page.cur.hostname
            sub: page.tab === "door" ? "refused at the door" : page.tab === "ask" ? "asking to join" : page.cur && page.sel === page.cur.id ? "the one you picked" : "the first in the list · click another"
            facts: !page.cur ? []
                 : page.tab === "pc" ? [["Department", page.cur.m.deptName], ["Signed in", page.cur.m.user || "No one"], ["IP address", page.cur.ip || "—", null, true],
                                        ["Version", page.cur.ver || "—"], ["Key", page.cur.gen ? "no. " + page.cur.gen : "—"], ["Last seen", page.cur.m.online ? "now" : Time.ago(page.cur.seen)]]
                 : page.tab === "acct" ? [["Role", page.cur.role], ["Department", page.cur.dept], ["Workstation", page.cur.ws || "—", null, true], ["Key", page.cur.gen ? "no. " + page.cur.gen : "—"], ["Now", page.cur.now]]
                 : page.tab === "door" ? [["Address", page.cur.ip || "—", null, true], ["Refused because", page.cur.why.charAt(0).toUpperCase() + page.cur.why.slice(1)],
                                          ["Tries this week", Theme.fmt(page.cur.tries)], ["Last try", Time.atDay(page.cur.last)]].concat(page.cur.blocked ? [["Now", "Blocked at the door", Theme.crit]] : [])
                 : [["Wants to be", page.cur.requested_level === "super_user" ? "the Super User's machine" : page.cur.requested_level === "admin" ? "an Admin" : "a worker PC"], ["Department", Fleet.deptName(page.cur.requested_department_id) || "Not said"],
                    ["Address", page.cur.peer || "—", null, true], ["System", page.cur.os || "—"], ["Asked", Time.atDay(page.cur.created_at)], ["Expires", Time.atDay(page.cur.expires_at)]]
            Txt { visible: page.tab === "door" && page.cur !== null; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; text: page.cur && page.cur.say ? page.cur.say : "" }
            Column {
                visible: page.tab === "ask" && page.cur !== null
                width: parent.width; spacing: 6
                Txt { text: "THE CODE ON ITS SCREEN"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Field { width: parent.width; text: page.code; placeholderText: "Type the code the machine shows"; onTextEdited: page.code = text }
                Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                      text: "Only someone in front of it can see the code. Five wrong codes refuse it." }
            }
            actions: [
                // a machine
                Btn { visible: Nav.boss && page.tab === "pc" && page.cur !== null && page.cur.m && (Fleet.dept(page.cur.m.dept) || { admins: [] }).admins.length > 0; iconName: "login"
                      text: page.cur && page.cur.m && Fleet.dept(page.cur.m.dept) && Fleet.dept(page.cur.m.dept).admins.length ? "Work on it in " + Fleet.dept(page.cur.m.dept).admins[0].name + "'s console →" : ""
                      onClicked: Nav.enter(Fleet.dept(page.cur.m.dept).admins[0], ["machines", page.cur.m.host]) },
                Btn { visible: Nav.boss && page.tab === "pc" && page.cur !== null && page.cur.m && (Fleet.dept(page.cur.m.dept) || { admins: [] }).admins.length === 0; enabled: false; text: "No Admin to work on it"
                      tip: page.cur && page.cur.m ? page.cur.m.deptName + " has no Admin, so there is no console to work on it in. Appoint one first." : "" },
                Btn { visible: page.tab === "pc" && page.cur !== null; kind: "primary"; danger: true; text: "Make a new key"; onClicked: page.rekey(page.cur.m.host, page.cur.m.pc_id) },
                // an account
                Btn { visible: Nav.boss && page.tab === "acct" && page.cur !== null && page.cur.role === "Admin"; danger: true; text: "Stop being an Admin"; onClicked: page.demote(page.cur) },
                Btn { visible: page.tab === "acct" && page.cur !== null; kind: "primary"; danger: true; text: "Make a new key"; enabled: !!(page.cur && page.cur.pc_id); tip: page.cur && !page.cur.pc_id ? "No workstation on record to re-key" : ""
                      onClicked: page.rekey(page.cur.you ? "your account" : page.cur.name, page.cur.pc_id) },
                // refused
                Btn { visible: page.tab === "door" && page.cur !== null; text: page.cur && page.cur.blocked ? "Unblock this address" : "Block this address"
                      onClicked: page.block(page.cur, !page.cur.blocked) },
                Btn { visible: page.tab === "door" && page.cur !== null && page.cur.kind === "unknown"; kind: "primary"; text: "Register this PC"; onClicked: keys.ask({ mode: "pc" }) },
                Btn { visible: page.tab === "door" && page.cur !== null && page.cur.kind !== "unknown" && !!page.cur.pc_id; kind: "primary"; danger: true; text: "Make a new key"
                      onClicked: page.rekey(page.cur.machine || page.cur.host, page.cur.pc_id) },
                // asking to join
                Btn { visible: page.tab === "ask" && page.cur !== null; danger: true; text: "Refuse"
                      onClicked: falcon.call("enroll.refuse", { enrollment_id: page.cur.id, reason: "refused" }, function (ok, r) { if (ok) { Msg.ok("Refused"); page.load() } else Msg.failed(r.message || "Not refused") }) },
                Btn { visible: page.tab === "ask" && page.cur !== null; kind: "primary"; text: "Let it in"; enabled: page.code.trim().length > 0
                      onClicked: falcon.call(page.cur.requested_level === "super_user" ? "handover.confirm" : "enroll.confirm", { enrollment_id: page.cur.id, code: page.code.trim() }, function (ok, r) {
                          if (ok) { Msg.ok(page.cur.requested_level === "super_user" ? page.cur.hostname + " is the Super User's machine now · this one no longer is" : page.cur.hostname + " joined · its key went to the machine"); page.code = ""; page.load(); Fleet.refresh() } else Msg.failed(r.message || "Wrong code") }) }
            ]
        }
    }
}
