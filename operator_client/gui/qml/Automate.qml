pragma Singleton
import QtQuick

// The words for automation (boards AU04-AU10): what can set one off, said as a sentence, and what each
// action does, said as a person would. Automation and Actions both read from here, so a thing is never
// called two names. Nothing here is typed by the user: every trigger is a pick from these lists.
//
// A file being OPENED is not offered: the Engine cannot see a file being read (only created, changed,
// moved, copied, deleted), so a trigger on it would never fire.
QtObject {
    // the first blank of the sentence: what kind of thing happens
    readonly property var kinds: [
        { key: "file", text: "a file", icon: "file" },
        { key: "usb", text: "a USB drive", icon: "key" },
        { key: "program", text: "a program", icon: "window" },
        { key: "user", text: "someone", icon: "user" },
        { key: "network", text: "the network", icon: "globe" },
        { key: "time", text: "a time", icon: "clock" },
        { key: "machine", text: "the machine", icon: "cpu" },
        { key: "work", text: "a task or a flow", icon: "tasks" }
    ]
    // the second blank, per kind: what happens to it, and the event type it means
    readonly property var verbs: ({
        file: [{ type: "file.created", text: "is created" }, { type: "file.modified", text: "is changed" },
               { type: "file.moved", text: "is moved" }, { type: "file.copied", text: "is copied" },
               { type: "file.deleted", text: "is deleted" }],
        usb: [{ type: "usb.inserted", text: "is plugged in" }, { type: "usb.removed", text: "is taken out" }],
        program: [{ type: "program.launched", text: "starts" }, { type: "program.exited", text: "closes" }],
        user: [{ type: "user.login", text: "signs in" }, { type: "user.logout", text: "signs out" }],
        network: [{ type: "network.connected", text: "connects" }, { type: "network.disconnected", text: "drops" }],
        time: [{ type: "time.recurring", text: "comes round" }, { type: "time.scheduled", text: "arrives, once" }],
        machine: [{ type: "threshold.cpu", text: "stays busy" }, { type: "threshold.memory", text: "runs low on memory" },
                  { type: "system.idle", text: "sits idle" }],
        work: [{ type: "task.started", text: "is started" }, { type: "task.deadline_soft", text: "reaches its first deadline" },
               { type: "task.deadline_final", text: "passes its final deadline" }, { type: "flow.failed", text: "fails" },
               { type: "resource.violation", text: "puts a file out of place" }]
    })
    readonly property var tiers: [
        { key: "restricted", text: "Restricted", tone: "danger" }, { key: "admin", text: "Admin", tone: "warn" },
        { key: "workers", text: "Workers", tone: "accent" }, { key: "common", text: "Common", tone: "ok" }
    ]
    readonly property var dayNames: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    function kindOf(type) {
        for (var k in verbs) for (var i = 0; i < verbs[k].length; i++) if (verbs[k][i].type === type) return k
        return "file"
    }
    function verbOf(type) {
        var v = verbs[kindOf(type)] || []
        for (var i = 0; i < v.length; i++) if (v[i].type === type) return v[i].text
        return type
    }
    function kindText(key) { for (var i = 0; i < kinds.length; i++) if (kinds[i].key === key) return kinds[i].text; return key }
    function iconFor(type) { var k = kindOf(type); for (var i = 0; i < kinds.length; i++) if (kinds[i].key === k) return kinds[i].icon; return "bell" }
    function tierText(key) { for (var i = 0; i < tiers.length; i++) if (tiers[i].key === key) return tiers[i].text; return key }
    function folderName(p) { var s = String(p || "").replace(/\\/g, "/").replace(/\/$/, ""); return s.split("/").pop() || s }
    function minutes(s) {
        s = Number(s || 0)
        return s >= 3600 && s % 3600 === 0 ? (s / 3600) + (s === 3600 ? " hour" : " hours") : s >= 60 ? Math.round(s / 60) + " min" : s + " s"
    }
    function days(list) {
        if (!list || list.length === 0 || list.length === 7) return "Every day"
        var sorted = list.slice().sort()
        if (sorted.join() === "0,1,2,3,4") return "Weekdays"
        if (sorted.join() === "5,6") return "Weekends"
        return sorted.map(function (d) { return dayNames[d] }).join(", ")
    }

    // An automation's trigger as a line to read: { title, sub }. `where` is how its machines read
    // ("every machine", "OPS-03, OPS-07"), worked out by the page that knows the department.
    function when(spec, where) {
        var t = spec.type, m = spec.match || {}
        var title, sub = where
        if (t.indexOf("file.") === 0) {
            title = (m.tier ? "A " + tierText(m.tier).toLowerCase() + " file " : "A file ") + verbOf(t)
            if (m.path_prefix) sub = "in " + folderName(m.path_prefix) + " · " + where
        } else if (t === "time.recurring") {
            title = m.interval_s ? "Every " + minutes(m.interval_s) : days(m.days) + " at " + m.at
        } else if (t === "time.scheduled") {
            var d = new Date(m.at)
            title = "Once, " + Qt.formatDateTime(d, "d MMM") + " at " + Qt.formatDateTime(d, "HH:mm")
        } else if (t === "threshold.cpu") {
            title = "The processor stays busy"; sub = "above " + (m.percent || 80) + " %" + (m.duration_s ? " for " + minutes(m.duration_s) : "")
        } else if (t === "threshold.memory") {
            title = "Memory runs low"; sub = "above " + (m.percent || 80) + " % used"
        } else if (t === "system.idle") {
            title = "A machine sits idle"; sub = "for " + minutes(m.seconds || 600) + " · " + where
        } else if (t === "program.launched" || t === "program.exited") {
            title = (m.process ? m.process + " " : "A program ") + verbOf(t)
        } else if (t === "user.login" || t === "user.logout") {
            title = "Someone " + verbOf(t)
        } else if (t.indexOf("task.") === 0) {
            title = "A task " + verbOf(t); sub = m.task_id ? "task " + m.task_id : "any of your tasks"
        } else if (t === "flow.failed") {
            title = "A flow fails"; sub = "any of your flows"
        } else if (t === "resource.violation") {
            title = "A file lands out of place"; sub = "anywhere in your department"
        } else {
            title = kindText(kindOf(t)).replace(/^a /, "A ").replace(/^the /, "The ") + " " + verbOf(t)
        }
        return { title: title.charAt(0).toUpperCase() + title.slice(1), sub: sub }
    }

    // --- actions -----------------------------------------------------------------------------------
    readonly property var builtinWords: ({
        notify: { text: "Notify", does: "shows a message on their screen", done: "notified", icon: "bell" },
        lock_session: { text: "Lock the screen", does: "for a set time, with a message", done: "screen locked", icon: "lock", short: "the lock" },
        screenshot: { text: "Screenshot", does: "a still of their screen, now", done: "screenshot taken", icon: "camera" },
        rename_file: { text: "Rename a file", does: "gives a file a new name", done: "file renamed", icon: "file" },
        restore_file: { text: "Restore a file", does: "puts the last good copy back", done: "file restored", icon: "file" },
        kill_process: { text: "Close a program", does: "ends it, unsaved work is lost", done: "program closed", icon: "x" },
        start_process: { text: "Start a program", does: "opens it on their machine", done: "program started", icon: "play" },
        shutdown: { text: "Shut down", does: "turns the machine off", done: "shut down", icon: "power" },
        reboot: { text: "Restart", does: "turns it off and on again", done: "restarted", icon: "power" },
        process_list: { text: "Programs running", does: "what is open, and for how long", done: "programs listed", icon: "window" },
        system_metrics: { text: "System load", does: "processor and memory, now", done: "load read", icon: "cpu" },
        file_activity: { text: "File activity", does: "what changed in a folder", done: "activity read", icon: "file" },
        idle_time: { text: "Idle time", does: "how long since they touched it", done: "idle time read", icon: "clock" },
        snapshot_file: { text: "Snapshot a file", does: "keeps a copy as it is now", done: "file kept", icon: "camera" },
        usb_contents: { text: "USB contents", does: "what is on the drive", done: "drive listed", icon: "key" }
    })
    function actionName(a) {
        if (!a) return ""
        var w = builtinWords[a.builtin_type]
        return a.name && a.name !== a.builtin_type ? a.name : (w ? w.text : a.name || "an action")
    }
    function actionIcon(a) {
        if (a && (a.action_kind === "custom" || a.kind === "custom")) return "terminal"
        var w = a ? builtinWords[a.builtin_type] : null
        return w ? w.icon : "play"
    }
    function actionDoes(a) {
        if (a && (a.action_kind === "custom" || a.kind === "custom"))
            return "your script · " + (a.custom_script_language === "powershell" ? "PowerShell" : "Python")
        var w = a ? builtinWords[a.builtin_type] : null
        return w ? w.does : ""
    }
    // "right away · gives up after 1 min"
    function actionTiming(a) {
        var t = a && a.timing && a.timing.mode === "delayed" ? "after " + minutes(a.timing.delay_s) : "right away"
        return a && a.timeout_seconds ? t + " · gives up after " + minutes(a.timeout_seconds) : t
    }
    // one run, as a few words: "screen locked" / "the lock timed out" / "Clear temp failed"
    function outcome(run) {
        var w = builtinWords[run.builtin_type]
        var name = run.action_name && run.action_name !== run.builtin_type ? run.action_name : (w ? w.text : "the action")
        if (run.status === "pending") return name.toLowerCase() + " running"
        if (run.status === "terminated") return (w && w.short ? w.short : name.toLowerCase()) + (run.terminated_reason === "timeout" ? " timed out" : " stopped")
        if (run.status === "failed") return name.toLowerCase() + " failed"
        return w ? w.done : name.toLowerCase() + " done"
    }
}
