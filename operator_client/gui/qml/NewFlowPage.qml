import QtQuick
import "."

// NEW FLOW (and Edit). Four parts on the left -- where the files come from, what happens on the way,
// where they go, then the checks -- and the flow drawn on the right as it is built. Every change is
// checked against the other flows for a folder written twice or a loop back to a source, before it is
// saved; the Engine runs the same checks again.
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

    component Head: Column {
        property string t: ""
        property string d: ""
        width: parent ? parent.width : 0
        spacing: 2
        bottomPadding: 16
        Txt { text: parent.t; font.pixelSize: Theme.fTitle; font.weight: Font.DemiBold; width: parent.width }
        Txt { text: parent.d; color: Theme.text3; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone }
    }
    component Num: Rectangle {
        property int n: 1
        width: 22; height: 22; radius: 4; color: Theme.surface3
        Txt { anchors.centerIn: parent; text: String(parent.n); mono: true; font.pixelSize: 12; elide: Text.ElideNone }
    }
    component Box: Rectangle {
        default property alias inner: bc.data
        width: parent ? parent.width : 0
        height: bc.height + 28
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.border
        Column { id: bc; x: 14; y: 14; width: parent.width - 28; spacing: 10 }
    }

    EditorShell {
        width: parent.width
        ratio: 0.5
        problem: page.problem
        note: page.checks.length ? "" : "No loop, no folder written twice, every folder different"
        saveLabel: page.editId ? "Save changes" : "Create flow"
        onCancel: page.cancel()
        onSave: page.save()
        leftPane: Rectangle {
            width: parent.width
            height: secs.height
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.border
            Column {
                id: secs
                width: parent.width
                // 1. sources
                Column {
                    x: 24; width: parent.width - 48; topPadding: 22; bottomPadding: 22; spacing: 12
                    Head { t: "Where do the files come from?"; d: "A folder on a machine you manage. Files go the same way from it; nothing is copied back." }
                    Box {
                        Row { spacing: 10
                              Num { n: 1 }
                              Segmented { options: [{ value: "dir", label: "A folder" }, { value: "flow", label: "An existing flow" }]; value: "dir"
                                          onPicked: function (v) { if (v === "flow") { Msg.warn("Continuing another flow is not built in the Engine yet"); value = "dir" } } } }
                        Row { x: 32; spacing: 10
                              Select { width: 260; search: true; placeholder: "Machine"; value: page.src.pc || null; options: page.hosts; enabled: !page.editId
                                       onPicked: function (v) { page.src = { pc: v, path: page.src.path } } }
                              FolderField { width: 200; pcId: page.src.pc; text: page.src.path; placeholder: "Folder"
                                            onEdited: function (t) { page.src = { pc: page.src.pc, path: t } } } }
                    }
                    Row { spacing: 10
                          Btn { iconName: "plus"; text: "Add a source"; enabled: false; tip: "Several sources are not built in the Engine yet" }
                          Txt { text: "1 source"; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } }
                    Row { spacing: 12
                          Txt { width: 130; text: "Copy files"; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                          Segmented { small: false; options: ["Real time", "On a schedule", "Only when I run it"]; value: page.when; onPicked: function (v) { page.when = v } } }
                    Txt { x: 142; width: parent.width - 142; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                          text: page.when === "Real time" ? "A file is copied the moment it changes, from the machine's own file events."
                                : page.when === "On a schedule" ? "Copying on a schedule is not built in the Engine yet; the flow copies in real time."
                                : "Nothing moves until someone presses Run on the flow." }
                }
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                // 2. along the way
                Column {
                    x: 24; width: parent.width - 48; topPadding: 22; bottomPadding: 22; spacing: 12
                    Head { t: "Should anything happen to the files on the way?"; d: "Optional. A step before the split applies to every destination; a step on one branch applies to that destination only." }
                    Rectangle { visible: page.stages.length === 0; width: parent.width; height: 46; radius: Theme.radius; color: "transparent"; border.width: 1; border.color: Theme.borderStrong
                                Txt { anchors.centerIn: parent; text: "No steps. Files are copied exactly as they are."; color: Theme.text3 } }
                    Repeater {
                        model: page.stages
                        Box {
                            required property var modelData
                            required property int index
                            Row { spacing: 10; width: parent.width
                                  Num { n: index + 1 }
                                  Select { width: 130; value: modelData.kind; options: ["Transform", "Categorize"]; onPicked: function (v) { page.setStage(index, { kind: v, op: page.stageOps[v][0] }) } }
                                  Select { width: 200; value: modelData.op; options: page.stageOps[modelData.kind].indexOf(modelData.op) < 0 ? [modelData.op].concat(page.stageOps[modelData.kind]) : page.stageOps[modelData.kind]
                                           onPicked: function (v) { page.setStage(index, { op: v }) } }
                                  Item { width: parent.width - 410; height: 1 }
                                  Btn { small: true; kind: "text"; iconName: "close"; onClicked: { var s = page.stages.slice(); s.splice(index, 1); page.stages = s } } }
                            // the destination picker wraps under the switch when the box is narrow, as the concept's row does
                            Flow { width: parent.width; spacing: 8
                                  Txt { height: aseg.height; verticalAlignment: Text.AlignVCenter; text: "Applies to"; color: Theme.text3; font.pixelSize: 12 }
                                  Segmented { id: aseg; options: [{ value: "all", label: "Every destination (before the split)" }, { value: "one", label: "One destination" }]
                                              value: modelData.scope === "all" ? "all" : "one"; onPicked: function (v) { page.setStage(index, { scope: v === "all" ? "all" : 0 }) } }
                                  Select { visible: modelData.scope !== "all"; width: 200; small: true; value: modelData.scope
                                           options: page.dests.map(function (d, j) { return { value: j, label: d.mode === "ask" ? "Destination " + (j + 1) : d.pc ? page.hostName(d.pc) + " " + d.path : "Destination " + (j + 1) } })
                                           onPicked: function (v) { page.setStage(index, { scope: v }) } } }
                        }
                    }
                    Btn { iconName: "plus"; text: "Add a step"; onClicked: page.stages = page.stages.concat([{ kind: "Transform", op: "Rename by date", scope: "all" }]) }
                    Txt { visible: page.stages.length > 0; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                          text: "Each step is kept with the flow by name and drawn where it applies. Of these, the Worker carries out Sort by file type today; the others are not built in the Worker yet and leave the files as they are." }
                }
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                // 3. destinations
                Column {
                    x: 24; width: parent.width - 48; topPadding: 22; bottomPadding: 22; spacing: 12
                    Head { t: "Where should the files go?"; d: Nav.boss ? "Each destination gets its own copy of every file. You manage every machine, so any of them can be picked without asking."
                                                                        : "Each destination gets its own copy of every file. A machine you manage needs nobody to agree; a machine that is not yours asks its owner first." }
                    Repeater {
                        model: page.dests
                        Box {
                            required property var modelData
                            required property int index
                            Row { spacing: 10; width: parent.width
                                  Num { n: index + 1 }
                                  Segmented { visible: !Nav.boss; options: [{ value: "mine", label: "A machine you manage" }, { value: "ask", label: "Ask someone to pick" }]
                                              value: modelData.mode; onPicked: function (v) { page.setDest(index, { mode: v }) } }
                                  Item { width: parent.width - (Nav.boss ? 70 : 380); height: 1 }
                                  Btn { small: true; kind: "text"; iconName: "close"; enabled: page.dests.length > 1
                                        onClicked: { var d = page.dests.slice(); d.splice(index, 1); page.dests = d; page.stages = page.stages.filter(function (s) { return s.scope !== index }) } } }
                            Row { visible: modelData.mode === "mine"; x: 32; spacing: 10
                                  Select { width: 260; search: true; placeholder: "Machine"; value: modelData.pc || null; options: page.hosts; onPicked: function (v) { page.setDest(index, { pc: v }) } }
                                  FolderField { width: 200; pcId: modelData.pc; text: modelData.path; onEdited: function (t) { page.setDest(index, { path: t }) } } }
                            Txt { visible: modelData.mode === "mine" && modelData.pc > 0; x: 32; color: Theme.text3; font.pixelSize: 12
                                  text: Nav.boss ? "You manage every machine, so nobody has to agree." : "If it is not yours, its owner is asked to agree before anything is copied there." }
                            Txt { visible: modelData.mode === "ask"; x: 32; width: parent.width - 32; color: Theme.med; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                                  text: "Asking the Super User or another Admin to pick a folder on their own workstation is not built in the Engine yet. Pick their machine and folder instead: they are asked to agree." }
                        }
                    }
                    Row { spacing: 10
                          Btn { iconName: "plus"; text: "Add a destination"; onClicked: page.dests = page.dests.concat([{ mode: "mine", pc: 0, path: "", who: 0 }]) }
                          Txt { text: Theme.many(page.dests.length, "destination") + (page.dests.length > 1 ? ", so the flow branches" : ""); color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } }
                    Rectangle { visible: page.dests.length > 8; width: parent.width; height: 40; radius: 6; color: Theme.alpha(Theme.med, 0.09)
                                Txt { x: 12; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 24; font.pixelSize: 12
                                      text: "That is a lot of destinations. Every file is copied " + page.dests.length + " times. Consider splitting this into two flows." } }
                }
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                // 4. check
                Column {
                    x: 24; width: parent.width - 48; topPadding: 22; bottomPadding: 22; spacing: 8
                    Head { t: "Name it and check it"; d: page.editId ? "The checks run again against every other flow. The flow keeps running as it was until you save." : "These checks run against every other flow before anything is copied." }
                    Row { spacing: 12
                          Txt { width: 130; text: "Name"; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                          Field { width: 320; enabled: false; placeholderText: page.src.path ? Sync.folder(page.src.path) + "-…" : "my-flow" } }
                    Txt { x: 142; width: parent.width - 142; bottomPadding: 10; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                          text: "A flow is named after its source folder for now. A name of its own is not built in the Engine yet." }
                    Repeater {
                        model: [["No loop back to the source, along the whole chain", !page.checks.some(function (c) { return /loop/.test(c[1]) })],
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
        rightPane: Rectangle {
            width: parent.width
            height: rc.height + 28
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.border
            Column {
                id: rc
                x: 16; y: 14
                width: parent.width - 32
                spacing: 8
                Row { spacing: 8
                      Txt { text: "The flow so far"; font.weight: Font.DemiBold; elide: Text.ElideNone }
                      Txt { text: "files only move left to right"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter } }
                Txt { visible: page.editId > 0; width: parent.width; color: Theme.text3; font.pixelSize: 12; textFormat: Text.StyledText
                      text: "Editing <b>" + (page.flows.filter(function (x) { return x.id === page.editId }).map(page.flowName)[0] || "this flow") + "</b>. It keeps running as it was until you save." }
                Select { visible: !page.editId; width: 240; small: true; search: true; placeholder: "Start from a copy of a flow"; value: page.copyOf || null
                         options: (page.copyOf ? [{ value: 0, label: "Start blank" }] : []).concat(page.flows.map(function (x) { return { value: x.id, label: "Copy of " + page.flowName(x) } }))
                         onPicked: function (v) { page.startFrom(v) } }
                FlowPreview {
                    width: parent.width
                    srcs: [{ host: page.src.pc ? page.hostName(page.src.pc) : "", path: page.src.path }]
                    stages: page.stages
                    dests: page.dests.map(function (d) { return d.mode === "ask" ? { host: "Someone", ask: true } : { host: d.pc ? page.hostName(d.pc) : "", path: d.path } })
                }
                Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12
                      text: page.bad.length ? page.bad.length + " problem" + (page.bad.length === 1 ? "" : "s") + " to fix, listed at the bottom of the form" : "No loop, no folder written twice, every folder different" }
            }
        }
    }
}
