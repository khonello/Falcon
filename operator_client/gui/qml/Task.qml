pragma Singleton

// WHAT A TASK'S PARTS MEAN, in one place, so the table, the drawer and the proposal all say the same
// thing. A verification item is a machine-readable row; a person reads a sentence.
import QtQuick

QtObject {
    readonly property var phrases: ({
        "file.create": "make",
        "file.update": "change",
        "file.exists": "have",
        "program.used": "use",
        "program.used_with_file": "use",
        "program.installed_available": "have installed",
        "program.closed_not_running": "have closed",
        "program.running": "be running"
    })

    // "make budget-2026.xlsx", "have Excel installed"
    function say(item) {
        if (!item) return ""
        var verb = phrases[item.target_type + "." + item.intent] || item.intent
        var where = item.path ? " in " + item.path : ""
        if (item.intent === "used_with_file") where = " with that file"
        return verb + " " + item.name + where
    }

    function itemTone(status) { return status === "failed" ? "danger" : status === "passed" ? "" : "" }
    function itemWord(status) { return status === "passed" ? "done" : status === "failed" ? "not done" : "waiting" }

    // one place decides what a task's state is
    function state(t) {
        if (!t) return { word: "", tone: "", line: "" }
        var now = new Date()
        var fin = t.final_deadline_at ? new Date(t.final_deadline_at) : null
        var soft = t.soft_deadline_at ? new Date(t.soft_deadline_at) : null
        if (t.status === "completed") return { word: "done", tone: "", line: "verified by the assigner" }
        if (fin && fin < now) return { word: "late", tone: "danger", line: "past the final deadline" }
        if (soft && soft < now) return { word: "due", tone: "warn", line: "past the soft deadline" }
        if (t.status === "in_progress") return { word: "started", tone: "", line: "the assignee has started" }
        return { word: "not started", tone: "", line: "assigned, not started" }
    }

    function when(iso) {
        if (!iso) return ""
        var d = new Date(iso)
        return Qt.formatDateTime(d, "d MMM, HH:mm")
    }
}
