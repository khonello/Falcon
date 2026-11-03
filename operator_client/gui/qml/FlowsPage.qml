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
    property var log: []
    property var rAsks: []                // restricted files a held flow met, that this person may allow
    property var gsel: ({})               // which of several things at one gate is shown
    property var gpick: ({})              // which of a gate's choices is picked
    property bool loading: false

    function load() {
        falcon.call("flow.list", {}, function (ok, r) {
            page.flows = ok ? (r.flows || []) : []
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
    function stateOf(f) {
        if (f.status === "inactive") return "stopped"
        if (f.consent_status === "pending") return "waiting"
        if (f.status === "paused" || f.pause_reason || (f.destinations || []).some(function (d) { return !!d.paused_reason })) return "paused"
        return "running"
    }
    // what waits at a flow's gate: each with its kind, a line, and its choices ([label, fn, enabled, why])
    function gatesOf(f) {
        var out = []
        page.rAsks.filter(function (c) { return c.flow.id === f.id }).forEach(function (c) {
            out.push({ id: "r" + c.id, hot: true, kind: "Restricted, yours", icon: "stop", title: page.nameOf(f) + " met " + page.folder(c.sample_path), line: "you restricted it; the flow waits for you", at: c.asked_at,
                       acts: [["Allow it for this flow", function () { page.consentR(c, true) }, true, ""], ["Keep it paused", function () { page.consentR(c, false) }, true, ""]] })
        })
        if (f.pause_reason === "restricted:consent" && !out.length)
            out.push({ id: "rw" + f.id, kind: "Restricted, someone else's", icon: "stop", title: page.nameOf(f) + " met a restricted file", line: "it waits for the Admin who marked it to say yes", acts: [] })
        if (f.pause_reason && f.pause_reason !== "restricted:consent" && f.consent_status !== "pending")
            out.push({ id: "p" + f.id, hot: true, kind: f.pause_reason.indexOf("destination") === 0 ? "A destination is gone" : f.pause_reason.indexOf("source") === 0 ? "A source is gone" : "Held by Falcon",
                       icon: "disconnect", title: page.nameOf(f) + (f.pause_reason.indexOf("destination") === 0 ? " cannot reach where it lands" : f.pause_reason.indexOf("source") === 0 ? " cannot read where it starts" : " stopped by itself"),
                       line: f.suggestion || "nothing more goes through until it is fixed",
                       acts: [["Try it again", function () { page.call("flow.resume", { flow_id: f.id }, "Trying it again") }, page.mine(f), "Only " + page.who(f) + " can do this"],
                              ["Pick another folder", function () { Nav.go("flows", "edit-" + f.id) }, page.mine(f), "Only " + page.who(f) + " can change it"]] })
        ;(f.destinations || []).filter(function (d) { return !!d.paused_reason }).forEach(function (d) {
            out.push({ id: "d" + d.id, hot: true, kind: "A destination stopped", icon: "disconnect", title: (d.destination_hostname || "storage") + " stopped taking files", line: f.suggestion || "files wait in line until it takes them",
                       acts: [["Try it again", function () { page.call("flow.resume", { flow_id: f.id, destination_id: d.id }, "Trying it again") }, page.mine(f), "Only " + page.who(f) + " can do this"]] })
        })
        if (f.consent_status === "pending") {
            if (page.askedOfMe(f)) out.push({ id: "a" + f.id, kind: "Wants to send you files", icon: "inbox", title: page.who(f) + ": " + page.nameOf(f), line: f.source_hostname + " " + f.source_path,
                                              acts: [["Accept", function () { page.call("flow.consent", { flow_id: f.id, granted: true }, "Accepted · it starts copying") }, true, ""],
                                                     ["Decline", function () { page.call("flow.consent", { flow_id: f.id, granted: false }, "Declined · they are told") }, true, ""]] })
            else out.push({ id: "w" + f.id, kind: "Waiting on someone else", icon: "clock", title: page.nameOf(f) + " waits for an Admin", line: "to pick a folder and agree; nothing moves until they do",
                            acts: [["Remind", null, false, "The Engine cannot send a reminder yet"]] })
        }
        return out
    }
    function call(type, payload, ok) {
        falcon.call(type, payload, function (good, r) {
            if (!good) { Msg.failed(r && r.message ? r.message : "Not done"); return }
            Msg.ok(ok); page.load()
        })
    }
    function consentR(c, grant) { call("flow.restricted_consent", { consent_id: c.id, grant: grant }, grant ? "Allowed for this flow · its destinations become places it may be" : "It stays paused") }

    readonly property var groupsDef: [["running", "Running", "moving files, or set up and ready"], ["waiting", "Waiting", "on someone else: a folder to be picked, or an ask to you"],
                                      ["stopped", "Stopped", "stopped by you; nothing goes through"], ["paused", "Paused", "held for you, or paused by you; nothing more goes through until you act"]]
    readonly property var rows: flows.map(function (f) { return Object.assign({ key: String(f.id), name: page.nameOf(f), st: page.stateOf(f) }, f) })
    function inGroup(k) { return rows.filter(function (r) { return r.st === k }).sort(function (a, b) { return (page.lastCopy(b) || 0) - (page.lastCopy(a) || 0) }) }
    readonly property var cur: {
        for (var i = 0; i < rows.length; i++) if (rows[i].key === sel) return rows[i]
        return inGroup("paused")[0] || inGroup("waiting")[0] || inGroup("running")[0] || null
    }
    property string pickedKey: ""
    onCurChanged: {
        pickedKey = cur ? cur.key : ""; loading = true; ldT.restart(); log = []
        if (cur) { var id = cur.id; falcon.call("flow.history", { flow_id: id }, function (ok, r) { if (page.cur && page.cur.id === id) page.log = ok ? (r.history || []) : [] }) }
    }
    Timer { id: ldT; interval: Theme.loadMs; onTriggered: page.loading = false }
    readonly property var steps: Sync.steps(cur)
    readonly property var gates: cur ? gatesOf(cur) : []
    readonly property int gi: cur ? Math.min(gsel[cur.key] || 0, Math.max(0, gates.length - 1)) : 0
    readonly property var g0: gates.length ? gates[gi] : null
    function shape(f) {
        var n = (f.destinations || []).length, s = Sync.steps(f).length
        return "1 source → " + (s ? Theme.many(s, "step") + " → " : "") + Theme.many(n, "destination")
    }
    function why(f) {
        var g = gatesOf(f)
        if (g.length) return g[0].title.indexOf(page.nameOf(f) + " ") === 0 ? g[0].title.slice(page.nameOf(f).length + 1) : g[0].title
        if (f.status === "inactive") return "stopped"
        var l = lastCopy(f)
        return l ? "last copy " + Time.ago(l) : "nothing yet"
    }

    situation: {
        if (!flows.length) return "You have no flows yet."
        var moving = rows.filter(function (r) { return r.st === "running" && page.lastCopy(r) && Time.sameDay(page.lastCopy(r), Time.now) }).length
        var p = inGroup("paused"), w = inGroup("waiting")
        return Theme.fmt(moving) + " of " + Theme.fmt(flows.length) + " flows moved files today; " + (p.length ? Theme.listNames(p.map(function (r) { return r.name }), 2) + (p.length === 1 ? " is" : " are") + " paused" : "nothing is paused")
               + (w.length ? ", " + Theme.fmt(w.length) + " waiting on someone else" : "") + "."
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
            title: "Your flows · " + page.flows.length
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
                            icon: "branches"
                            hot: urg
                            tint: grp.late
                            title: modelData.name
                            tag: "by " + page.who(modelData)
                            line: gs.length ? page.why(modelData) + (gs.length > 1 ? " · and " + (gs.length - 1) + " more" : "") : page.shape(modelData) + " · " + page.why(modelData)
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
                                text: page.lastCopy(fc.modelData) ? Time.ago(page.lastCopy(fc.modelData)) : "no copy yet"
                            }
                            // opened: its facts beside what waits at its gate (am-in)
                            Row {
                                width: parent.width
                                spacing: 24
                                Column {
                                    y: 2
                                    width: Math.min(420, parent.width - 230 - 24)
                                    Repeater {
                                        model: [["From", fc.modelData.source_hostname + " " + fc.modelData.source_path],
                                                ["To", (fc.modelData.destinations || []).map(function (d) { return (d.destination_hostname || "storage") + " " + (d.destination_path || "(they pick the folder)") }).join(", ")],
                                                ["Along the way", Sync.steps(fc.modelData).map(function (s, i) { return (i + 1) + ". " + s.op }).join("  ") || "copied as it is"],
                                                ["Made by", page.who(fc.modelData)]]
                                        delegate: Item {
                                            required property var modelData
                                            required property int index
                                            width: parent.width
                                            height: fv.height + 10
                                            Txt { y: 5; width: 120; text: modelData[0]; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                                            Txt { id: fv; x: 132; y: 5; width: parent.width - 132; text: modelData[1]; font.pixelSize: 13; mono: index < 2; wrapMode: Text.WrapAnywhere; elide: Text.ElideNone }
                                            Rectangle { visible: index < 3; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
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
                                            Txt { width: 230; text: modelData.line + (modelData.at ? "; waiting " + Time.waitLen((Time.now - Time.ms(modelData.at)) / 3600000) : ""); color: Theme.text3; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                                        }
                                    }
                                    Row { visible: fc.gs.length === 0; spacing: 6
                                          Rectangle { width: 7; height: 7; radius: 3.5; anchors.verticalCenter: parent.verticalCenter; color: Theme.ok }
                                          Txt { text: "nothing waits; it runs by itself"; font.pixelSize: 13; elide: Text.ElideNone } }
                                    Txt { topPadding: 4; text: "Last copy"; color: Theme.text3; font.pixelSize: 12 }
                                    Txt { text: page.lastCopy(fc.modelData) ? Time.atDay(page.lastCopy(fc.modelData)) : "none yet"; font.pixelSize: 13; color: Theme.text3 }
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
                sub: page.cur ? page.cur.name + ": what waits at its gate, and what you can do with it" : "pick a flow on the left"
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
                Column {
                    visible: page.g0 !== null
                    width: parent.width
                    spacing: 6
                    Item {
                        width: parent.width
                        height: gk.height
                        Row { id: gk; spacing: 5
                              Icon { name: page.g0 ? page.g0.icon : "clock"; size: 12; color: page.g0 && page.g0.hot ? Theme.crit : Theme.text2; anchors.verticalCenter: parent.verticalCenter }
                              Txt { text: page.g0 ? page.g0.kind : ""; color: page.g0 && page.g0.hot ? Theme.crit : Theme.text2; font.pixelSize: 12; elide: Text.ElideNone } }
                        Txt { anchors.right: parent.right; text: page.g0 && page.g0.at ? "waiting " + Time.waitLen((Time.now - Time.ms(page.g0.at)) / 3600000) : ""; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                    }
                    Txt { width: parent.width; text: page.g0 ? page.g0.title : ""; font.pixelSize: 14; font.weight: Font.DemiBold; lh: 1.35; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                    Txt { width: parent.width; text: page.g0 ? page.g0.line : ""; color: Theme.text2; wrapMode: Text.WordWrap; elide: Text.ElideNone }
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
                        Btn { visible: page.cur !== null && page.mine(page.cur); anchors.verticalCenter: parent.verticalCenter; small: true; iconName: "edit"; text: "Edit"; onClicked: Nav.go("flows", "edit-" + page.cur.id) }
                        Txt { visible: page.cur !== null && !page.mine(page.cur); anchors.verticalCenter: parent.verticalCenter; width: parent.width - ctlRow.width - 12
                              text: page.cur ? (page.askedOfMe(page.cur) ? "an ask to you" : "made by " + page.who(page.cur) + "; only they change it") : ""; color: Theme.text3; font.pixelSize: 12 }
                        Row {
                            id: ctlRow
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 18
                            readonly property var act: page.g0 && page.g0.acts.length ? page.g0.acts[page.gpick[page.g0.id] || 0] : null
                            Btn { visible: ctlRow.act !== null; small: true; kind: "primary"; text: ctlRow.act ? ctlRow.act[0] : ""; enabled: ctlRow.act !== null && ctlRow.act[2]
                                  tip: ctlRow.act && !ctlRow.act[2] ? ctlRow.act[3] : ""; onClicked: if (ctlRow.act[1]) ctlRow.act[1]() }
                            Row {
                                visible: page.cur !== null && page.mine(page.cur)
                                spacing: 6
                                readonly property bool held: page.cur !== null && (page.cur.st === "paused" || page.cur.st === "stopped")
                                Btn { visible: parent.held; small: true; kind: "primary"; iconName: "caretr"; text: page.cur && page.cur.st === "stopped" ? "Start again" : "Resume"
                                      enabled: page.cur !== null && page.cur.st !== "stopped"; tip: page.cur && page.cur.st === "stopped" ? "The Engine cannot start a stopped flow again yet" : ""
                                      onClicked: page.call("flow.resume", { flow_id: page.cur.id }, "Resumed · it carries on, and keeps what was held") }
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
                sub: page.cur ? page.cur.name : "pick a flow on the left"
                readonly property var last: page.log.length ? page.log[0] : null
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
                              text: !page.cur ? "Pick a flow on the left." : page.loading ? "Loading " + page.cur.name : page.cur.consent_status === "pending" ? "Not synced yet. It starts once an Admin agrees and picks a folder." : "Not synced yet." }
                        Txt { visible: syncP.last !== null && !page.loading; width: parent.width; textFormat: Text.StyledText; elide: Text.ElideNone
                              text: syncP.last ? "<span style='font-size:16px;font-weight:600'>" + Time.atDay(syncP.last.synced_at || syncP.last.at) + "</span>"
                                    + (page.log.length > 1 ? "<font color='" + Theme.text3 + "'> · the one before was " + Time.atDay(page.log[1].synced_at || page.log[1].at) + "</font>" : "") : "" }
                        Txt { visible: syncP.last !== null && !page.loading; width: parent.width; color: Theme.text2; wrapMode: Text.WordWrap; elide: Text.ElideNone
                              text: syncP.last ? [syncP.last.path || syncP.last.file_path || "", syncP.last.outcome || syncP.last.result || ""].filter(function (s) { return s }).join(" · ") : "" }
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
            srcs: page.cur ? [{ host: page.cur.source_hostname, path: page.cur.source_path, gone: !!page.cur.pause_reason && page.cur.pause_reason.indexOf("source") === 0 }] : []
            stages: page.steps
            dests: page.cur ? (page.cur.destinations || []).map(function (d) {
                return { host: d.destination_hostname || "storage", path: d.destination_path, ask: page.cur.consent_status === "pending", bad: !!d.paused_reason } }) : []
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
        sub: "files go one way only; nothing restricted rides along without its owner's say"
        GiveSteps {
            steps: [["Pick where files start", "a folder or one file on your machines, or one a flow already fills"], ["Say what happens on the way", "convert, compress, rename or sort, in order; or copy them as they are"], ["Pick where they land", "folders you manage; another Admin's is asked first"]]
            act: "Make a flow"
            onGo: Nav.go("flows", "new")
        }
    }
}
