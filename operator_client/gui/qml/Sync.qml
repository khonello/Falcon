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

    // a folder, said the way a person says it
    function folder(path) {
        if (!path) return ""
        var p = String(path).replace(/\\/g, "/")
        var bits = p.split("/").filter(function (b) { return b.length > 0 })
        return bits.length > 0 ? bits[bits.length - 1] : p
    }
}
