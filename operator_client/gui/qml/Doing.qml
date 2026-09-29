pragma Singleton

// WHAT AN ACTION AND AN EVENT ARE CALLED, in one place. The Engine's names are wire identifiers --
// `lock_session`, `threshold.cpu` -- and nobody says those out loud. The console says them the way a
// person would, and every page says them the same way. (Named Doing, not Control: QtQuick has enough
// Controls already.)
import QtQuick

QtObject {
    // the built-in Actions, by the Engine's own key
    readonly property var actionNames: ({
        "screenshot": "Take a screenshot",
        "notify": "Show them a message",
        "lock_session": "Lock the screen",
        "rename_file": "Rename a file",
        "restore_file": "Put a file back",
        "kill_process": "Stop a program",
        "start_process": "Start a program",
        "shutdown": "Shut the machine down",
        "reboot": "Restart the machine",
        "process_list": "List what is running",
        "system_metrics": "Read the machine's levels",
        "file_activity": "Watch a folder",
        "idle_time": "Read how long it has been idle",
        "snapshot_file": "Take a copy of a file",
        "usb_contents": "List what is on the USB"
    })

    // the things that can set an automation off
    readonly property var eventNames: ({
        "file.created": "a file appears", "file.modified": "a file changes",
        "file.moved": "a file moves", "file.copied": "a file is copied",
        "file.deleted": "a file is deleted", "file.accessed": "a file is opened",
        "usb.inserted": "a USB goes in", "usb.removed": "a USB comes out",
        "user.login": "somebody signs in", "user.logout": "somebody signs out",
        "program.launched": "a program starts", "program.exited": "a program closes",
        "network.connected": "the network comes back", "network.disconnected": "the network drops",
        "task.started": "a task is started", "task.target_appeared": "a task's file appears",
        "task.deadline_soft": "a task's nudge comes round", "task.deadline_final": "a task falls due",
        "flow.failed": "a flow stops", "resource.violation": "a file turns up where it should not",
        "system.idle": "the machine goes idle", "threshold.cpu": "the CPU stays high",
        "threshold.memory": "memory stays high", "time.scheduled": "a time comes round",
        "time.recurring": "every so often"
    })

    // the words on the wire, when the console has nothing better
    function plain(key, book) {
        var word = book[key]
        return word ? word : String(key).replace(/[._]/g, " ")
    }
    function actionName(a) {
        if (!a) return ""
        if (a.name) return a.name
        if (a.action_kind === "custom") return "a script"
        return plain(a.builtin_type, actionNames)
    }
    function eventName(type) { return plain(type, eventNames) }

    function kindWord(kind) {
        return kind === "control" ? "does something" : kind === "monitoring" ? "reports something"
                                                                            : "a script of your own"
    }

    // a built-in's parameters, said as a label rather than a key
    function paramLabel(name) {
        var book = { "message": "What it says", "duration_s": "For how long, in seconds",
                     "path": "Which file or folder", "new_name": "The new name",
                     "name": "Which program", "command": "What to run" }
        return book[name] || String(name).replace(/_/g, " ")
    }

    // where an automation watches, and what it watches for
    function scope(spec) {
        if (!spec) return "every machine"
        var pcs = spec.pc_ids
        return !pcs || pcs.length === 0 ? "every machine"
               : pcs.length === 1 ? "one machine" : pcs.length + " machines"
    }
}
