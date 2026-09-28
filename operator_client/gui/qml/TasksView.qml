import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// TASKS (boards TK04 the page, TK05 describing one, TK06 one task). An Admin's -- and a Super User inside one sees it.
//
//   list  four cells: Needs you (to verify, given to you), Deadlines, By person, Closed (hands off to Record)
//   new   side by side: your words, and the structure the local model filled; whatever it could not settle is a
//         DECISION, worked down one at a time, each asked on the line it is about; a detected split is drafted;
//         Confirm waits for every decision. Nothing is committed on the model's say-so.
//   task  the checks and the files on the left, the verdict the full height on the right -- only the assigner closes it
//
// Never the assigner on a list: on your own page it is always you. A task given TO you names who gave it.
Item {
    id: root

    property string mode: "list"            // list | new | task
    property var tasks: []
    property var closed: []
    property var task: null                 // task.get
    property var tree: []
    property string clock: ""

    // --- data -------------------------------------------------------------------------------------
    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("task.list", {}, function (ok, r) { if (ok) root.tasks = r.tasks; else shell.notify(r.message, true) })
        falcon.call("task.list", { include_completed: true }, function (ok, r) {
            if (ok) root.closed = r.tasks.filter(function (t) { return t.status === "completed" })
        })
        falcon.call("hierarchy.tree", {}, function (ok, r) { if (ok) root.tree = r.departments })
    }
    function open(id) {
        falcon.call("task.get", { task_id: id }, function (ok, r) {
            if (ok) { root.task = r.task; root.mode = "task"; root.recheck(true) } else shell.notify(r.message, true)
        })
    }
    // THE VERIFICATION STACK (task.stack): the checks re-evaluated against the file index as it is
    // now. Signs of work, never proof of it -- the verdict stays the assigner's, which is why this
    // only ever changes what the checks SAY, never the task's status.
    property string checkedAt: ""
    function recheck(quiet) {
        if (!root.task) return
        var id = root.task.id
        falcon.call("task.stack", { task_id: id }, function (ok, r) {
            if (!ok) { if (!quiet) shell.notify(r.message, true); return }
            if (!root.task || root.task.id !== id) return
            var t = {}
            for (var k in root.task) t[k] = root.task[k]
            t.items = r.items
            root.task = t
            root.checkedAt = Qt.formatTime(new Date(), "HH:mm")
            if (!quiet) shell.notify("Checked again", false)
        })
    }
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onScopeChanged() { if (falcon.isConnected) root.refresh() }
        function onPushReceived(type, p) {
            if (type.indexOf("task.") === 0) { root.refresh(); if (root.task && p.task_id === root.task.id) root.open(root.task.id) }
        }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Keys.onEscapePressed: root.mode = "list"
    focus: true

    readonly property int me: shell.heldAdmin ? shell.heldAdmin.account_id : falcon.accountId
    readonly property var mine: tasks.filter(function (t) { return t.assigner_account_id === root.me })
    readonly property var givenToMe: tasks.filter(function (t) { return t.assignee_account_id === root.me && t.assigner_account_id !== root.me })
    function isOverdue(t) { var h = t.final_deadline_at ? Date.parse(t.final_deadline_at) : NaN; return !isNaN(h) && h < Date.now() }
    function dayOf(iso) {
        if (!iso) return ""
        var d = new Date(iso), now = new Date()
        var days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        return (d.toDateString() === now.toDateString()) ? "today" : days[d.getDay()]
    }
    // to verify: you set it, it has begun, and nothing in its stack is still waiting
    readonly property var toVerify: mine.filter(function (t) { return t.status === "in_progress" })
    readonly property var deadlines: mine.filter(function (t) { return t.final_deadline_at }).sort(function (a, b) {
        return Date.parse(a.final_deadline_at) - Date.parse(b.final_deadline_at) })
    readonly property var people: {
        var by = {}, order = []
        for (var i = 0; i < mine.length; i++) {
            var t = mine[i]
            if (!by[t.assignee_account_id]) { by[t.assignee_account_id] = { name: t.assignee_name || "Someone", tasks: [] }; order.push(t.assignee_account_id) }
            by[t.assignee_account_id].tasks.push(t)
        }
        return order.map(function (k) { return by[k] })
    }
    readonly property var closedThisWeek: closed.filter(function (t) {
        return t.completed_at && (Date.now() - Date.parse(t.completed_at)) < 7 * 86400000 })

    // --- the header, shared by the three modes --------------------------------------------------------
    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 22
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 16

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Column {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4
                Row {
                    spacing: 6
                    Txt { text: "Tasks"; color: root.mode === "list" ? "#ffffff" : Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody
                          font.weight: root.mode === "list" ? Font.DemiBold : Font.Normal
                          MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: root.mode = "list" } }
                    Icon { visible: root.mode !== "list"; name: "chev"; color: Qt.rgba(1, 1, 1, 0.45); size: 12; anchors.verticalCenter: parent.verticalCenter }
                    Txt { objectName: "tasksCrumb"; visible: root.mode !== "list"; color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                          text: root.mode === "new" ? "New task" : (root.task ? root.taskTitle(root.task) : "") }
                }
                Row {
                    spacing: 12
                    Txt { text: root.mode === "new" ? "New task" : root.mode === "task" && root.task ? root.taskTitle(root.task) : "Tasks"
                          color: "#ffffff"; font.pixelSize: Theme.fTitle; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                    Txt { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody; color: Theme.warn
                          text: root.mode === "list" ? ((root.toVerify.length + root.givenToMe.length) > 0
                                                         ? (root.toVerify.length + root.givenToMe.length) + " waiting on you" : "")
                                : root.mode === "task" && root.task ? (root.task.assignee_name || "") + (root.task.final_deadline_at ? " · due " + root.dayOf(root.task.final_deadline_at) : "")
                                : "the model proposes; you decide" }
                }
            }
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 16
                TBtn { visible: root.mode === "list"; text: "New task"; iconName: "plus"; onClicked: { newTask.reset(); root.mode = "new" } }
                Txt { text: root.mode === "list" ? root.clock : "Esc to go back"; color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody
                      anchors.verticalCenter: parent.verticalCenter }
            }
        }

        // ===================================================================================================
        // TK04: the page
        GridLayout {
            visible: root.mode === "list"
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 2
            rowSpacing: 20
            columnSpacing: 20

            GridCell {
                objectName: "tasksNeeds"
                Layout.fillWidth: true
                Layout.preferredWidth: 2
                Layout.fillHeight: true
                topAlign: true
                title: "Needs you"
                narration: ({ brief: (root.toVerify.length + root.givenToMe.length) === 0 ? "nothing" : (root.toVerify.length + root.givenToMe.length) + " things",
                              tone: (root.toVerify.length + root.givenToMe.length) > 0 ? "accent" : "", state: "ok" })
                Row {
                    width: parent.width
                    spacing: 24
                    Column {
                        width: (parent.width - 24) / 2
                        spacing: 8
                        Txt { text: "Under way — yours to verify"; color: Theme.faint; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
                        PagedColumn {
                            width: parent.width; height: Math.max(80, root.height / 2 - 150); itemHeight: 58
                            model: root.toVerify
                            visible: root.toVerify.length > 0
                            delegate: InfoCard {
                                initials: modelData ? Theme.initials(modelData.assignee_name || "") : ""
                                title: modelData ? root.taskTitle(modelData) : ""
                                line: modelData ? (modelData.assignee_name || "") + " · started " + root.dayOf(modelData.started_at) : ""
                                stateWord: "verify"; stateTone: "ok"
                                onClicked: root.open(modelData.id)
                            }
                        }
                        Txt { visible: root.toVerify.length === 0; text: "Nothing to verify."; color: Theme.faint; font.pixelSize: Theme.fBody }
                    }
                    Column {
                        width: (parent.width - 24) / 2
                        spacing: 8
                        Txt { text: "Given to you"; color: Theme.faint; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
                        PagedColumn {
                            width: parent.width; height: Math.max(80, root.height / 2 - 150); itemHeight: 58
                            model: root.givenToMe
                            visible: root.givenToMe.length > 0
                            delegate: InfoCard {
                                iconName: "tasks"; iconTone: "accent"
                                title: modelData ? root.taskTitle(modelData) : ""
                                line: modelData ? "from " + (modelData.assigner_name || "above") + (modelData.final_deadline_at ? " · by " + root.dayOf(modelData.final_deadline_at) : "") : ""
                                stateWord: modelData && modelData.status === "active" ? "start" : "started"
                                stateTone: modelData && modelData.status === "active" ? "accent" : ""
                                onClicked: root.open(modelData.id)
                            }
                        }
                        Txt { visible: root.givenToMe.length === 0; text: "Nothing given to you."; color: Theme.faint; font.pixelSize: Theme.fBody }
                    }
                }
            }

            GridCell {
                objectName: "tasksDeadlines"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "Deadlines"
                narration: ({ brief: root.deadlines.filter(root.isOverdue).length > 0 ? root.deadlines.filter(root.isOverdue).length + " overdue" : "on time",
                              tone: root.deadlines.filter(root.isOverdue).length > 0 ? "danger" : "", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 0
                    Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: Theme.fSection; font.weight: Font.DemiBold
                          bottomPadding: 10
                          text: root.deadlines.length === 0 ? "No task you set has a deadline."
                                : root.isOverdue(root.deadlines[0]) ? (root.deadlines[0].assignee_name || "Someone") + " is past the final deadline."
                                : "The next is due " + root.dayOf(root.deadlines[0].final_deadline_at) + "." }
                    Repeater {
                        model: root.deadlines.slice(0, 5)
                        delegate: Item {
                            required property var modelData
                            width: parent.width; height: 34
                            Txt { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 90; elide: Text.ElideRight
                                  text: root.taskTitle(modelData); color: Theme.dim; font.pixelSize: Theme.fBody }
                            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody; font.weight: Font.Medium
                                  text: root.isOverdue(modelData) ? "overdue" : root.dayOf(modelData.final_deadline_at)
                                  color: root.isOverdue(modelData) ? Theme.danger : Theme.ink }
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                        }
                    }
                }
            }

            GridCell {
                objectName: "tasksByPerson"
                Layout.fillWidth: true
                Layout.preferredWidth: 2
                Layout.fillHeight: true
                topAlign: true
                title: "By person"
                narration: ({ brief: "who is carrying what", state: root.people.length === 0 ? "empty" : "ok",
                              note: "No tasks set", sentence: "Describe one with New task." })
                PagedColumn {
                    width: parent.width
                    height: Math.max(100, root.height / 2 - 110)
                    itemHeight: 58
                    model: root.people
                    delegate: InfoCard {
                        initials: modelData ? Theme.initials(modelData.name) : ""
                        title: modelData ? modelData.name : ""
                        line: modelData ? modelData.tasks.map(function (t) { return root.taskTitle(t) }).join(" · ") : ""
                        stateWord: modelData ? (modelData.tasks.filter(root.isOverdue).length > 0 ? "overdue"
                                                : modelData.tasks.length + (modelData.tasks.length === 1 ? " task" : " tasks")) : ""
                        stateTone: modelData && modelData.tasks.filter(root.isOverdue).length > 0 ? "danger" : ""
                        onClicked: if (modelData) root.open(modelData.tasks[0].id)
                    }
                }
            }

            GridCell {
                objectName: "tasksClosed"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "Closed"
                narration: ({ brief: "hands off to Record", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 8
                    Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: Theme.fSection; font.weight: Font.DemiBold
                          text: root.closedThisWeek.length === 0 ? "Nothing closed this week."
                                : root.closedThisWeek.length + (root.closedThisWeek.length === 1 ? " closed this week." : " closed this week.") }
                    Repeater {
                        model: root.closedThisWeek.slice(0, 3)
                        delegate: InfoCard { required property var modelData; width: parent.width; iconName: "check"; iconTone: "ok"
                                             title: root.taskTitle(modelData); line: (modelData.assignee_name || "") + " · " + root.dayOf(modelData.completed_at)
                                             stateWord: "verified"; stateTone: "ok" }
                    }
                    Row { spacing: 4
                          Txt { text: "All of them are in Record"; color: Theme.accent; font.pixelSize: Theme.fBody
                                MouseArea { anchors.fill: parent; anchors.margins: -4; cursorShape: Qt.PointingHandCursor; onClicked: shell.show("reports") } }
                          Icon { name: "chev"; size: 12; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter } }
                }
            }
        }

        // ===================================================================================================
        // TK06: one task -- the checks and the files, and the verdict the full height
        RowLayout {
            visible: root.mode === "task" && root.task !== null
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 2
                Layout.fillHeight: true
                spacing: 20

                GridCell {
                    objectName: "taskChecks"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    topAlign: true
                    title: "The checks"
                    narration: ({ brief: root.task ? root.checksBrief(root.task) : "", tone: root.task && root.itemsFailed(root.task) > 0 ? "warn" : "", state: "ok" })
                    Column {
                        width: parent.width
                        spacing: 0
                        Txt { visible: root.task && root.task.verification_mode === "none"; width: parent.width; wrapMode: Text.WordWrap
                              text: "No verification was chosen for this task. You close it by looking at the work."; color: Theme.dim; font.pixelSize: Theme.fBody }
                        Repeater {
                            model: root.task ? (root.task.items || []) : []
                            delegate: Item {
                                required property var modelData
                                width: parent.width; height: 52
                                Row {
                                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; spacing: 12
                                    Rectangle { width: 20; height: 20; radius: 6; anchors.verticalCenter: parent.verticalCenter
                                                color: modelData.status === "passed" ? Theme.ok : modelData.status === "failed" ? Theme.danger : Theme.line2
                                                Icon { anchors.centerIn: parent; visible: modelData.status !== "pending"; size: 12; weight: 2.4; color: "#10131a"
                                                       name: modelData.status === "passed" ? "check" : "x" } }
                                    Column { anchors.verticalCenter: parent.verticalCenter; spacing: 1
                                        Txt { text: modelData.proposed_filename || modelData.program_name || ("item " + modelData.sequence)
                                              color: Theme.ink; font.pixelSize: Theme.fRow - 1; font.weight: Font.DemiBold }
                                        Txt { text: root.itemLine(modelData); color: Theme.faint; font.pixelSize: Theme.fMeta } }
                                }
                                Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: root.intentWord(modelData.intent)
                                      color: Theme.tone(modelData.intent === "create" ? "ok" : "accent"); font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
                                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                            }
                        }
                        Txt { topPadding: 8; visible: root.task && root.task.verification_mode !== "none"; color: Theme.faint; font.pixelSize: Theme.fMeta
                              text: "Signs of work, never proof of it. The checks inform; the verdict is yours." }
                        Item {
                            visible: root.task && root.task.verification_mode !== "none"
                            width: parent.width
                            height: 34
                            GBtn { objectName: "recheckStack"; anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                                   text: "Check them again"; iconName: "check"; small: true; onClicked: root.recheck(false) }
                            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                  visible: root.checkedAt !== ""
                                  text: "checked " + root.checkedAt; color: Theme.faint; font.pixelSize: Theme.fMeta }
                        }
                    }
                }
                GridCell {
                    objectName: "taskFiles"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 190
                    topAlign: true
                    title: "The files"
                    narration: ({ brief: "tracked by name, not by folder", state: "ok" })
                    Flow {
                        width: parent.width
                        spacing: 14
                        Repeater {
                            model: root.task ? (root.task.items || []).filter(function (i) { return i.target_type === "file" }) : []
                            delegate: Rectangle {
                                required property var modelData
                                width: (parent.width - 14) / 2; height: 96; radius: 12; color: Theme.pane
                                Column { anchors.fill: parent; anchors.margins: 14; spacing: 6
                                    Row { spacing: 9
                                          Icon { name: "file"; size: 17; color: modelData.file_path ? Theme.accent : Theme.faint }
                                          Txt { text: modelData.proposed_filename || ""; color: Theme.ink; monospace: true; font.pixelSize: Theme.fRow - 1; font.weight: Font.DemiBold } }
                                    Txt { width: parent.width; elide: Text.ElideMiddle; color: Theme.faint; font.pixelSize: Theme.fMeta
                                          text: modelData.file_path ? modelData.file_path : "not created yet — found by name wherever it is saved" }
                                    Txt { visible: !!modelData.file_last_seen_at; color: Theme.dim; font.pixelSize: Theme.fMeta
                                          text: "last seen " + String(modelData.file_last_seen_at || "").substring(11, 16) }
                                }
                            }
                        }
                    }
                }
            }

            GridCell {
                objectName: "taskVerdict"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: root.task && root.task.assigner_account_id === root.me ? "Review, then decide" : "Your part"
                narration: ({ brief: root.task && root.task.assigner_account_id === root.me ? "yours alone" : "", tone: "accent", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 12
                    Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: Theme.fSection; font.weight: Font.DemiBold
                          text: root.task ? root.verdictSentence(root.task) : "" }
                    Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.dim; font.pixelSize: Theme.fBody
                          text: root.task ? String(root.task.description_raw || "") : "" }
                    KeyRow { label: "For"; value: root.task ? (root.task.assignee_name || "") : "" }
                    KeyRow { label: "Final deadline"; value: root.task && root.task.final_deadline_at ? root.dayOf(root.task.final_deadline_at) : "none"
                             tone: root.task && root.isOverdue(root.task) ? "danger" : "" }
                    KeyRow { label: "State"; value: root.task ? (root.task.status === "active" ? "not started" : root.task.status === "in_progress" ? "under way" : "closed") : "" }
                    Txt { visible: root.task && root.task.assigner_account_id === root.me && root.task.status !== "completed"; width: parent.width; wrapMode: Text.WordWrap
                          text: "Only you can close this task, and only as a whole."; color: Theme.dim; font.pixelSize: Theme.fBody }
                    Row {
                        spacing: 8
                        visible: root.task && root.task.assigner_account_id === root.me && root.task.status !== "completed"
                        TBtn { text: "Complete"; tone: "ok"; iconName: "check"
                               onClicked: falcon.call("task.verify", { task_id: root.task.id, outcome: "complete" }, root.after) }
                        TBtn { text: "Send back"; tone: "warn"
                               onClicked: falcon.call("task.verify", { task_id: root.task.id, outcome: "incomplete" }, root.after) }
                    }
                    TBtn { visible: root.task && root.task.assignee_account_id === root.me && root.task.status === "active"
                           text: "Start"; iconName: "play"; onClicked: falcon.call("task.start", { task_id: root.task.id }, root.after) }
                }
            }
        }

        // ===================================================================================================
        // TK05: describing a task
        NewTask {
            id: newTask
            visible: root.mode === "new"
            Layout.fillWidth: true
            Layout.fillHeight: true
            tree: root.tree
            onCreated: function (id) { root.refresh(); root.open(id) }
        }
    }

    // --- words -------------------------------------------------------------------------------------------
    function taskTitle(t) {
        var d = String(t.description_raw || "Task")
        var cut = d.split(/[.;]/)[0]
        return cut.length > 44 ? cut.substring(0, 42) + "…" : cut
    }
    function intentWord(i) {
        return ({ create: "Create", update: "Update", exists: "Exists", used: "Used", used_with_file: "Used with",
                  installed_available: "Installed", closed_not_running: "Closed", running: "Running" })[i] || i
    }
    function itemLine(it) {
        if (it.status === "passed") return it.file_path ? "found at " + it.file_path : "passed"
        if (it.status === "failed") return "not met"
        return it.target_type === "program" ? "watching the program" : it.intent === "create" ? "not created yet" : "waiting for a change"
    }
    function itemsFailed(t) { return (t.items || []).filter(function (i) { return i.status === "failed" }).length }
    function checksBrief(t) {
        var items = t.items || []
        if (items.length === 0) return "no checks"
        var passed = items.filter(function (i) { return i.status === "passed" }).length
        return passed + " of " + items.length + " passed"
    }
    function verdictSentence(t) {
        if (t.status === "completed") return "This task is closed."
        var items = t.items || []
        if (t.verification_mode === "none") return "Look at the work, then decide."
        var passed = items.filter(function (i) { return i.status === "passed" }).length
        var failed = itemsFailed(t)
        if (passed === items.length) return "Every check passed. Look at the work, then decide."
        return passed + " of " + items.length + " checks passed" + (failed > 0 ? "; " + failed + " not met." : "; the rest are waiting.")
    }
    function after(ok, r) {
        shell.notify(ok ? "Done" : r.message, !ok)
        root.refresh()
        if (ok && root.task) root.open(root.task.id)
    }
}
