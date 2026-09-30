import QtQuick
import "."

// WHAT WAS ASKED OF WHOM, and whether it is done. The stack is evidence, not a verdict: only the
// assigner closes a task, and they close the whole task, never item by item (task combo doc).
Item {
    id: root

    property var tasks: []
    property bool loaded: false
    property var chosen: null            // the table row
    property var detailTask: null        // what task.get answered, with the live stack
    property string pane: "checks"

    readonly property var rows: tasks.map(function (t) {
        var s = Task.state(t)
        return { task_id: t.id, what: t.description_raw, who: t.assignee_name || "",
                 by: t.assigner_name || "", status: t.status,
                 stateWord: s.word, stateTone: s.tone, line: s.line,
                 due: Task.when(t.final_deadline_at || t.soft_deadline_at),
                 checks: t.verification_mode === "none" ? "nothing to check" : "a stack" }
    })
    readonly property int late: rows.filter(function (r) { return r.stateTone === "danger" }).length

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("task.list", { include_completed: true }, function (ok, r) {
            root.loaded = true
            if (ok) root.tasks = r.tasks || []
        })
    }
    function openTask(row) {
        chosen = row
        detailTask = null
        detail.open()
        pane = "checks"
        falcon.call("task.get", { task_id: row.task_id }, function (ok, r) {
            if (ok) root.detailTask = r.task
        })
    }
    function verify(outcome) {
        if (!chosen) return
        falcon.call("task.verify", { task_id: chosen.task_id, outcome: outcome }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not verified"); return }
            Msg.ok(outcome === "complete" ? "Task closed" : "Left open")
            detail.close()
            root.refresh()
        })
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.tasks = []; root.loaded = false }
        function onPushReceived(type) { if (String(type).indexOf("task.") === 0) root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s5
        spacing: Theme.s3

        PageHeader {
            width: parent.width
            title: "Tasks"
            subtitle: root.rows.length + " tasks"
                      + (root.late > 0 ? " · " + root.late + " past the deadline" : "")
            Btn {
                objectName: "newTask"
                kind: "primary"
                iconName: "plus"
                text: "New task"
                onClicked: maker.open()
            }
        }

        Rectangle {
            width: parent.width
            height: parent.height - y
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Table {
                objectName: "tasksTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                loading: !root.loaded
                pageSize: 12
                rows: root.rows
                emptyText: "No tasks yet"
                emptyHint: "A task is something asked of one person, with the checks that show it happened."
                onRowActivated: function (row) { root.openTask(row) }
                columns: [
                    { title: "Task", key: "what", strong: true },
                    { title: "Assigned to", key: "who", width: 150 },
                    { title: "State", key: "stateWord", width: 130, tag: true,
                      filters: ["not started", "started", "due", "late", "done"],
                      tone: function (r) { return r.stateTone } },
                    { title: "Due", key: "due", width: 150, mono: true,
                      tone: function (r) { return r.stateTone === "" ? "mid" : r.stateTone } },
                    { title: "Checks", key: "checks", width: 140,
                      tone: function () { return "mid" } }
                ]
            }
        }
    }

    NewTask {
        id: maker
        objectName: "newTaskModal"
        page: root
        onCreated: root.refresh()
    }

    Confirm {
        id: closeIt
        objectName: "verifyConfirm"
        page: root
        title: "Close this task"
        cost: "Verifying closes the task for good: it is the only way a task completes, and nothing "
              + "reopens it. The checks are evidence -- look at the work yourself before you do this."
        verb: "Verify"
        onAccepted: root.verify("complete")
    }

    Drawer {
        id: detail
        objectName: "taskDrawer"
        page: root
        title: root.chosen ? root.chosen.what : ""
        subtitle: root.chosen ? (root.chosen.who + " · " + root.chosen.line) : ""

        Descriptions {
            width: parent.width
            items: root.chosen ? [
                { label: "Assigned to", value: root.chosen.who },
                { label: "Assigned by", value: root.chosen.by },
                { label: "State", value: root.chosen.stateWord, tag: true, tone: root.chosen.stateTone },
                { label: "Due", value: root.chosen.due || "no deadline", mono: !!root.chosen.due }
            ] : []
        }

        // two kinds of thing about one task: what would show it is done, and what has happened
        Tabs {
            width: parent.width
            visible: root.detailTask !== null
            current: root.pane
            tabs: [{ key: "checks", label: "Checks",
                     count: root.detailTask && root.detailTask.items
                            ? root.detailTask.items.filter(function (i) { return i.status !== "passed" }).length
                            : 0 },
                   { key: "history", label: "History" }]
            onPicked: function (k) { root.pane = k }
        }
        Column {
            width: parent.width
            spacing: 0
            visible: root.detailTask !== null && root.pane === "checks"

            Repeater {
                model: root.detailTask && root.detailTask.items ? root.detailTask.items : []
                delegate: Item {
                    required property var modelData
                    width: parent.width
                    height: 34

                    Txt {
                        anchors.left: parent.left
                        anchors.right: mark.left
                        anchors.rightMargin: Theme.s2
                        anchors.verticalCenter: parent.verticalCenter
                        text: Task.say(modelData)
                        font.pixelSize: Theme.fSmall
                    }
                    Tag {
                        id: mark
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: Task.itemWord(modelData.status)
                        tone: Task.itemTone(modelData.status)
                    }
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: Theme.split
                    }
                }
            }
        }
        Trail {
            width: parent.width
            visible: root.detailTask !== null && root.pane === "history"
            items: root.detailTask && root.detailTask.expectations
                   ? root.detailTask.expectations.map(function (e) {
                       return { at: Task.when(e.observed_at).substring(0, 5),
                                text: e.summary || e.kind || "something happened" }
                     })
                   : []
        }
        Empty {
            width: parent.width
            visible: root.detailTask !== null && root.pane === "history"
                     && !(root.detailTask.expectations || []).length
            text: "Nothing yet"
            hint: "What the Engine notices about this task shows up here."
        }

        Alert {
            width: parent.width
            visible: root.pane === "checks" && root.detailTask !== null
                     && root.detailTask.verification_mode === "none"
            kind: "note"
            text: "Nothing is checked on this one. The assigner chose that when they made it."
        }

        // the Drawer's footer is a Row: order places these, not anchors
        footer: [
            Btn {
                text: "Not done"
                visible: root.chosen && root.chosen.status !== "completed"
                onClicked: root.verify("incomplete")
            },
            Btn {
                objectName: "verifyTask"
                kind: "primary"
                text: "Verify"
                visible: root.chosen && root.chosen.status !== "completed"
                onClicked: closeIt.open()
            }
        ]
    }
}
