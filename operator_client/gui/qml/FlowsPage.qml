import QtQuick
import "."

// FLOWS, as the version 1 concept draws it (docs/design/concepts-admin.html, AdminFlowsPage2): are files getting where they should,
// and where is something held up? The situation in a sentence; your flows as one card per flow by what each is doing (Running,
// Waiting, Stopped, Paused last); on the right the picked flow's Controls (what waits at its gate, and one line of controls: Edit
// or whose it is on the left, the gate's action, then apart from it Pause and Stop, or Resume) and its last sync; the flow drawn
// below; Make a flow has its own page. Only an Admin-to-Admin flow needs consent: the destination Admin's, who picks the folder.
Page {
    id: page
    objectName: "flowsView"

    property var flows: []
    property string sel: { var a = Nav.takeArrive("flows"); return a !== null ? String(a) : Nav.sub && String(Nav.sub).indexOf("edit-") !== 0 && Nav.sub !== "new" ? String(Nav.sub) : "" }
    property string exp: ""
    property var rAsks: []                // restricted files a held flow met, that this person may allow
    property var runs: ({})               // each flow's flow.runs: its last sync as a diff
    property var kept: ({})               // quiet flows kept this visit
    property string askPath: ""           // the folder picked for an ask
    property var gsel: ({})               // which of several things at one gate is shown
    property var gpick: ({})              // which of a gate's choices is picked
    property bool loading: false

    function load() {
        falcon.call("flow.list", {}, function (ok, r) {
            page.flows = ok ? (r.flows || []) : []
            page.flows.forEach(function (f) {
                falcon.call("flow.runs", { flow_id: f.id }, function (ok2, r2) { if (ok2) { var x = Object.assign({}, page.runs); x[f.id] = r2; page.runs = x } })
            })
            var held = page.flows.filter(function (f) { return f.pause_reason === "restricted:consent" })
            var found = [], left = held.length
            if (!left) { page.rAsks = []; return }
            held.forEach(function (f) {
                falcon.call("flow.restricted", { flow_id: f.id }, function (ok2, r2) {
                    if (ok2 && r2) (r2.consents || []).forEach(function (c) { if (c.state === "asked" && (r2.can_decide || []).indexOf(c.id) >= 0) found.push(Object.assign({ flow: f }, c)) })
                    if (--left === 0) page.rAsks = found
                })
            })
        })
    }
    Component.onCompleted: load()
    Connections { target: falcon; function onPushReceived(type) { if (/^flow/.test(type)) again.restart() } }
    Timer { id: again; interval: 300; onTriggered: page.load() }

    function folder(p) { var x = String(p || "").replace(/[\\\/]+$/, "").split(/[\\\/]/); return x[x.length - 1] || p }
    function mine(f) { return f.created_by_account_id === falcon.accountId }
    function who(f) { return mine(f) ? "you" : f.created_by_name || Fleet.adminName(f.created_by_account_id) || "another Admin" }
    function nameOf(f) { return f.name || folder(f.source_path) + "-" + f.id }
    function lastCopy(f) {
        var m = null
        ;(f.destinations || []).forEach(function (d) { var t = d.last_sync ? Time.ms(d.last_sync.synced_at) : null; if (t && (!m || t > m)) m = t })
        return m
    }
    function askedOfMe(f) { return f.consent_status === "pending" && (f.destinations || []).some(function (d) { return d.owner_account_id === falcon.accountId }) }
    function hours(x) { return x ? (Time.now - Time.ms(x)) / 3600000 : 0 }
    function asked(f) { return Time.sameDay(Time.ms(f.created_at), Time.now) ? "today " + Time.hhmm(f.created_at) : Time.dayName(f.created_at).toLowerCase() + " " + Time.hhmm(f.created_at) }
    // the Admin at a workstation: their name, and whether it is on
    function adminAt(pc) {
        for (var i = 0; i < Fleet.depts.length; i++)
            for (var k = 0; k < (Fleet.depts[i].admins || []).length; k++)
                if (Fleet.depts[i].admins[k].pc_id === pc) return Fleet.depts[i].admins[k]
        return null
    }
    function picker(f) { var d = (f.destinations || [])[0], a = d ? page.adminAt(d.destination_pc_id) : null; return a ? a.name : "an Admin" }
    function place(d) { return (d.destination_hostname || "storage") + " " + (d.destination_path || "") }
    function gone(f) { return (f.sources || []).filter(function (s) { return !!s.pause_reason })[0] || null }
    function offDest(f) { return (f.destinations || []).filter(function (d) { var a = page.adminAt(d.destination_pc_id); return !d.let_them_choose && a !== null && a.online === false })[0] || null }
    function today(f) { return f.files_copied ? f.files_copied.today || 0 : 0 }
    function stateOf(f) {
        if (f.status === "inactive") return "stopped"
        if (f.consent_status === "pending") return "waiting"
        if (f.status === "paused" || f.pause_reason || page.gone(f) || (f.destinations || []).some(function (d) { return !!d.paused_reason })) return "paused"
        if (page.offDest(f)) return "waiting"
        return "running"
    }
    // what waits at a flow's gate, as the concept lists them: each with its kind, a line, where, how long, and its choices ([label, fn, enabled, why])
    function gatesOf(f) {
        var out = [], name = page.nameOf(f)
        page.rAsks.filter(function (c) { return c.flow.id === f.id }).forEach(function (c) {
            out.push({ id: "r" + c.id, hot: true, kind: "Restricted", icon: "stop", title: name + " met " + page.folder(c.sample_path), where: String(c.sample_path).replace(/[^\/\\]+$/, ""), line: "you restricted it; the flow waits for you", wait: page.hours(c.asked_at),
                       acts: [["Allow it for this flow", function () { page.consentR(c, true) }, true, ""], ["Keep it paused", function () { page.consentR(c, false) }, true, ""]] })
        })
        if (f.pause_reason === "restricted:consent" && !out.length)
            out.push({ id: "rw" + f.id, kind: "Restricted, someone else's", icon: "stop", title: name + " met a restricted file", where: f.source_hostname + " " + f.source_path, line: "it waits for the Admin who marked it to say yes", wait: 0, acts: [] })
        if (f.pause_reason && f.pause_reason !== "restricted:consent" && f.consent_status !== "pending")
            out.push({ id: "p" + f.id, hot: true, kind: f.pause_reason.indexOf("destination") === 0 ? "A destination is gone" : f.pause_reason.indexOf("source") === 0 ? "A source is gone" : "Held by Falcon",
                       icon: "disconnect", title: name + (f.pause_reason.indexOf("destination") === 0 ? " cannot reach where it lands" : f.pause_reason.indexOf("source") === 0 ? " cannot read where it starts" : " stopped"), where: f.source_hostname + " " + f.source_path, wait: 0,
                       line: f.suggestion || "nothing more goes through until it is fixed",
                       acts: [["Try it again", function () { page.call("flow.resume", { flow_id: f.id }, "Trying it again") }, true, ""],
                              ["Pick another folder", function () { Nav.go("flows", "edit-" + f.id) }, true, ""]] })
        ;(f.destinations || []).filter(function (d) { return !!d.paused_reason }).forEach(function (d) {
            out.push({ id: "d" + d.id, hot: true, kind: "A destination stopped", icon: "disconnect", title: name + " cannot reach " + page.place(d), where: "files wait in line until it takes them", line: "the folder stopped taking files", wait: 0.3,
                       acts: [["Try it again", function () { page.call("flow.resume", { flow_id: f.id, destination_id: d.id }, "Trying it again") }, true, ""]] })
        })
        var run = page.runs[f.id], beside = run && run.last ? (run.last.items || []).filter(function (i) { return i.outcome === "kept_beside" })[0] : null
        if (beside) {
            var nm = page.folder(beside.path), mod = nm.replace(/(\.[^.]+)?$/, "-modified$1")
            out.push({ id: "k" + f.id, kind: "Kept beside", icon: "copy", title: nm + " was changed where it landed", where: page.place((f.destinations || [])[0] || {}), line: "the flow kept both: " + mod + " beside the new one", wait: page.hours(run.last.ended_at),
                       acts: [["Keep the new one", function () { page.call("flow.keep", { flow_id: f.id, path: beside.path, keep: "new" }, "Kept the new one; the other is in the audit log") }, true, ""],
                              ["Keep both", function () { page.call("flow.keep", { flow_id: f.id, path: beside.path, keep: "both" }, "Both kept") }, true, ""]] })
        }
        if (f.consent_status === "pending") {
            if (page.askedOfMe(f)) out.push({ id: "a" + f.id, ask: true, kind: "Wants to send you files", icon: "inbox", title: page.who(f) + ": " + name, where: f.source_hostname + " " + f.source_path + (Sync.steps(f).length ? " · " + Sync.steps(f).map(function (s) { return s.op }).join(", ") : ""), line: "", wait: page.hours(f.created_at),
                                              acts: [["Pick a folder", function () { page.call("flow.consent", { flow_id: f.id, granted: true, destination_path: page.askPath }, "Accepted · it starts copying") }, true, ""],
                                                     ["Decline", function () { page.call("flow.consent", { flow_id: f.id, granted: false }, "Declined · they are told") }, true, ""]] })
            else {
                var remind = function () { page.call("flow.remind", { flow_id: f.id }, "Reminded " + page.picker(f)) }
                var long = !Time.sameDay(Time.ms(f.created_at), Time.now)
                out.push(long ? { id: "w" + f.id, hot: true, kind: "Waited too long", icon: "clock", title: name + " still waits for " + page.picker(f), where: "asked " + page.asked(f) + "; no folder picked", line: "remind them once more, send it somewhere else, or take the ask back", wait: page.hours(f.created_at),
                                  acts: [["Remind", remind, true, ""], ["Pick another destination", function () { Nav.go("flows", "edit-" + f.id) }, true, ""], ["Withdraw the ask", function () { page.call("flow.delete", { flow_id: f.id }, "Ask withdrawn; " + name + " is stopped") }, true, ""]] }
                              : { id: "w" + f.id, kind: "Waiting on someone else", icon: "clock", title: name + " waits for " + page.picker(f), where: "to pick a folder, asked " + page.asked(f), line: "nothing moves until they do", wait: page.hours(f.created_at),
                                  acts: [["Remind", remind, true, ""]] })
            }
        }
        var g = page.gone(f)
        if (g) out.push({ id: "g" + f.id, hot: true, kind: "A source is gone", icon: "folderopen", title: g.source_hostname + " " + g.source_path + " is not there any more", where: name + " reads from it", line: "it was moved or renamed; the flow's other sources still go", wait: page.hours(g.paused_at),
                          acts: [["Pick another folder", function () { Nav.go("flows", "edit-" + f.id) }, true, ""],
                                 ["Wait for it", function () { Msg.ok("Waiting; you are told when it is back") }, true, ""],
                                 ["Stop the flow", function () { page.call("flow.delete", { flow_id: f.id }, "Stopped · its history is kept") }, true, ""]] })
        var q = f.files_copied && f.files_copied.last_at ? page.hours(f.files_copied.last_at) / 24 : 0
        if (q >= 14 && !page.kept[f.id])
            out.push({ id: "q" + f.id, kind: "Quiet for a long time", icon: "pausecircle", title: name + " has moved nothing in " + Math.round(q) + " days", where: (f.sources || []).map(function (s) { return s.source_hostname + " " + s.source_path }).join(", "), line: "a suggestion only; nothing stops by itself", wait: q * 24,
                       acts: [["Keep it", function () { var k = Object.assign({}, page.kept); k[f.id] = true; page.kept = k; Msg.ok(name + " kept") }, true, ""],
                              ["Stop it", function () { page.call("flow.delete", { flow_id: f.id }, "Stopped · its history is kept") }, true, ""]] })
        var off = page.offDest(f)
        if (off) { var ad = page.adminAt(off.destination_pc_id)
            out.push({ id: "o" + f.id, kind: "A destination is off", icon: "disconnect", title: off.destination_hostname + " has been off since " + Time.hhmm(ad.last_seen_at), where: name + " · files wait for it", line: "it goes when the machine is back; " + (page.mine(f) ? "you" : page.who(f)) + " made this flow", wait: page.hours(ad.last_seen_at),
                       acts: [["Keep waiting", function () { Msg.ok("Keeps waiting") }, true, ""]] }) }
        return out.sort(function (x, y) { return (y.hot ? 1 : 0) - (x.hot ? 1 : 0) || y.wait - x.wait })
    }
    function call(type, payload, ok) {
        falcon.call(type, payload, function (good, r) {
            if (!good) { Msg.failed(r && r.message ? r.message : "Not done"); return }
            Msg.ok(ok); page.load()
        })
    }
    function consentR(c, grant) { call("flow.restricted_consent", { consent_id: c.id, grant: grant }, grant ? "Allowed for this flow · its destinations become places it may be" : "It stays paused") }

    readonly property var groupsDef: [["running", "Running", "moving files, or set up and ready"], ["waiting", "Waiting", "on someone else: a folder to be picked, a machine to come back, or an ask to you"],
                                      ["stopped", "Stopped", "stopped by you; nothing goes through until you start it again"], ["paused", "Paused", "held for you, or paused by you; nothing more goes through until you act"]]
    readonly property var rows: flows.map(function (f) { return Object.assign({ key: String(f.id), name: page.nameOf(f), st: page.stateOf(f) }, f) })
    // the hot first, then what has waited longest
    function inGroup(k) { return rows.filter(function (r) { return r.st === k }).sort(function (a, b) {
        var ga = page.gatesOf(a)[0], gb = page.gatesOf(b)[0]
        return (gb && gb.hot ? 1 : 0) - (ga && ga.hot ? 1 : 0) || (gb ? gb.wait : 0) - (ga ? ga.wait : 0) }) }
    readonly property var mineList: rows.filter(function (r) { return !page.askedOfMe(r) })
    readonly property var cur: {
        for (var i = 0; i < rows.length; i++) if (rows[i].key === sel) return rows[i]
        return inGroup("paused")[0] || inGroup("waiting")[0] || inGroup("running")[0] || null
    }
    property string pickedKey: ""
    onCurChanged: {
        pickedKey = cur ? cur.key : ""; loading = true; ldT.restart(); askPath = ""
    }
    Timer { id: ldT; interval: Theme.loadMs; onTriggered: page.loading = false }
    readonly property var steps: Sync.steps(cur)
    readonly property var gates: cur ? gatesOf(cur) : []
    readonly property int gi: cur ? Math.min(gsel[cur.key] || 0, Math.max(0, gates.length - 1)) : 0
    readonly property var g0: gates.length ? gates[gi] : null
    function shape(f) {
        var n = (f.destinations || []).length, s = Sync.steps(f).length
        return Theme.many((f.sources || [1]).length, "source") + " → " + (s ? Theme.many(s, "step") + " → " : "") + Theme.many(n, "destination")
    }
    function strip(g, f) { var n = page.nameOf(f) + " "; return g.title.indexOf(n) === 0 ? g.title.slice(n.length) : g.title }
    function why(f) { var l = page.lastCopy(f); return f.status === "inactive" ? "stopped" : l ? "last copy " + Time.at(l) : "nothing yet" }

    situation: {
        if (!flows.length) return "You have no flows yet."
        var xs = mineList, moving = xs.filter(function (r) { return page.today(r) > 0 && r.pause_reason !== "restricted:consent" && !(r.destinations || []).some(function (d) { return !!d.paused_reason }) }).length
        var H = xs.filter(function (r) { return r.pause_reason === "restricted:consent" }).map(function (r) { return r.name })
        var B = xs.filter(function (r) { return (r.destinations || []).some(function (d) { return !!d.paused_reason }) }).map(function (r) { return r.name })
        var W = xs.filter(function (r) { return r.consent_status === "pending" }).length
        var sum = xs.reduce(function (n, r) { return n + page.today(r) }, 0)
        return Theme.fmt(moving) + " of " + Theme.fmt(xs.length) + " flows moved files today; " + (H.length ? Theme.listNames(H, 2) + " is held for you" : "nothing is held for you")
               + (B.length ? ", " + Theme.listNames(B, 2) + " has a destination stopped" : "") + (W ? ", " + Theme.fmt(W) + " wait" + (W === 1 ? "s" : "") + " for a folder" : "") + ". " + Theme.fmt(sum) + " files went through today."
    }
    situationAt: Time.now

    Confirm { id: confirm; page: page }

    Row {
        width: parent.width
        spacing: 14
        // --- your flows (stretched to the column beside it) ----------------------------------------------------
        Box {
            id: listP
            objectName: "flowCards"
            width: (parent.width - 14) * 8 / 12
            height: Math.max(implicitHeight, rightCol.implicitHeight)
            title: "The flows · " + page.mineList.length
            sub: "by what each is doing, paused last; click one and its controls, last sync and drawing follow; expand it for its facts"
            Repeater {
                model: page.groupsDef
                delegate: Group {
                    id: grp
                    required property var modelData
                    required property int index
                    readonly property var xs: page.inGroup(modelData[0])
                    visible: xs.length > 0
                    spaced: page.groupsDef.slice(0, index).some(function (g) { return page.inGroup(g[0]).length > 0 })
                    width: listP.innerW
                    late: modelData[0] === "paused"
                    cardGap: 5
                    title: modelData[1] + " · " + xs.length
                    sub: modelData[2]
                    Repeater {
                        model: grp.xs
                        delegate: Card {
                            id: fc
                            required property var modelData
                            readonly property var gs: page.gatesOf(modelData)
                            readonly property bool urg: gs.length > 0 && !!gs[0].hot
                            objectName: "flow_" + modelData.id
                            width: grp.cardW
                            midW: 110
                            actW: 104
                            padV: 7
                            readonly property bool ask: page.askedOfMe(modelData)
                            icon: ask ? "inbox" : "branches"
                            hot: urg
                            tint: grp.late
                            title: ask ? gs[0].title : modelData.name
                            tag: ask ? "" : "by " + page.who(modelData)
                            line: ask ? gs[0].kind.toLowerCase() : gs.length ? page.strip(gs[0], modelData) + (gs.length > 1 ? " · and " + (gs.length - 1) + " more" : "") : page.shape(modelData) + " · " + page.why(modelData)
                            lineHot: urg
                            picked: page.cur !== null && page.cur.key === modelData.key
                            expandable: true
                            expanded: page.exp === modelData.key
                            onOpen: page.sel = modelData.key
                            onToggle: { page.sel = modelData.key; page.exp = expanded ? "" : modelData.key }
                            mid: Txt {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone
                                text: fc.ask ? Time.waitLen(fc.gs[0].wait) + " ago" : Theme.fmt(page.today(fc.modelData)) + " today"
                            }
                            // opened: its facts beside what waits at its gate (am-in)
                            Row {
                                width: parent.width
                                spacing: 24
                                Column {
                                    y: 2
                                    width: Math.min(420, parent.width - 230 - 24)
                                    Repeater {
                                        model: [["From", (fc.modelData.sources || []).map(function (s) { return s.source_hostname + " " + s.source_path }).join(", ")],
                                                ["To", (fc.modelData.destinations || []).map(function (d) { return (d.destination_hostname || "storage") + " " + (d.destination_path || "(they pick the folder)") }).join(", ")],
                                                ["Along the way", Sync.steps(fc.modelData).map(function (s, i) { return (i + 1) + ". " + s.op }).join("  ") || "copied as it is"],
                                                ["Made by", page.who(fc.modelData)], ["Since it began", Theme.fmt(fc.modelData.files_copied ? fc.modelData.files_copied.total : 0) + " files"]]
                                        delegate: Item {
                                            required property var modelData
                                            required property int index
                                            width: parent.width
                                            height: fv.height + 10
                                            Txt { y: 5; width: 120; text: modelData[0]; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                                            Txt { id: fv; x: 132; y: 5; width: parent.width - 132; text: modelData[1]; font.pixelSize: 13; mono: index < 2; wrapMode: Text.WrapAnywhere; elide: Text.ElideNone }
                                            Rectangle { visible: index < 4; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                                        }
                                    }
                                }
                                Column {
                                    width: 230
                                    spacing: 6
                                    Txt { topPadding: 4; text: "At the gate"; color: Theme.text3; font.pixelSize: 12 }
                                    Repeater {
                                        model: fc.gs
                                        delegate: Column {
                                            required property var modelData
                                            width: 230
                                            spacing: 2
                                            Row { spacing: 6
                                                  Rectangle { width: 7; height: 7; radius: 3.5; anchors.verticalCenter: parent.verticalCenter; color: modelData.hot ? Theme.crit : Theme.text4 }
                                                  Txt { text: modelData.kind; font.pixelSize: 13; color: modelData.hot ? Theme.crit : Theme.text; elide: Text.ElideNone } }
                                            Txt { width: 230; text: modelData.where + "; waiting " + Time.waitLen(modelData.wait); color: Theme.text3; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                                        }
                                    }
                                    Row { visible: fc.gs.length === 0; spacing: 6
                                          Rectangle { width: 7; height: 7; radius: 3.5; anchors.verticalCenter: parent.verticalCenter; color: Theme.ok }
                                          Txt { text: "nothing waits; it runs by itself"; font.pixelSize: 13; elide: Text.ElideNone } }
                                    Item { width: 1; height: 4 }
                                    Txt { text: "Today"; color: Theme.text3; font.pixelSize: 12 }
                                    Repeater {
                                        model: [["Files through it", Theme.fmt(page.today(fc.modelData))], ["Last copy", page.lastCopy(fc.modelData) ? Time.at(page.lastCopy(fc.modelData)) : "none yet"]]
                                        delegate: Item {
                                            required property var modelData
                                            required property int index
                                            width: 230; height: 27.75
                                            Txt { y: 4; text: modelData[0]; font.pixelSize: 13; elide: Text.ElideNone }
                                            Txt { y: 4; anchors.right: parent.right; text: modelData[1]; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                                            Rectangle { visible: index === 0; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            Quiet { visible: page.flows.length === 0; text: "No flows yet. Make one below." }
        }

        // --- controls, and the last sync ----------------------------------------------------------------------
        Column {
            id: rightCol
            width: (parent.width - 14) * 4 / 12
            spacing: 14
            Box {
                id: ctlP
                objectName: "flowControls"
                width: parent.width
                title: "Controls"
                sub: page.cur && page.askedOfMe(page.cur) ? "an ask to send you files" : page.cur ? page.cur.name + ": what waits at its gate, and what you can do with it" : "pick a flow on the left"
                // several at one gate: one at a time, so the line always carries one action
                Item {
                    visible: page.gates.length > 1
                    width: parent.width
                    height: 22
                    Txt { anchors.verticalCenter: parent.verticalCenter; text: Theme.many(page.gates.length, "thing") + " wait at its gate"; color: Theme.text3; font.pixelSize: 12 }
                    StepPager { anchors.right: parent.right; y: -6; width: 120; showCount: false; total: 0; pageNo: page.gi; pages: page.gates.length
                                onStep: function (d) { var g = Object.assign({}, page.gsel); g[page.cur.key] = page.gi + d; page.gsel = g } }
                }
                // the gate (fl-gate): its kind and how long it has waited, what it is, and its choices
                Rectangle {
                    visible: page.g0 !== null
                    width: parent.width
                    height: gateC.height + 12
                    radius: Theme.radiusLg
                    color: Theme.surface2
                    Column {
                        id: gateC
                        x: 12
                        width: parent.width - 24
                        spacing: 6
                        Item {
                            width: parent.width
                            height: gk.height
                            Row { id: gk; spacing: 5
                                  Icon { name: page.g0 ? page.g0.icon : "clock"; size: 12; color: page.g0 && page.g0.hot ? Theme.crit : Theme.text2; anchors.verticalCenter: parent.verticalCenter }
                                  Txt { text: page.g0 ? page.g0.kind : ""; color: page.g0 && page.g0.hot ? Theme.crit : Theme.text2; font.pixelSize: 12; elide: Text.ElideNone } }
                            Txt { anchors.right: parent.right; text: page.g0 && page.g0.wait ? "waiting " + Time.waitLen(page.g0.wait) : ""; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                        }
                        Txt { width: parent.width; text: page.g0 ? page.g0.title : ""; font.pixelSize: 14; font.weight: Font.DemiBold; lh: 1.35; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                        Txt { visible: text !== ""; width: parent.width; text: page.g0 ? page.g0.line : ""; color: Theme.text2; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                        Field { visible: page.g0 !== null && !!page.g0.ask && (page.gpick[page.g0.id] || 0) === 0; width: parent.width; placeholderText: "The folder on your workstation"; text: page.askPath; onTextEdited: page.askPath = text }
                        Column {
                            visible: page.g0 !== null && page.g0.acts.length > 1
                            width: parent.width
                            spacing: 6
                            Item { width: parent.width; height: wt.height + 12; Txt { id: wt; y: 10; text: "What to do"; font.pixelSize: 12; font.weight: Font.DemiBold; color: Theme.text2; elide: Text.ElideNone } }
                            Repeater {
                                model: page.g0 && page.g0.acts.length > 1 ? page.g0.acts : []
                                delegate: Opt {
                                    required property var modelData
                                    required property int index
                                    on: (page.gpick[page.g0.id] || 0) === index
                                    title: modelData[0]
                                    onClicked: { var p = Object.assign({}, page.gpick); p[page.g0.id] = index; page.gpick = p }
                                }
                            }
                        }
                    }
                }
                Quiet { visible: page.cur !== null && page.gates.length === 0 && page.cur.st !== "stopped"; icon: page.cur && page.cur.status === "paused" && !page.cur.pause_reason ? "pausecircle" : "check"
                        text: page.cur ? (page.cur.status === "paused" && !page.cur.pause_reason ? "You paused " + page.cur.name + ". Nothing goes through until you resume it." : "Nothing waits at a gate; " + page.cur.name + " runs by itself.") : "" }
                Quiet { visible: page.cur !== null && page.cur.st === "stopped"; icon: "stop"; text: page.cur ? "You stopped " + page.cur.name + ". Nothing goes through." : "" }
                Quiet { visible: page.cur === null; text: "Pick a flow on the left." }
                // the controls' line, the same in every case (fl-acts: under a rule)
                Column {
                    visible: page.cur !== null
                    width: parent.width
                    spacing: 12
                    Rectangle { width: parent.width; height: 1; color: Theme.border }
                    Item {
                        width: parent.width
                        height: 24
                        Btn { visible: page.cur !== null; anchors.verticalCenter: parent.verticalCenter; small: true; iconName: "edit"; text: "Edit"; onClicked: Nav.go("flows", "edit-" + page.cur.id) }
                        Row {
                            id: ctlRow
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 18
                            readonly property var act: page.g0 && page.g0.acts.length ? page.g0.acts[page.gpick[page.g0.id] || 0] : null
                            Btn { visible: ctlRow.act !== null; small: true; kind: "primary"; text: ctlRow.act ? ctlRow.act[0] : ""; enabled: ctlRow.act !== null && ctlRow.act[2] && !(page.g0 && page.g0.ask && (page.gpick[page.g0.id] || 0) === 0 && page.askPath.trim() === "")
                                  tip: ctlRow.act && !ctlRow.act[2] ? ctlRow.act[3] : ""; onClicked: if (ctlRow.act[1]) ctlRow.act[1]() }
                            Row {
                                visible: page.cur !== null
                                spacing: 6
                                readonly property bool held: page.cur !== null && (page.cur.st === "paused" || page.cur.st === "stopped")
                                Btn { visible: parent.held; small: true; kind: "primary"; iconName: "caretr"; text: page.cur && page.cur.st === "stopped" ? "Start again" : "Resume"
                                      onClicked: page.cur.st === "stopped" ? page.call("flow.start", { flow_id: page.cur.id }, "Started again; it catches up on what it missed") : page.call("flow.resume", { flow_id: page.cur.id }, "Resumed · it carries on, and keeps what was held") }
                                Btn { visible: !parent.held; small: true; iconName: "pausecircle"; text: "Pause"; onClicked: page.call("flow.pause", { flow_id: page.cur.id }, "Paused · nothing is lost") }
                                Btn { visible: !parent.held; small: true; danger: true; iconName: "stop"; text: "Stop"
                                      onClicked: confirm.ask({ title: "Stop " + page.cur.name + "?", text: "Nothing goes through it any more. What it copied stays where it is, and its history is kept.", ok: "Stop it", danger: true },
                                                             function () { page.call("flow.delete", { flow_id: page.cur.id }, "Stopped · its history is kept") }) }
                            }
                        }
                    }
                }
                Pulse { parent: ctlP; key: page.loading ? null : page.pickedKey || null }
            }
            Box {
                id: syncP
                objectName: "flowLastSync"
                width: parent.width
                title: "Last sync"
                sub: page.cur && page.askedOfMe(page.cur) ? "an ask has not synced anything" : page.cur ? page.cur.name : "pick a flow on the left"
                readonly property var run: page.cur ? page.runs[page.cur.id] || null : null
                readonly property var last: run && run.last ? run.last : null
                function when(x) { var d = Math.round((new Date(Time.now).setHours(0, 0, 0, 0) - new Date(Time.ms(x)).setHours(0, 0, 0, 0)) / 86400000)
                                   return (d === 0 ? "" : d === 1 ? "yesterday " : Time.dayName(x) + " ") + Time.hhmm(x) }
                function kb(n) { n = Math.abs(n) / 1000; return n >= 1000 ? (n / 1000).toFixed(1) + " MB" : Math.round(n) + " KB" }
                readonly property var items: last ? last.items || [] : []
                readonly property int arrived: items.filter(function (i) { return i.outcome === "new" }).length
                readonly property int updated: items.filter(function (i) { return i.outcome === "changed" || i.outcome === "kept_beside" }).length
                readonly property int held: run ? (run.waiting || []).length : 0
                readonly property real added: items.reduce(function (n, i) { return n + (i.bytes_after || 0) - (i.bytes_before || 0) }, 0)
                Rectangle {
                    width: parent.width
                    height: sc.height + 20
                    radius: Theme.radiusLg
                    color: Theme.surface2
                    Column {
                        id: sc
                        x: 12; y: 10
                        width: parent.width - 24
                        spacing: 6
                        Txt { visible: syncP.last === null || page.loading; width: parent.width; color: Theme.text3; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone
                              text: !page.cur ? "Pick a flow on the left." : page.loading ? "Loading " + page.cur.name : page.askedOfMe(page.cur) ? "Nothing goes through until you pick a folder for it."
                                    : page.cur.consent_status === "pending" ? "Not synced yet. It starts once " + page.picker(page.cur) + " picks a folder." : "Not synced yet." }
                        Txt { visible: syncP.last !== null && !page.loading; width: parent.width; textFormat: Text.StyledText; elide: Text.ElideNone
                              text: syncP.last ? "<span style='font-size:16px;font-weight:600'>" + syncP.when(syncP.last.ended_at) + "</span>"
                                    + (syncP.run.earlier && syncP.run.earlier.length ? "<font color='" + Theme.text3 + "'> · the one before was " + syncP.when(syncP.run.earlier[0].ended_at) + "</font>" : "") : "" }
                        Txt { visible: syncP.last !== null && !page.loading; width: parent.width; textFormat: Text.StyledText; elide: Text.ElideNone
                              text: (syncP.arrived ? "<font color='" + Theme.ok + "'><b>" + syncP.arrived + "</b></font> arrived &nbsp;&nbsp; " : "") + (syncP.updated ? "<b>" + syncP.updated + "</b> updated &nbsp;&nbsp; " : "")
                                    + (syncP.held ? "<font color='" + Theme.med + "'><b>" + syncP.held + "</b></font> did not go &nbsp;&nbsp; " : "")
                                    + (syncP.added ? "<font color='" + Theme.text3 + "'>" + (syncP.added > 0 ? "+" : "−") + syncP.kb(syncP.added) + " in all</font>" : "") }
                    }
                }
                Pulse { parent: syncP; key: page.loading ? null : page.pickedKey || null }
            }
        }
    }

    // --- the picked flow, drawn ---------------------------------------------------------------------------
    Box {
        id: drawP
        objectName: "flowDrawn"
        width: parent.width
        title: page.cur ? page.cur.name : "The picked flow"
        sub: page.cur ? "drawn from its own sources, steps and destinations · " + page.shape(page.cur) : "pick a flow above to draw it here"
        FlowGraph {
            visible: page.cur !== null
            width: parent.width
            wait: page.cur !== null && page.cur.consent_status === "pending"
            srcs: page.cur ? (page.cur.sources || []).map(function (s) { return { host: s.source_hostname, path: s.source_path, gone: !!s.pause_reason } }) : []
            stages: page.steps
            dests: page.cur ? (page.cur.destinations || []).map(function (d) {
                return { host: d.destination_hostname || "storage", path: d.destination_path, ask: page.cur.consent_status === "pending", bad: !!d.paused_reason } }) : []
        }
        Txt {
            readonly property var notes: !page.cur ? [] : [page.cur.pause_reason === "restricted:consent" ? "red outline: held for your consent at that source" : "",
                                                          (page.cur.destinations || []).some(function (d) { return !!d.paused_reason }) ? "dashed red: a destination that stopped taking files" : "",
                                                          page.cur.consent_status === "pending" ? "dashed grey: waiting for an Admin to pick a folder" : ""].filter(function (x) { return x })
            visible: notes.length > 0
            width: parent.width; text: notes.join(" · "); color: Theme.text3; font.pixelSize: 12
        }
        Rectangle {
            visible: page.cur === null
            width: parent.width; height: 110; radius: Theme.radiusLg
            color: "transparent"; border.width: 1.5; border.color: Theme.border
            Row { anchors.centerIn: parent; spacing: 8
                  Icon { name: "branches"; size: 13; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                  Txt { text: "Nothing picked"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone } }
        }
        Pulse { parent: drawP; key: page.loading ? null : page.pickedKey || null }
    }

    // --- make a flow: a few careful steps, so it has its own page ---------------------------------------------
    Box {
        objectName: "makeFlow"
        width: parent.width
        accentFoot: true
        title: "Make a flow"
        sub: "files go one way only; nothing restricted rides along without an Admin's say"
        GiveSteps {
            steps: [["Pick where files start", "one or more folders on your machines, or ones a flow already fills"], ["Say what happens on the way", "convert, compress, rename or sort, in order; or copy them as they are"], ["Pick where they land", "folders you manage; anyone else's is asked first"]]
            act: "Make a flow"
            onGo: Nav.go("flows", "new")
        }
    }
}
