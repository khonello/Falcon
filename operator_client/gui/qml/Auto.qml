pragma Singleton

// HOW AN AUTOMATION READS. The Engine keeps a condition (`type`, `pc_ids`, `match`) and its actions;
// this says it as the concept does -- "When a USB storage device is inserted on a Operations machine,
// do Take a screenshot" -- and sorts what each run came to.
import QtQuick

QtObject {
    readonly property var when: ({
        "usb.inserted": "a USB storage device is inserted", "usb.removed": "a USB storage device is removed",
        "user.login": "a user signs in", "user.logout": "a user signs out",
        "program.launched": "a program starts", "program.exited": "a program closes",
        "network.connected": "the machine joins a network", "network.disconnected": "the machine loses its network",
        "file.created": "a file is created in a folder", "file.modified": "a file changes in a folder", "file.moved": "a file is moved",
        "file.copied": "a file is copied", "file.deleted": "a file is deleted", "file.accessed": "a file is opened",
        "file.attributes_changed": "a file's attributes change", "file.permissions_changed": "a file's permissions change",
        "folder.created": "a folder is created", "folder.moved": "a folder is moved", "folder.deleted": "a folder is deleted",
        "resource.violation": "a copy of a restricted file appears where it is not allowed", "flow.failed": "a flow stops copying",
        "task.started": "a task is started", "task.target_appeared": "a task's target appears",
        "task.deadline_soft": "a task reaches its soft deadline", "task.deadline_final": "a task reaches its final deadline",
        "system.idle": "the machine goes idle", "threshold.cpu": "CPU stays high", "threshold.memory": "memory stays high",
        "time.scheduled": "it is a set time", "time.recurring": "it is a set time"
    })
    readonly property var names: ({
        "usb.inserted": "USB device inserted", "resource.violation": "Restricted file copied where it isn't allowed",
        "threshold.cpu": "Sustained high CPU", "threshold.memory": "Sustained high memory", "time.recurring": "Scheduled run",
        "time.scheduled": "One-time run", "user.login": "User signs in", "user.logout": "User signs out", "system.idle": "Machine goes idle",
        "program.launched": "Program starts", "flow.failed": "Flow stopped"
    })
    function kind(type) { return /^threshold|^system\.idle/.test(type) ? "Threshold" : /^time\./.test(type) ? "Schedule" : "Event" }
    function kindIcon(k) { return k === "Threshold" ? "linechart" : k === "Schedule" ? "clock" : "thunderbolt" }
    function kindColor(k) { return k === "Threshold" ? Theme.ser4 : k === "Schedule" ? Theme.ser2 : Theme.ser3 }
    readonly property var dayNames: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    function nameOf(e) {
        var s = e.condition_spec || {}
        return e.name || names[s.type] || (s.type ? (when[s.type] || s.type).replace(/^a /, "").replace(/^./, function (x) { return x.toUpperCase() }) : "Automation")
    }
    function whenOf(e) {
        var s = e.condition_spec || {}, m = s.match || {}
        if (s.type === "threshold.cpu" || s.type === "threshold.memory")
            return (s.type === "threshold.cpu" ? "CPU" : "memory") + " stays above " + (m.percent || 80) + "%" + (m.duration_s ? " for " + Math.round(m.duration_s / 60) + " minutes" : "")
        if (s.type === "system.idle") return "the machine is idle for " + Math.round((m.seconds || 600) / 60) + " minutes"
        if (s.type === "time.recurring") {
            if (m.interval_s) return "every " + Math.round(m.interval_s / 60) + " minutes"
            var ds = m.days || []
            return "it is " + (m.at || "?") + " on " + (!ds.length || ds.length === 7 ? "any day" : ds.length === 5 && ds.indexOf(5) < 0 && ds.indexOf(6) < 0 ? "a weekday" : ds.map(function (d) { return dayNames[d] }).join(", "))
        }
        if (s.type === "time.scheduled") return "it is " + Time.atDay(m.at)
        var w = when[s.type] || s.type
        if (m.process) w += " (" + m.process + ")"
        if (m.path_prefix) w += " under " + m.path_prefix
        return w
    }
    function whereOf(e) {
        var ids = (e.condition_spec || {}).pc_ids
        if (!ids || !ids.length) return e.org_wide ? "any machine" : "any machine here"
        var hs = ids.map(function (p) { return Fleet.byPc[p] ? Fleet.byPc[p].host : "PC " + p })
        return hs.length > 3 ? hs.slice(0, 3).join(", ") + " and " + (hs.length - 3) + " more" : hs.join(", ")
    }
    // where it runs, as the side panel says it: a whole department as "Operations · 7 here", else the machines
    function whereFact(e) {
        var ids = (e.condition_spec || {}).pc_ids
        var d = Fleet.depts.length === 1 ? Fleet.depts[0] : null
        if (d && (!ids || !ids.length || d.machines.every(function (m) { return ids.indexOf(m.pc_id) >= 0 }))) return d.name + " · " + d.machines.length + " here"
        return whereOf(e).replace(/^./, function (x) { return x.toUpperCase() })
    }
    function sentence(e) { return "When " + whenOf(e) + " on " + whereOf(e) + ", do " + (e.actions || []).map(function (a) { return a.name }).join(", ") }

    // a run's outcome, in the concept's four words
    function outcome(ex) {
        var st = ex.status
        if (st === "success") return "Success"
        if (st === "terminated") return "Stopped by you"
        if (st === "pending") return "Running"
        if (ex.timed_out || /time ?out/i.test(String(ex.summary || ex.result_summary || ex.error || ""))) return "Timed out"
        return "Failed"
    }
    function outColor(o) { return o === "Success" ? Theme.ok : o === "Failed" ? Theme.crit : o === "Timed out" ? Theme.med : o === "Running" ? Theme.ser1 : Theme.ser3 }
    function problem(o) { return o === "Failed" || o === "Timed out" }
    function summarize(runs) {
        var c = {}
        runs.forEach(function (x) { var o = outcome(x); c[o] = (c[o] || 0) + 1 })
        return ["Timed out", "Failed", "Stopped by you", "Running", "Success"].filter(function (k) { return c[k] }).map(function (k) { return [k, c[k]] })
    }
    function lastRunText(runs) {
        var s = summarize(runs)
        return s.length === 1 && s[0][0] === "Success" ? (s[0][1] === 1 ? "Succeeded" : "All " + s[0][1] + " succeeded") : s.map(function (x) { return x[1] + " " + x[0].toLowerCase() }).join(", ")
    }
}
