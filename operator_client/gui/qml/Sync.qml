pragma Singleton

// WHAT A FLOW'S PARTS MEAN, in one place. (Named Sync, not Flow: QtQuick already has a Flow.) A flow is one direction: a folder on one machine lands in
// folders on others. The Engine already writes the suggestion for a failure -- the console never
// invents its own words for one.
import QtQuick

QtObject {
    // one place decides what a flow's state is
    function state(f) {
        if (!f) return { word: "", tone: "", line: "" }
        if (f.status === "inactive") return { word: "retired", tone: "", line: "kept, but not running" }
        if (f.consent_status === "pending")
            return { word: "waiting", tone: "warn", line: "the other side has not said yes yet" }
        if (f.status === "paused")
            return { word: "stopped", tone: "danger", line: f.suggestion || reason(f.pause_reason) }
        return { word: "running", tone: "", line: "copying as files change" }
    }

    // a pause reason is "<stage>:<kind>"; the Engine's suggestion is the sentence, this is the fallback
    function reason(raw) {
        if (!raw) return "stopped"
        var parts = String(raw).split(":")
        if (parts[0] === "consent") return "nobody has said yes yet"
        return parts[1] ? parts[1].replace(/_/g, " ") + ", at the " + parts[0] : String(raw)
    }

    function where(d) {
        if (!d) return ""
        return (d.destination_hostname || "remote storage") + "  " + d.destination_path
    }

    // THE STEPS ALONG THE WAY. The builder holds them as a list, [{kind, op, scope: "all" | destination index}];
    // the Engine holds a tree (each stage and each destination points at its parent stage). A step's name is kept
    // in its config as `op`, so it comes back as it was picked; `by` is what the Worker already reads.
    readonly property var stepOps: ({ Transform: ["Rename by date", "Convert to PDF", "Compress to ZIP"], Categorize: ["Sort by file type", "Sort by month"] })
    function stepKind(st) { return st.stage_type === "categorization" ? "Categorize" : "Transform" }
    function stepName(st) {
        var c = st.config || {}
        if (typeof c === "string") { try { c = JSON.parse(c) } catch (e) { c = {} } }
        if (c.op) return c.op
        if (st.stage_type === "categorization") return c.by === "month" ? "Sort by month" : "Sort by file type"
        return c.to ? "Convert to " + String(c.to).toUpperCase() : "Transform"
    }
    function stageOut(s, parent) {
        var cfg = { op: s.op }
        if (s.op === "Sort by file type") cfg.by = "extension"
        return { stage_type: s.kind === "Categorize" ? "categorization" : "transformation", parent_index: parent, config: cfg }
    }
    // the Engine's tree as the builder's list. Only stages a live destination reaches count: an edit re-creates
    // the stages and the old ones stay on record, unreached. A stage every destination passes is before the split.
    function steps(f) {
        if (!f) return []
        var by = {}
        ;(f.stages || []).forEach(function (s) { by[s.id] = s })
        var chains = (f.destinations || []).map(function (d) {
            var out = [], cur = d.parent_stage_id, guard = 0
            while (cur !== null && cur !== undefined && by[cur] && guard++ < 64) { if (by[cur].stage_type !== "branch") out.unshift(cur); cur = by[cur].parent_stage_id }
            return out
        })
        var ids = []
        chains.forEach(function (c) { c.forEach(function (id) { if (ids.indexOf(id) < 0) ids.push(id) }) })
        ids.sort(function (a, b) { return a - b })
        return ids.map(function (id) {
            var all = chains.every(function (c) { return c.indexOf(id) >= 0 })
            var first = 0
            while (first < chains.length && chains[first].indexOf(id) < 0) first++
            return { kind: stepKind(by[id]), op: stepName(by[id]), scope: all ? "all" : first }
        })
    }
    // the builder's list as the Engine's tree: the shared steps one after another, then each destination's own
    // steps after them, one after another. Answers the stages and, per destination, the stage it hangs off.
    function plan(list, nDests) {
        var out = [], last = null
        list.forEach(function (s) { if (s.scope === "all") { out.push(stageOut(s, last)); last = out.length - 1 } })
        var parents = []
        for (var i = 0; i < nDests; i++) {
            var p = last
            list.forEach(function (s) { if (s.scope === i) { out.push(stageOut(s, p)); p = out.length - 1 } })
            parents.push(p)
        }
        return { stages: out, parents: parents }
    }

    // a folder, said the way a person says it
    function folder(path) {
        if (!path) return ""
        var p = String(path).replace(/\\/g, "/")
        var bits = p.split("/").filter(function (b) { return b.length > 0 })
        return bits.length > 0 ? bits[bits.length - 1] : p
    }
}
