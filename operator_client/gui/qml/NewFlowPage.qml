import QtQuick
import "."

// NEW FLOW (and Edit). The flow drawn on top as it is built; under it three columns in the files' own
// order -- Sources, Along the way, Destinations -- each with its own Add and always one height, the
// tallest one's; then the name, how files are copied and the checks. Every change is checked against the
// other flows for a folder written twice or a loop back to a source before it is saved; the Engine runs
// the same checks again.
//
// What the Engine takes today: one source folder, destinations on machines (a machine not yours is
// asked to agree), and steps by kind. Several sources, continuing another flow, and asking someone to
// pick their own folder are drawn and held back, and say so.
Page {
    id: page
    objectName: "newFlow"
    bare: true

    readonly property int editId: Nav.sub && String(Nav.sub).indexOf("edit-") === 0 ? Number(String(Nav.sub).slice(5)) : 0
    property var flows: []
    property var src: ({ pc: 0, path: "" })
    property string when: "Real time"
    property var stages: []                 // [{kind, op, scope: "all" | index}]
    property var dests: [{ mode: "mine", pc: 0, path: "", who: 0 }]

    property int copyOf: 0                  // the flow this one starts as a copy of, or 0
    Component.onCompleted: falcon.call("flow.list", {}, function (ok, r) {
        page.flows = ok ? (r.flows || []) : []
        if (page.editId) page.fill(page.flows.filter(function (x) { return x.id === page.editId })[0])
    })
    // the builder's state from an existing flow: as itself when editing it, or as a copy to start from
    function fill(f) {
        if (!f) return
        page.src = { pc: f.source_pc_id, path: f.source_path }
        page.dests = (f.destinations || []).map(function (d) { return { mode: "mine", pc: d.destination_pc_id || 0, path: d.destination_path, who: 0 } })
        page.stages = Sync.steps(f)
    }
    function startFrom(id) {
        page.copyOf = id || 0
        if (!id) { page.src = { pc: 0, path: "" }; page.stages = []; page.dests = [{ mode: "mine", pc: 0, path: "", who: 0 }]; return }
        page.fill(page.flows.filter(function (x) { return x.id === id })[0])
    }
    function flowName(f) { return Sync.folder(f.source_path) + "-" + f.id }
    readonly property var stageOps: Sync.stepOps
    readonly property var hosts: {
        var out = []
        if (!Nav.boss && falcon.pcId) out.push({ value: falcon.pcId, label: "your workstation" })
        Fleet.machines.forEach(function (m) { out.push({ value: m.pc_id, label: m.host + " · " + (m.user || "no user") + (m.online ? "" : " · offline") }) })
        if (Nav.boss) Fleet.depts.forEach(function (d) { d.admins.forEach(function (a) { if (a.pc_id) out.push({ value: a.pc_id, label: (a.hostname || "WS") + " · " + a.name + "'s workstation" }) }) })
        return out
    }
    function hostName(pc) { var m = Fleet.byPc[pc]; if (m) return m.host; var h = hosts.filter(function (x) { return x.value === pc })[0]; return h ? h.label.split(" · ")[0] : "" }
    function setDest(i, f) { var d = dests.slice(); d[i] = Object.assign({}, d[i], f); dests = d }
    function setStage(i, f) { var s = stages.slice(); s[i] = Object.assign({}, s[i], f); stages = s }
    function key(pc, p) { return pc + " " + String(p || "").toLowerCase().replace(/[\\\/]+$/, "") }

    // the checks, against every other flow: a folder written twice, a loop back to the source, the same folder twice
    readonly property var checks: {
        var out = [], sk = key(src.pc, src.path)
        var ds = dests.filter(function (d) { return d.mode === "mine" && d.pc && d.path })
        var keys = ds.map(function (d) { return key(d.pc, d.path) })
        if (keys.filter(function (k, i) { return keys.indexOf(k) !== i }).length) out.push(["bad", "Two destinations are the same folder."])
        ds.forEach(function (d, i) {
            var dk = key(d.pc, d.path)
            if (src.pc && dk === sk) out.push(["bad", "Destination " + (i + 1) + " is the source."])
            flows.forEach(function (f) {
                if (f.id === page.editId) return
                if ((f.destinations || []).some(function (x) { return key(x.destination_pc_id, x.destination_path) === dk }))
                    out.push(["warn", page.hostName(d.pc) + " " + d.path + " is already written by another flow. Two flows writing one folder can overwrite each other."])
                if (key(f.source_pc_id, f.source_path) === dk && (f.destinations || []).some(function (x) { return key(x.destination_pc_id, x.destination_path) === sk }))
                    out.push(["bad", "This would make a loop: files sent to " + page.hostName(d.pc) + " " + d.path + " come back to the source through another flow."])
            })
            var m = Fleet.byPc[d.pc]
            if (m && !m.online) out.push(["warn", m.host + " is offline. Its branch starts when it is back."])
        })
        return out
    }
    readonly property var bad: checks.filter(function (c) { return c[0] === "bad" })
    readonly property string problem: !src.pc || !src.path ? "Pick where the files come from."
        : !dests.some(function (d) { return d.mode === "mine" && d.pc && d.path }) ? "Add at least one destination."
        : dests.some(function (d) { return d.mode === "ask" }) ? "Asking someone to pick their own folder is not built in the Engine yet."
        : dests.some(function (d) { return d.mode === "mine" && (!d.pc || !d.path) }) ? "Finish or remove the empty destination."
        : bad.length ? "Fix the problems above first." : ""

    Confirm { id: confirm; page: page }
    function cancel() {
        if (!src.pc && !src.path && !stages.length && dests.every(function (d) { return !d.pc && !d.path })) { Nav.go("flows"); return }
        confirm.ask({ title: page.editId ? "Stop editing this flow?" : "Stop creating this flow?", ok: "Discard", cancel: "Keep going", danger: true,
                      text: page.editId ? "Your changes are discarded. The flow keeps running as it was." : "Nothing has been saved. What you have set so far is discarded." },
                    function () { Nav.go("flows") })
    }
    function save() {
        // the shared steps one after another, then each destination's own steps; each keeps its name (Sync.plan)
        var p = Sync.plan(stages, dests.length)
        var ds = []
        dests.forEach(function (d, i) { if (d.mode === "mine") ds.push({ destination_pc_id: d.pc, destination_path: d.path, parent_index: p.parents[i] }) })
        var payload = { destinations: ds, stages: p.stages }
        if (page.editId) payload.flow_id = page.editId
        else { payload.source_pc_id = src.pc; payload.source_path = src.path }
        falcon.call(page.editId ? "flow.edit" : "flow.create", payload, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not saved"); return }
            Msg.ok(page.editId ? "Saved · checks passed, recorded in the audit log" : r.consent_pending ? "Flow created · the owner is asked to agree" : "Flow created and running")
            Nav.go("flows")
        })
    }

    // the three columns are side by side at every width and one height, the tallest one's, so their Add buttons
    // sit on one line (user, 13 Oct 2026)
    readonly property real colH: Math.max(c1.need, c2.need, c3.need)
    // the Applies-to switch at its natural width; a card narrower than that stretches it and cuts the labels short
    TextMetrics { id: tmAll; font.family: Theme.sans; font.pixelSize: Theme.fSmall; font.weight: Font.Medium; text: "Every destination (before the split)" }
    TextMetrics { id: tmOne; font.family: Theme.sans; font.pixelSize: Theme.fSmall; font.weight: Font.Medium; text: "One destination" }
    readonly property real applyW: tmAll.width + tmOne.width + 4 * 9 + 4

    // a stage column: its number, title and a quiet line, the cards, and its Add button on the bottom line
    component StageCol: Rectangle {
        id: sc
        property int n: 1
        property string t: ""
        property string d: ""
        default property alias inner: cb.data
        property alias add: addSlot.data
        readonly property real need: 42 + 14 + cb.height + 10 + addSlot.height + 14
        width: parent ? (parent.width - 28) / 3 : 0
        height: page.colH
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.border
        Row { x: 14; height: 41; spacing: 8
              Num { n: sc.n; anchors.verticalCenter: parent.verticalCenter }
              Txt { text: sc.t; font.weight: Font.DemiBold; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
              Txt { text: sc.d; color: Theme.text3; font.pixelSize: Theme.fSmall; leftPadding: 2; width: Math.min(implicitWidth, sc.width - x - 14)
                    anchors.verticalCenter: parent.verticalCenter } }
        Rectangle { y: 41; x: 1; width: parent.width - 2; height: 1; color: Theme.border }
        Column { id: cb; x: 14; y: 56; width: parent.width - 28; spacing: 10 }
        Item { id: addSlot; x: 14; width: parent.width - 28; height: childrenRect.height; anchors.bottom: parent.bottom; anchors.bottomMargin: 14 }
    }
    component Num: Rectangle {
        property int n: 1
        width: 22; height: 22; radius: 4; color: Theme.surface3
        Txt { anchors.centerIn: parent; text: String(parent.n); mono: true; font.pixelSize: 12; elide: Text.ElideNone }
    }
    // a card in a column; its close button sits pinned in the top-right corner
    component Box: Rectangle {
        id: bx
        default property alias inner: bc.data
        property bool canRemove: true
        signal remove()
        width: parent ? parent.width : 0
        height: bc.height + 28
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.border
        Column { id: bc; x: 14; y: 14; width: parent.width - 54; spacing: 10 }
        Btn { x: parent.width - width - 8; y: 10; small: true; kind: "text"; iconName: "close"; enabled: bx.canRemove; onClicked: bx.remove() }
    }

    EditorShell {
        width: parent.width
        ratio: 1
        problem: page.problem
        note: "Checked against every other flow and the one file index"
        saveLabel: page.editId ? "Save changes" : "Create flow"
        onCancel: page.cancel()
        onSave: page.save()
        leftPane: Column {
            width: parent.width
            spacing: 14
            // the drawing, on top, as it is built
            Panel {
                width: parent.width
                title: page.editId ? "Editing " + (page.flows.filter(function (x) { return x.id === page.editId }).map(page.flowName)[0] || "this flow") : "The flow so far"
                sub: page.editId ? "it keeps running as it was until you save" : "files only move left to right"
                extra: Select { visible: !page.editId; width: 220; small: true; search: true; placeholder: "Start from a copy of a flow"; value: page.copyOf || null
                                options: (page.copyOf ? [{ value: 0, label: "Start blank" }] : []).concat(page.flows.map(function (x) { return { value: x.id, label: "Copy of " + page.flowName(x) } }))
                                onPicked: function (v) { page.startFrom(v) } }
                FlowPreview {
                    objectName: "newFlowPreview"
                    width: parent.width
                    srcs: [{ host: page.src.pc ? page.hostName(page.src.pc) : "", path: page.src.path }]
                    stages: page.stages
                    dests: page.dests.map(function (d) { return d.mode === "ask" ? { host: "Someone", ask: true } : { host: d.pc ? page.hostName(d.pc) : "", path: d.path } })
                }
            }
            // sources | along the way | destinations, in the files' own order
            Row {
                width: parent.width
                spacing: 14
                StageCol {
                    id: c1
                    objectName: "nfSources"
                    n: 1; t: "Sources"; d: "a folder, or an existing flow"
                    Box {
                        canRemove: false
                        Segmented { options: [{ value: "dir", label: "A folder" }, { value: "flow", label: "An existing flow" }]; value: "dir"
                                    onPicked: function (v) { if (v === "flow") { Msg.warn("Continuing another flow is not built in the Engine yet"); value = "dir" } } }
                        Flow { width: parent.width; spacing: 10
                               Select { width: Math.min(280, parent.width); search: true; placeholder: "Machine"; value: page.src.pc || null; options: page.hosts; enabled: !page.editId
                                        onPicked: function (v) { page.src = { pc: v, path: page.src.path } } }
                               FolderField { width: Math.min(200, parent.width); pcId: page.src.pc; text: page.src.path; placeholder: "Folder"
                                             onEdited: function (t) { page.src = { pc: page.src.pc, path: t } } } }
                    }
                    add: Btn { width: parent.width; iconName: "plus"; text: "Add a source"; enabled: false; tip: "Several sources are not built in the Engine yet" }
                }
                StageCol {
                    id: c2
                    objectName: "nfSteps"
                    n: 2; t: "Along the way"; d: "optional"
                    Item { visible: page.stages.length === 0; width: parent.width; height: 46
                           // dashed, as the concept's empty slot is
                           Canvas { anchors.fill: parent
                                    onPaint: { var c = getContext("2d"); c.reset(); c.strokeStyle = Theme.borderStrong; c.lineWidth = 1; c.setLineDash([4, 3])
                                               var r = Theme.radius, w = width - 1, h = height - 1; c.beginPath(); c.moveTo(0.5 + r, 0.5); c.lineTo(w - r, 0.5); c.arcTo(w, 0.5, w, r, r)
                                               c.lineTo(w, h - r); c.arcTo(w, h, w - r, h, r); c.lineTo(0.5 + r, h); c.arcTo(0.5, h, 0.5, h - r, r); c.lineTo(0.5, 0.5 + r); c.arcTo(0.5, 0.5, 0.5 + r, 0.5, r); c.stroke() }
                                    onWidthChanged: requestPaint()
                                    Connections { target: Theme; function onDarkChanged() { parent.requestPaint() } } }
                                Txt { anchors.centerIn: parent; width: Math.min(implicitWidth, parent.width - 20); text: "No steps. Files are copied exactly as they are."; color: Theme.text3 } }
                    Repeater {
                        model: page.stages
                        Box {
                            required property var modelData
                            required property int index
                            onRemove: { var s = page.stages.slice(); s.splice(index, 1); page.stages = s }
                            Flow { width: parent.width; spacing: 10
                                   Select { width: 130; value: modelData.kind; options: ["Transform", "Categorize"]; onPicked: function (v) { page.setStage(index, { kind: v, op: page.stageOps[v][0] }) } }
                                   Select { width: Math.min(200, parent.width); value: modelData.op; options: page.stageOps[modelData.kind].indexOf(modelData.op) < 0 ? [modelData.op].concat(page.stageOps[modelData.kind]) : page.stageOps[modelData.kind]
                                            onPicked: function (v) { page.setStage(index, { op: v }) } } }
                            // below the close button, so this row may use the card's right padding too
                            Flow { width: parent.width + 40; spacing: 8
                                   Txt { height: aseg.height; verticalAlignment: Text.AlignVCenter; text: "Applies to"; color: Theme.text3; font.pixelSize: 12 }
                                   Segmented { id: aseg; block: page.applyW > parent.width; width: block ? parent.width : implicitWidth; options: [{ value: "all", label: "Every destination (before the split)" }, { value: "one", label: "One destination" }]
                                               value: modelData.scope === "all" ? "all" : "one"; onPicked: function (v) { page.setStage(index, { scope: v === "all" ? "all" : 0 }) } }
                                   Select { visible: modelData.scope !== "all"; width: Math.min(200, parent.width); small: true; value: modelData.scope
                                            options: page.dests.map(function (d, j) { return { value: j, label: d.mode === "ask" ? "Destination " + (j + 1) : d.pc ? page.hostName(d.pc) + " " + d.path : "Destination " + (j + 1) } })
                                            onPicked: function (v) { page.setStage(index, { scope: v }) } } }
                        }
                    }
                    Txt { visible: page.stages.length > 0; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                          text: "The Worker carries out Sort by file type today; the other steps are not built in the Worker yet and leave the files as they are." }
                    add: Btn { width: parent.width; iconName: "plus"; text: "Add a step"; onClicked: page.stages = page.stages.concat([{ kind: "Transform", op: "Rename by date", scope: "all" }]) }
                }
                StageCol {
                    id: c3
                    objectName: "nfDests"
                    n: 3; t: "Destinations"; d: page.dests.length > 1 ? page.dests.length + ", so the flow branches" : "each gets its own copy"
                    Repeater {
                        model: page.dests
                        Box {
                            required property var modelData
                            required property int index
                            canRemove: page.dests.length > 1
                            onRemove: { var d = page.dests.slice(); d.splice(index, 1); page.dests = d
                                        page.stages = page.stages.filter(function (s) { return s.scope !== index }).map(function (s) { return typeof s.scope === "number" && s.scope > index ? Object.assign({}, s, { scope: s.scope - 1 }) : s }) }
                            Segmented { visible: !Nav.boss; options: [{ value: "mine", label: "A machine you manage" }, { value: "ask", label: "Ask someone to pick" }]
                                        value: modelData.mode; onPicked: function (v) { page.setDest(index, { mode: v }) } }
                            Flow { visible: modelData.mode === "mine"; width: parent.width; spacing: 10
                                   Select { width: Math.min(280, parent.width); search: true; placeholder: "Machine"; value: modelData.pc || null; options: page.hosts; onPicked: function (v) { page.setDest(index, { pc: v }) } }
                                   FolderField { width: Math.min(200, parent.width); pcId: modelData.pc; text: modelData.path; onEdited: function (t) { page.setDest(index, { path: t }) } } }
                            Txt { visible: modelData.mode === "mine" && modelData.pc > 0; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                                  text: Nav.boss ? "You manage every machine, so nobody has to agree." : "If it is not yours, its owner is asked to agree before anything is copied there." }
                            Txt { visible: modelData.mode === "ask"; width: parent.width; color: Theme.med; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                                  text: "Asking the Super User or another Admin to pick a folder on their own workstation is not built in the Engine yet. Pick their machine and folder instead: they are asked to agree." }
                        }
                    }
                    Rectangle { visible: page.dests.length > 8; width: parent.width; height: wt.height + 20; radius: 6; color: Theme.alpha(Theme.med, 0.09)
                                border.width: 1; border.color: Theme.alpha(Theme.med, 0.35)
                                Txt { id: wt; x: 12; y: 10; width: parent.width - 24; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                                      text: "That is a lot of destinations. Every file is copied " + page.dests.length + " times. Consider splitting this into two flows." } }
                    add: Btn { width: parent.width; iconName: "plus"; text: "Add a destination"; onClicked: page.dests = page.dests.concat([{ mode: "mine", pc: 0, path: "", who: 0 }]) }
                }
            }
            // the name, how files are copied, and the checks
            Panel {
                width: parent.width
                title: "Name it and check it"
                sub: page.editId ? "the checks run again against every other flow" : "checked against the one file index before anything is copied"
                Flow {
                    id: nameRow
                    width: parent.width
                    spacing: 28
                    readonly property real half: (width - 28) / 2
                    Column {
                        width: nameRow.half
                        spacing: 8
                        Row { spacing: 12
                              Txt { width: 130; text: "Name"; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                              Field { width: Math.min(320, nameRow.half - 142); enabled: false; placeholderText: page.src.path ? Sync.folder(page.src.path) + "-…" : "my-flow" } }
                        Txt { x: 142; width: parent.width - 142; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                              text: "A flow is named after its source folder for now. A name of its own is not built in the Engine yet." }
                        Row { spacing: 12; topPadding: 6; width: parent.width
                              Txt { width: 130; height: Theme.controlSm; verticalAlignment: Text.AlignVCenter; text: "Copy files"; color: Theme.text3 }
                              Flow { width: parent.width - 142; spacing: 12
                                     Repeater {
                                         model: [["Real time", 96], ["On a schedule", 122], ["Only when I run it", 140]]
                                         Radio { required property var modelData; width: modelData[1]; height: Theme.controlSm
                                                 options: [{ value: modelData[0], label: modelData[0] }]; value: page.when; onPicked: function (v) { page.when = v } }
                                     } } }
                        Txt { x: 142; width: parent.width - 142; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                              text: page.when === "Real time" ? "A file is copied the moment it changes, from the machine's own file events."
                                    : page.when === "On a schedule" ? "Copying on a schedule is not built in the Engine yet; the flow copies in real time."
                                    : "Nothing moves until someone presses Run on the flow." }
                    }
                    Column {
                        width: nameRow.half
                        spacing: 8
                        Repeater {
                            model: [["No loop back to a source, along the whole chain", !page.checks.some(function (c) { return /loop/.test(c[1]) })],
                                    ["No folder written by two flows", !page.checks.some(function (c) { return /already written/.test(c[1]) })],
                                    ["Every source and destination is a different folder", !page.checks.some(function (c) { return /same folder|is the source/.test(c[1]) })]]
                            Row { required property var modelData; spacing: 8
                                  Icon { name: modelData[1] ? "checkcircle" : "closecircle"; size: 15; color: modelData[1] ? Theme.ok : Theme.crit }
                                  Txt { text: modelData[0]; elide: Text.ElideNone } }
                        }
                        Repeater {
                            model: page.checks
                            Rectangle { required property var modelData
                                        width: parent.width; height: ct.height + 20; radius: 6
                                        color: Theme.alpha(modelData[0] === "bad" ? Theme.crit : Theme.med, 0.09)
                                        border.width: 1; border.color: Theme.alpha(modelData[0] === "bad" ? Theme.crit : Theme.med, 0.35)
                                        Txt { id: ct; x: 12; y: 10; width: parent.width - 24; text: modelData[1]; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone } }
                        }
                    }
                }
            }
        }
    }
}
