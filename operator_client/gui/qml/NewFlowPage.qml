import QtQuick
import "."

// MAKE A FLOW (and Edit), in the concept's drawer: three steps, then the summary, as Give a task does. The flow is drawn at the top the whole way and redrawn as each part is filled in.
// Every change is checked against the other flows for a folder written twice or a loop back to a source; the Engine runs the same checks again. What a step can do comes from
// the Engine (flow.steps): Kind, then What it does, then that operation's settings.
Editor {
    id: page
    objectName: "newFlow"
    readonly property int editId: Nav.sub && String(Nav.sub).indexOf("edit-") === 0 ? Number(String(Nav.sub).slice(5)) : 0
    readonly property string editName: editing ? editing.name || "" : ""
    drawerTitle: editId ? "Edit " + editName : "Make a flow"
    drawerNote: "closing keeps what you set; nothing runs until you confirm"
    property bool keeps: !editId
    names: ["Where files start", "What happens on the way", "Where they land", "Summary"]
    showTop: false
    confirmText: editId ? "Save changes" : "Create flow"
    confirmDisabled: problem !== ""

    property var flows: []
    property var editing: null
    property string name: ""
    property var srcs: [{ mode: "dir", pc: 0, path: "", flow: 0, branch: 0 }]
    property string when: "Real time"
    property var stages: []                     // [{ kind, opId, op, settings, scope: "all" | index }]
    property var dests: [{ mode: "mine", pc: 0, path: "", who: 0, note: "" }]
    property string onDelete: "keep"            // what the destinations do when a file is deleted at the source: keep their copy, or put it aside
    property var tree: []                       // flow.steps: categories of kinds of operations
    readonly property var runModes: ({ "Real time": "realtime", "On a schedule": "hourly", "Only when I run it": "manual" })

    Component.onCompleted: {
        falcon.call("flow.steps", {}, function (ok, r) { page.tree = ok ? (r.tree || []) : [] })
        falcon.call("flow.list", {}, function (ok, r) {
            page.flows = ok ? (r.flows || []) : []
            if (page.editId) { page.editing = page.flows.filter(function (x) { return x.id === page.editId })[0] || null; page.fill(page.editing, false) }
        })
    }
    function fill(f, copy) {
        if (!f) return
        name = copy ? "Copy of " + (f.name || "") : f.name || ""
        var ss = f.sources && f.sources.length ? f.sources : [{ source_pc_id: f.source_pc_id, source_path: f.source_path }]
        srcs = ss.map(function (s) { return { mode: s.source_kind === "file" ? "file" : "dir", pc: s.source_pc_id, path: s.source_path, flow: 0, branch: 0 } })
        when = f.run_mode === "hourly" ? "On a schedule" : f.run_mode === "manual" ? "Only when I run it" : "Real time"
        onDelete = f.on_source_delete === "mirror" ? "mirror" : "keep"
        dests = (f.destinations || []).map(function (d) { return { mode: "mine", pc: d.destination_pc_id || 0, path: d.destination_path, who: 0, note: "" } })
        stages = Sync.steps(f)
    }
    function startFrom(id) {
        if (!id) { name = ""; srcs = [{ mode: "dir", pc: 0, path: "", flow: 0, branch: 0 }]; stages = []; dests = [{ mode: "mine", pc: 0, path: "", who: 0, note: "" }]; step = 0; return }
        fill(flows.filter(function (x) { return x.id === id })[0], true); step = 0
    }
    readonly property var hosts: {
        var out = []
        if (myAdmin) out.push({ value: myAdmin.pc_id, label: myAdmin.hostname + " · your workstation" })
        Fleet.machines.forEach(function (m) { out.push({ value: m.pc_id, label: m.host + " · " + (m.user || "no user") + (m.online ? "" : " · offline") }) })
        return out
    }
    readonly property var admins: { var out = []; Fleet.depts.forEach(function (d) { (d.admins || []).forEach(function (a) { if (a.pc_id) out.push(a) }) }); return out }
    readonly property var myAdmin: admins.filter(function (a) { return a.account_id === falcon.accountId })[0] || null
    readonly property var people: admins.filter(function (a) { return a.account_id !== falcon.accountId }).map(function (a) { return { value: a.account_id, label: a.name + " · " + a.hostname } })
    function adminOf(id) { return admins.filter(function (a) { return a.account_id === id })[0] || null }
    function hostName(pc) { var m = Fleet.byPc[pc]; if (m) return m.host; var a = admins.filter(function (x) { return x.pc_id === pc })[0]; return a ? a.hostname : "" }
    readonly property var flowOpts: flows.filter(function (x) { return (x.destinations || []).some(function (d) { return d.destination_pc_id && d.destination_path }) })
                                         .map(function (x) { return { value: x.id, label: (x.name || "flow " + x.id) + " · by " + (x.created_by_name || "an Admin") } })
    function branches(id) { var f = flows.filter(function (x) { return x.id === id })[0]; return f ? (f.destinations || []).filter(function (d) { return d.destination_pc_id && d.destination_path }) : [] }
    readonly property var folderOpts: ["/documents/", "/reports/", "/exports/", "/archive/", "/payroll/", "/payroll-pdf/", "/intake/", "/weekly/"]
    function setSrc(i, f) { var s = srcs.slice(); s[i] = Object.assign({}, s[i], f); srcs = s }
    function setDest(i, f) { var d = dests.slice(); d[i] = Object.assign({}, d[i], f); dests = d }
    function setStage(i, f) { var s = stages.slice(); s[i] = Object.assign({}, s[i], f); stages = s }
    function key(pc, p) { return pc + " " + String(p || "").toLowerCase().replace(/[\\\/]+$/, "") }

    // each source as { pc, path, flow it continues }
    readonly property var rsrc: srcs.map(function (s) {
        if (s.mode === "flow") { var b = page.branches(s.flow)[s.branch || 0]; return b ? { pc: b.destination_pc_id, path: b.destination_path, up: page.flowName(s.flow) } : { pc: 0, path: "", up: "" } }
        var dk = page.key(s.pc, s.path), up = s.pc && s.path ? page.flows.filter(function (f) { return (f.destinations || []).some(function (d) { return page.key(d.destination_pc_id, d.destination_path) === dk }) })[0] : null
        return { pc: s.pc, path: s.path, up: up ? up.name || "" : "" }
    })
    function flowName(id) { var f = flows.filter(function (x) { return x.id === id })[0]; return f ? f.name || "flow " + id : "" }
    // the checks, against every other flow: a folder written twice, a loop back to a source, the same folder twice
    readonly property var checks: {
        var out = [], sk = rsrc.filter(function (s) { return s.pc && s.path }).map(function (s) { return page.key(s.pc, s.path) })
        if (sk.filter(function (k, i) { return sk.indexOf(k) !== i }).length) out.push(["bad", "Two sources are the same folder."])
        var ds = dests.filter(function (d) { return d.mode === "mine" && d.pc && d.path }), keys = ds.map(function (d) { return page.key(d.pc, d.path) })
        ds.forEach(function (d, i) {
            var dk = page.key(d.pc, d.path), nm = page.hostName(d.pc) + " " + d.path
            if (sk.indexOf(dk) >= 0) out.push(["bad", "Destination " + (i + 1) + " is one of the sources."])
            page.flows.forEach(function (f) {
                if (f.id === page.editId) return
                if ((f.destinations || []).some(function (x) { return page.key(x.destination_pc_id, x.destination_path) === dk })) out.push(["warn", nm + " is already written by the " + (f.name || "other") + " flow. Two flows writing one folder can overwrite each other."])
                if (page.key(f.source_pc_id, f.source_path) === dk && (f.destinations || []).some(function (x) { return sk.indexOf(page.key(x.destination_pc_id, x.destination_path)) >= 0 }))
                    out.push(["bad", "This would make a loop: files sent to " + nm + " come back to a source through " + (f.name || "another flow") + "."])
            })
            var m = Fleet.byPc[d.pc]
            if (m && !m.online) out.push(["warn", m.host + " is offline. Its branch starts when it is back."])
        })
        if (keys.filter(function (k, i) { return keys.indexOf(k) !== i }).length) out.push(["bad", "Two destinations are the same folder."])
        return out
    }
    readonly property var bad: checks.filter(function (c) { return c[0] === "bad" })
    readonly property var asks: dests.filter(function (d) { return d.mode === "ask" && d.who })
    function destOk(d) { return d.mode === "ask" ? !!d.who : !!(d.pc && d.path) }
    readonly property var stepProbs: [
        rsrc.some(function (s) { return !s.pc || !s.path }) ? (rsrc.length > 1 ? "Finish or remove the empty source." : "Pick where the files come from.") : "",
        stages.some(function (s) { return !s.opId && !s.op }) ? "Say what each step does." : "",
        !dests.some(destOk) ? "Add at least one destination." : dests.some(function (d) { return !page.destOk(d) }) ? "Finish or remove the empty destination." : "",
        bad.length ? "Fix the problems above first." : ""]
    readonly property string problem: stepProbs.filter(function (p) { return p })[0] || ""
    prob: stepProbs[step] || ""

    Confirm { id: confirm; page: page }
    function save() {
        var p = Sync.plan(stages, dests.length), ds = []
        dests.forEach(function (d, i) {
            if (d.mode === "ask") { var a = page.adminOf(d.who); ds.push({ destination_pc_id: a ? a.pc_id : null, destination_path: "", let_them_choose: true, parent_index: p.parents[i], note: d.note }) }
            else ds.push({ destination_pc_id: d.pc, destination_path: d.path, parent_index: p.parents[i] })
        })
        var payload = { name: name.trim() || (rsrc[0] ? Sync.folder(rsrc[0].path) : ""), destinations: ds, stages: p.stages, run_mode: runModes[when], on_source_delete: onDelete }
        if (editId) payload.flow_id = editId
        else if (srcs.length === 1 && srcs[0].mode === "flow") { var b = branches(srcs[0].flow)[srcs[0].branch || 0]; payload.from_flow = { flow_id: srcs[0].flow, destination_id: b ? b.id : 0 } }
        else if (srcs.length === 1) { payload.source_pc_id = rsrc[0].pc; payload.source_path = rsrc[0].path; if (srcs[0].mode === "file") payload.source_kind = "file" }
        else payload.sources = rsrc.map(function (s, i) { return { source_pc_id: s.pc, source_path: s.path, source_kind: page.srcs[i].mode === "file" ? "file" : "folder" } })
        send(payload)
    }
    // Files already in a destination are surfaced, never overwritten or accepted silently (flow-natural-combo.md, Pre-Flight Collision Check): the Engine refuses until the
    // creator says it is intended, and the flow never overwrites a file it did not write: the Worker keeps it beside the new one as <name>-modified.
    function send(payload) {
        falcon.call(page.editId ? "flow.edit" : "flow.create", payload, function (ok, r) {
            if (!ok && r && r.code === "conflict" && /collides with existing content/.test(r.message || "") && !payload.confirm_collisions) {
                var what = String(r.message).replace(/^.*existing content:\s*/, "").replace(/\s*--.*$/, "")
                confirm.ask({ title: "Files are already in the destination", ok: "Create anyway", cancel: "Choose another folder",
                              text: what + ". Nothing there is overwritten or deleted: where a file has the same name, the existing one is kept beside the new one as name-modified, and you are told." },
                            function () { payload.confirm_collisions = true; page.send(payload) })
                return
            }
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not saved"); return }
            var who = page.asks.map(function (d) { var a = page.adminOf(d.who); return a ? a.name : "" })
            Msg.ok(who.length ? (page.editId ? "Saved; " : "Flow created; ") + Theme.listNames(who) + " asked to pick a folder"
                   : page.editId ? "Saved · checks passed, recorded in the audit log"
                   : r.restricted_pending ? "Flow created but paused · it would carry something restricted, so its owner is asked first" : "Flow created and running")
            page.keeps = false
            Nav.go("flows")
        })
    }
    onConfirmed: save()
    onClosed: {}

    // the Engine's tree, flat: its kinds, and the operations of the one picked
    readonly property var kinds: {
        var out = []
        tree.forEach(function (c) { (c.kinds || []).forEach(function (k) { out.push(k) }) })
        return out.length ? out : Object.keys(Sync.stepOps).map(function (k) { return { kind: k, label: k, ops: Sync.stepOps[k].map(function (o) { return { op: o, label: o } }) } })
    }
    function kindOf(k) { return kinds.filter(function (x) { return x.kind === k })[0] || null }
    function opOf(st) { var k = kindOf(st.kind); return k ? (k.ops || []).filter(function (o) { return o.op === st.opId })[0] || null : null }
    function firstStep() { var k = kinds[0]; var o = k && k.ops ? k.ops[0] : null; return { kind: k ? k.kind : "", opId: o ? o.op : "", op: o ? o.label : "", settings: {}, scope: "all" } }

    // --- the flow so far, drawn --------------------------------------------------------------------------------------------------------
    component Fld: Column { property string label: ""; property string note: ""; default property alias inner: fi.data; width: parent ? parent.width : 0; spacing: 5
        Txt { text: parent.label; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
        Column { id: fi; width: parent.width }
        Txt { visible: parent.note !== ""; width: parent.width; text: parent.note; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone } }
    component NCard: Rectangle { id: nc; property int n: 0; property bool xOff: false; default property alias inner: ni.data; property alias lead: nh.data; signal removed()
        width: parent ? parent.width : 0; height: ncol.height + 30; radius: 8; color: Theme.surface2
        Column { id: ncol; x: 16; y: 14; width: parent.width - 32; spacing: 12
            Item { width: parent.width; height: 24
                Rectangle { width: 22; height: 22; radius: 4; color: Theme.surface3; anchors.verticalCenter: parent.verticalCenter
                            Txt { anchors.centerIn: parent; text: nc.n + 1; mono: true; font.pixelSize: 12; elide: Text.ElideNone } }
                Row { id: nh; x: 32; anchors.verticalCenter: parent.verticalCenter }
                Btn { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; small: true; kind: "text"; iconName: "close"; enabled: !nc.xOff; onClicked: nc.removed() } }
            Column { id: ni; width: parent.width; spacing: 12 } } }
    component Head2: Column { property string t: ""; property string d: ""; width: parent ? parent.width : 0; spacing: 2; bottomPadding: 10
        Txt { width: parent.width; text: parent.t; font.pixelSize: 18; font.weight: Font.DemiBold }
        Txt { width: parent.width; text: parent.d; color: Theme.text3; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone } }

    Box {
        objectName: "newFlowPreview"
        parent: page.topSlot
        width: page.width
        gap: 6
        title: page.editId ? "Editing " + page.editName : page.name.trim() || "The flow so far"
        sub: page.names[page.step] + " · step " + (page.step + 1) + " of 4"
        extra: Select { visible: !page.editId && page.step === 0; small: true; search: true; width: 220; placeholder: "Start from a copy of a flow"
                        options: page.flows.map(function (x) { return { value: x.id, label: "Copy of " + (x.name || x.id) } }); onPicked: function (v) { page.startFrom(v) } }
        FlowGraph {
            width: parent.width
            srcs: page.rsrc.map(function (s) { var h = page.hostName(s.pc); return { host: h || "Pick a machine", path: h && s.path ? s.path : h ? "and a folder" : "", empty: !(h && s.path) } })
            stages: page.stages
            dests: page.dests.map(function (d) {
                if (d.mode === "ask") { var a = page.adminOf(d.who); return { host: a ? a.name : "Pick a machine", path: "picks a folder", ask: true } }
                var h = page.hostName(d.pc); return { host: h || "Pick a machine", path: h && d.path ? d.path : h ? "and a folder" : "", empty: !(h && d.path) } })
        }
    }

    // --- where files start ---------------------------------------------------------------------------------------------------------------
    Head2 { visible: page.step === 0; t: "Where do the files come from?"; d: "One source or several. Each is a folder or one file on a machine, or an existing flow, so this one carries on with whatever that flow delivers." }
    Repeater {
        model: page.step === 0 ? page.srcs : []
        delegate: NCard {
            id: sc
            required property var modelData
            required property int index
            n: index; xOff: page.srcs.length === 1
            onRemoved: page.srcs = page.srcs.filter(function (_, j) { return j !== sc.index })
            lead: Segmented { options: [{ value: "dir", label: "A folder" }, { value: "file", label: "One file" }, { value: "flow", label: "An existing flow" }]; value: sc.modelData.mode; onPicked: function (v) { page.setSrc(sc.index, { mode: v }) } }
            Fld { visible: sc.modelData.mode === "flow"; label: "Flow"
                Select { width: parent.width; search: true; placeholder: "Pick a flow"; value: sc.modelData.flow || null; options: page.flowOpts; onPicked: function (v) { page.setSrc(sc.index, { flow: v, branch: 0 }) } } }
            Fld { visible: sc.modelData.mode === "flow" && page.branches(sc.modelData.flow).length > 1; label: "Which of its destinations"
                Select { width: parent.width; value: sc.modelData.branch || 0; options: page.branches(sc.modelData.flow).map(function (d, j) { return { value: j, label: page.hostName(d.destination_pc_id) + " " + d.destination_path } }); onPicked: function (v) { page.setSrc(sc.index, { branch: v }) } } }
            Fld { visible: sc.modelData.mode !== "flow"; label: "Machine"
                Select { width: parent.width; search: true; placeholder: "Pick a machine"; value: sc.modelData.pc || null; options: page.hosts; onPicked: function (v) { page.setSrc(sc.index, { pc: v }) } } }
            Fld { visible: sc.modelData.mode === "dir"; label: "Folder"
                FolderField { width: parent.width; pcId: sc.modelData.pc; text: sc.modelData.path; mono: false; placeholder: "For example /weekly/"; onEdited: function (t) { page.setSrc(sc.index, { path: t }) } } }
            Fld { visible: sc.modelData.mode === "file"; label: "File"; note: "Followed wherever it goes: moved or renamed on its machine, it keeps syncing from where it now is. The copy at each destination is followed the same way."
                Field { width: parent.width; text: sc.modelData.path; placeholderText: "For example C:\\Reports\\q3-summary.xlsx"; onTextEdited: page.setSrc(sc.index, { path: text }) } }
            Txt { visible: !!page.rsrc[sc.index] && page.rsrc[sc.index].up !== ""; width: parent.width; color: Theme.text3; font.pixelSize: 12; textFormat: Text.StyledText
                  text: page.rsrc[sc.index] ? (sc.modelData.mode === "flow" ? "Carries on <font color='" + Theme.text2 + "'>" + page.rsrc[sc.index].up + "</font> from where it delivers." : "This folder is where <font color='" + Theme.text2 + "'>" + page.rsrc[sc.index].up + "</font> delivers, so this flow carries on from it.") : "" }
        }
    }
    Btn { visible: page.step === 0; iconName: "plus"; text: "Add a source"; onClicked: page.srcs = page.srcs.concat([{ mode: "dir", pc: 0, path: "", flow: 0, branch: 0 }]) }
    NfSec { visible: page.step === 0; title: "Copy files"
        NfPick { title: "Real time"; desc: "A file is copied the moment it changes, from the machine's own file events."; on: page.when === "Real time"; onPicked: page.when = "Real time" }
        NfPick { title: "On a schedule"; desc: "Changed files are copied together, every hour."; on: page.when === "On a schedule"; onPicked: page.when = "On a schedule" }
        NfPick { title: "Only when I run it"; desc: "Nothing moves until someone presses Run on the flow."; on: page.when === "Only when I run it"; onPicked: page.when = "Only when I run it" } }

    NfSec { visible: page.step === 0; title: "When a file is deleted at the source"
        NfPick { objectName: "nfKeep"; title: "Keep the copies"; desc: "The destinations keep what they were given. Deleting a file here never deletes it there."; on: page.onDelete === "keep"; onPicked: page.onDelete = "keep" }
        NfPick { objectName: "nfMirror"; title: "Remove the copies"; desc: "The destinations put their copy aside, in a “.falcon-removed” folder; nothing is destroyed. Only a copy this flow wrote and nobody has changed is touched."; on: page.onDelete === "mirror"; onPicked: page.onDelete = "mirror" } }

    // --- what happens on the way -----------------------------------------------------------------------------------------------------------
    Head2 { visible: page.step === 1; t: "Should anything happen to the files on the way?"; d: "Optional. Steps run in order, top to bottom. With none, files are copied exactly as they are." }
    Rectangle { visible: page.step === 1 && page.stages.length === 0; width: parent.width; height: 54; radius: 8; color: "transparent"
                DashBox { radius: 8 }
                Txt { anchors.centerIn: parent; text: "No steps. Files are copied exactly as they are."; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone } }
    Repeater {
        model: page.step === 1 ? page.stages : []
        delegate: NCard {
            id: tc
            required property var modelData
            required property int index
            readonly property var k: page.kindOf(modelData.kind)
            readonly property var o: page.opOf(modelData)
            readonly property var sets: o && o.settings ? Object.keys(o.settings) : []
            n: index
            onRemoved: page.stages = page.stages.filter(function (_, j) { return j !== tc.index })
            lead: Txt { text: "Step " + (tc.index + 1); font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideNone }
            Fld { label: "Kind"
                Select { width: parent.width; value: tc.modelData.kind; options: page.kinds.map(function (x) { return { value: x.kind, label: x.label || x.kind } })
                         onPicked: function (v) { var f = page.kindOf(v), q = f && f.ops ? f.ops[0] : null; page.setStage(tc.index, { kind: v, opId: q ? q.op : "", op: q ? q.label : "", settings: {} }) } } }
            Fld { label: "What it does"
                Select { width: parent.width; value: tc.modelData.opId; options: (tc.k ? tc.k.ops || [] : []).map(function (x) { return { value: x.op, label: x.label || x.op } })
                         onPicked: function (v) { var q = (tc.k.ops || []).filter(function (x) { return x.op === v })[0]; page.setStage(tc.index, { opId: v, op: q ? q.label || v : v, settings: {} }) } } }
            // the operation's settings, drawn from what the Engine says about each
            Repeater {
                model: tc.sets
                delegate: Fld {
                    id: sf
                    required property var modelData
                    readonly property var spec: tc.o.settings[modelData]
                    readonly property var cur: (tc.modelData.settings || {})[modelData]
                    function put(v) { var s = Object.assign({}, tc.modelData.settings || {}); s[sf.modelData] = v; page.setStage(tc.index, { settings: s }) }
                    label: spec.label || String(modelData).replace(/_/g, " ").replace(/^./, function (x) { return x.toUpperCase() })
                    Select { visible: !!sf.spec.choices && !sf.spec.many; width: parent.width; value: sf.cur !== undefined ? sf.cur : sf.spec.default === undefined ? null : sf.spec.default
                             options: (sf.spec.choices || []).map(function (c) { return { value: c, label: sf.spec.words && sf.spec.words[c] ? sf.spec.words[c] : String(c) } }); onPicked: function (v) { sf.put(v) } }
                    Select { visible: !!sf.spec.choices && !!sf.spec.many; multiple: true; width: parent.width; values: sf.cur || []
                             options: (sf.spec.choices || []).map(function (c) { return { value: c, label: sf.spec.words && sf.spec.words[c] ? sf.spec.words[c] : String(c) } }); onPicked: function (v) { sf.put(v) } }
                    Field { visible: !sf.spec.choices && !sf.spec.flag; width: parent.width; text: sf.cur === undefined ? "" : Array.isArray(sf.cur) ? sf.cur.join(", ") : String(sf.cur)
                            onTextEdited: sf.put(sf.spec.list ? text.split(/[,\s]+/).filter(function (x) { return x }) : sf.spec.number ? Number(text) : text) }
                    Check { visible: !!sf.spec.flag; checked: !!sf.cur; onToggled: function (v) { sf.put(v) } }
                }
            }
            Fld { label: "Applies to"; note: tc.modelData.scope === "all" ? "before the flow splits, so every destination gets the result" : ""
                Segmented { small: false; options: [{ value: "all", label: "Every destination" }, { value: "one", label: "One destination" }]; value: tc.modelData.scope === "all" ? "all" : "one"; onPicked: function (v) { page.setStage(tc.index, { scope: v === "all" ? "all" : 0 }) } } }
            Fld { visible: tc.modelData.scope !== "all"; label: "Which destination"
                Select { width: parent.width; value: tc.modelData.scope === "all" ? 0 : tc.modelData.scope; onPicked: function (v) { page.setStage(tc.index, { scope: v }) }
                         options: page.dests.map(function (d, j) { var a = page.adminOf(d.who); return { value: j, label: d.mode === "ask" ? (a ? a.name + " picks a folder" : "Destination " + (j + 1)) : (page.hostName(d.pc) || "Destination " + (j + 1)) + " " + (d.path || "") } }) } }
        }
    }
    Btn { visible: page.step === 1; iconName: "plus"; text: "Add a step"; onClicked: page.stages = page.stages.concat([page.firstStep()]) }

    // --- where they land ---------------------------------------------------------------------------------------------------------------------
    Head2 { visible: page.step === 2; t: "Where should the files go?"; d: "Each destination gets its own copy of every file. For anywhere you do not manage, ask the person it belongs to; they pick the folder." }
    Repeater {
        model: page.step === 2 ? page.dests : []
        delegate: NCard {
            id: dc
            required property var modelData
            required property int index
            n: index; xOff: page.dests.length === 1
            onRemoved: page.dests = page.dests.filter(function (_, j) { return j !== dc.index })
            lead: Segmented { options: [{ value: "mine", label: "You pick the folder" }, { value: "ask", label: "Another Admin's machine" }]; value: dc.modelData.mode; onPicked: function (v) { page.setDest(dc.index, { mode: v }) } }
            readonly property var who: page.adminOf(modelData.who)
            Fld { visible: dc.modelData.mode === "ask"; label: "Which Admin"; note: dc.who ? dc.who.name + " picks a folder on their own workstation. Picking it is how they agree; until then this destination waits." : ""
                Select { width: parent.width; search: true; placeholder: "Another Admin"; value: dc.modelData.who || null; options: page.people; onPicked: function (v) { page.setDest(dc.index, { who: v }) } } }
            Fld { visible: dc.modelData.mode === "ask"; label: "A line for them"
                Field { width: parent.width; text: dc.modelData.note || ""; placeholderText: "What this is for (optional)"; onTextEdited: page.setDest(dc.index, { note: text }) } }
            Fld { visible: dc.modelData.mode === "mine"; label: "Machine"
                Select { width: parent.width; search: true; placeholder: "A Worker's machine, or your own"; value: dc.modelData.pc || null; options: page.hosts; onPicked: function (v) { page.setDest(dc.index, { pc: v }) } } }
            Fld { visible: dc.modelData.mode === "mine"; label: "Folder"; note: dc.modelData.pc ? "Nobody has to agree: only another Admin's machine asks them first." : ""
                FolderField { width: parent.width; pcId: dc.modelData.pc; text: dc.modelData.path; mono: false; placeholder: "For example /archive/"; onEdited: function (t) { page.setDest(dc.index, { path: t }) } } }
        }
    }
    Btn { visible: page.step === 2; iconName: "plus"; text: "Add a destination"; onClicked: page.dests = page.dests.concat([{ mode: "mine", pc: 0, path: "", who: 0, note: "" }]) }
    Decide { visible: page.step === 2 && page.dests.length > 8; c: Theme.med; text: "That is a lot of destinations. Every file is copied " + page.dests.length + " times." }

    // --- summary --------------------------------------------------------------------------------------------------------------------------------
    Head2 { visible: page.step === 3; t: page.editId ? "Check it and save" : "Name it and check it"
            d: page.editId ? "The checks run again against every other flow. It keeps running as it was until you save." : "Checked against the one file index and every other flow before anything is copied." }
    FactRows { visible: page.step === 3
        rows: [["Made by", "you"], ["From", page.rsrc.map(function (s) { return page.hostName(s.pc) + " " + s.path }).join(", ")], ["Along the way", page.stages.map(function (s, i) { return (i + 1) + ". " + s.op }).join("  ") || "copied as they are"],
               ["To", page.dests.map(function (d) { var a = page.adminOf(d.who); return d.mode === "ask" ? (a ? a.name : "") + " picks a folder" : page.hostName(d.pc) + " " + d.path }).join(", ")], ["Copies files", page.when.toLowerCase()], ["If a file is deleted", page.onDelete === "keep" ? "the copies stay" : "the copies are put aside"]] }
    Item { visible: page.step === 3; width: parent.width; height: Theme.control + 6
        Txt { width: 130; y: 12; text: "Name"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
        Field { x: 142; y: 6; width: 320; text: page.name; placeholderText: page.rsrc[0] ? Sync.folder(page.rsrc[0].path) || "my-flow" : "my-flow"; onTextEdited: page.name = text } }
    Column {
        visible: page.step === 3
        width: parent.width
        spacing: 8
        topPadding: 6
        Repeater {
            model: [["No loop back to a source, along the whole chain", !page.checks.some(function (c) { return /loop/.test(c[1]) })], ["No folder written by two flows", !page.checks.some(function (c) { return /already written/.test(c[1]) })],
                    ["Every source and destination is a different folder", !page.checks.some(function (c) { return /same folder|one of the sources/.test(c[1]) })]]
            Row { required property var modelData; spacing: 8
                Icon { name: modelData[1] ? "checkcirclefilled" : "closecirclefilled"; size: 14; color: modelData[1] ? Theme.ok : Theme.crit; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: modelData[0]; font.pixelSize: 13; elide: Text.ElideNone } }
        }
        Repeater { model: page.checks
            Decide { required property var modelData; c: modelData[0] === "bad" ? Theme.crit : Theme.med; text: modelData[1] } }
        Decide { visible: page.asks.length > 0; c: Theme.med
                 text: "Waiting on " + page.asks.map(function (d) { var a = page.adminOf(d.who); return a ? a.name : "" }).join(" and ") + ". The flow is created now. " + (page.asks.length === 1 ? "They are" : "Each is") + " asked to pick a folder on their own workstation, and that branch starts when they do. The rest starts straight away." }
    }
}
