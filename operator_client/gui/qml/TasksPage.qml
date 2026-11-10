import QtQuick
import "."

// TASKS, as the version 1 concept draws it (docs/design/concepts-admin.html, AdminTasksPage): is the work I gave getting done, and
// what do I close? The situation in a sentence; the work you gave as one card per task grouped by what you do about it (waiting
// for your verdict, on track, completed this week, late or gone quiet last); on the right the picked task with its verdict (the
// buttons live there, never on the cards: the user, 1 Nov 2026), and your to-dos under it; the picked task's targets below
// (loading in place, then a pulse); giving a task has its own page.
Page {
    id: page
    objectName: "tasksView"

    property var tasks: []
    property var detail: ({})          // task id -> task.get view
    property var todos: []
    property var sel: { var a = Nav.takeArrive("tasks"); return a !== null ? a : null }
    property var openId: null
    property bool asking: false
    property string why: ""
    property string tdt: ""
    property bool loading: false

    function load() {
        falcon.call("task.list", { include_completed: true }, function (ok, r) {
            page.tasks = ok ? (r.tasks || []) : []
            page.tasks.forEach(function (t) {
                falcon.call("task.get", { task_id: t.id }, function (ok2, r2) {
                    if (!ok2) return
                    var d = Object.assign({}, page.detail); d[t.id] = r2.task; page.detail = d
                })
            })
        })
        loadTodos()
    }
    function loadTodos() { falcon.call("todo.list", {}, function (ok, r) { page.todos = ok ? (r.todos || []) : [] }) }
    Component.onCompleted: load()
    Connections {
        target: falcon
        function onPushReceived(type, payload) { if (/^task/.test(type)) reload.restart(); if (type === "todo.changed") page.loadTodos() }
    }
    Timer { id: reload; interval: 300; onTriggered: page.load() }

    readonly property var groupsDef: [["verify", "Waiting for your verdict", "handed in; any Admin can close it"], ["track", "On track", "signs of progress"],
                              ["done", "Completed this week", "closed; kept here for the week"], ["late", "Late, or gone quiet", "past the deadline, or nothing seen for two days"]]
    readonly property var stateWord: ({ verify: "Handed in", track: "On track", done: "Completed", late: "Late, or gone quiet" })
    function items(t) { var d = detail[t.id]; return d && d.items ? d.items : [] }
    function found(t) { return items(t).filter(function (i) { return i.status === "passed" }).length }
    function lastSign(t) {
        var d = detail[t.id], ex = d && d.expectations ? d.expectations : [], m = null
        ex.forEach(function (e) { var x = Time.ms(e.observed_at); if (m === null || x > m) m = x })
        return m
    }
    function quiet(t) { var ls = lastSign(t); return Time.now - Time.ms(t.created_at) > 48 * 3600000 && (ls === null || Time.now - ls > 48 * 3600000) }
    function cat(t) {
        if (t.status === "completed") return "done"
        var its = items(t)
        if (its.length && its.every(function (i) { return i.status === "passed" })) return "verify"
        if ((t.final_deadline_at && Time.past(t.final_deadline_at)) || quiet(t)) return "late"
        return "track"
    }
    // the clock ticks every second and this reads it: `all` only changes when what it says changes, or everything hanging off it would be rebuilt each second
    readonly property var listed: tasks.filter(function (t) { return t.status !== "completed" || !t.completed_at || Time.now - Time.ms(t.completed_at) < 7 * 86400000 })
        .map(function (t) { return Object.assign({ k: page.cat(t), factRows: t.soft_deadline_at ? 5 : 4 }, t) })
        .sort(function (x, y) { return (Time.ms(x.final_deadline_at) || 9e15) - (Time.ms(y.final_deadline_at) || 9e15) })
    property var all: []
    property string allSaid: "[]"
    onListedChanged: { var s = JSON.stringify(listed); if (s !== allSaid) { allSaid = s; all = listed } }
    function inGroup(k) { return all.filter(function (x) { return x.k === k }) }
    // the most pressing is picked at first; nothing is open until you expand it
    readonly property var cur: {
        for (var i = 0; i < all.length; i++) if (all[i].id === sel) return all[i]
        var f = inGroup("verify")[0] || inGroup("late")[0] || inGroup("track")[0]
        return f || null
    }
    property var pickedId: null
    onCurChanged: { var id = cur ? cur.id : null; if (id === pickedId) return; loading = true; ldT.restart(); asking = false; why = ""; pickedId = id }
    Timer { id: ldT; interval: Theme.loadMs; onTriggered: page.loading = false }
    readonly property var curDetail: cur ? detail[cur.id] || null : null
    readonly property var curHost: cur ? Fleet.byAccount(cur.assignee_account_id) : null
    function hostOf(t) { var m = Fleet.byAccount(t.assignee_account_id); return m ? m.host : "" }
    function by(t) { return t.assigner_account_id === falcon.accountId ? "you" : t.assigner_name }

    situation: {
        if (!tasks.length) return "You have not given any tasks yet."
        var v = inGroup("verify").length, l = inGroup("late").length
        var next = all.filter(function (t) { return t.k !== "done" && t.final_deadline_at && !Time.past(t.final_deadline_at) })[0]
        return (v ? Theme.fmt(v) + (v === 1 ? " waits" : " wait") + " for your verdict" : "Nothing waits for your verdict") + "; " + (l ? Theme.fmt(l) + " late or gone quiet" : "nothing late") + "."
               + (next ? " The next deadline: " + next.description_raw + ", " + Time.atDay(next.final_deadline_at) + "." : "")
    }
    situationAt: Time.now

    function verdict(outcome) {
        falcon.call("task.verify", { task_id: cur.id, outcome: outcome, reason: why.trim() }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not recorded"); return }
            Msg.ok(outcome === "complete" ? "Marked complete" : "Sent back as incomplete · " + cur.assignee_name + " sees it")
            page.asking = false; page.why = ""; page.load()
        })
    }
    function addTodo() {
        var d = new Date(Time.now); d.setDate(d.getDate() + 1); d.setHours(17, 0, 0, 0)
        falcon.call("todo.add", { text: tdt.trim(), due_at: d.toISOString() }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not added"); return }
            Msg.ok("Added, due " + Time.atDay(d)); page.tdt = ""; page.loadTodos()
        })
    }
    function todoDone(t, done) {
        falcon.call("todo.done", { todo_id: t.id, done: done }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not changed"); return }
            if (done) Msg.ok("Done · " + t.text); page.loadTodos()
        })
    }

    // when a task was handed in: the moment its last target was found
    function handedAt(t) {
        var its = items(t); if (!its.length || !its.every(function (i) { return i.status === "passed" })) return null
        var m = null; its.forEach(function (i) { var x = Time.ms(i.passed_at || i.updated_at); if (x !== null && (m === null || x > m)) m = x }); return m !== null ? m : lastSign(t)
    }
    // what the card says on the right: early or late against the deadline, or how far through its time
    function barSay(t) {
        var given = Time.ms(t.created_at), fin = Time.ms(t.final_deadline_at)
        if (t.k === "done" || t.k === "verify") { var h = handedAt(t); if (h === null || fin === null) return t.k === "done" ? "closed" : "handed in"
            return h <= fin ? Time.waitLen((fin - h) / 3600000) + " early" : Time.waitLen((h - fin) / 3600000) + " late" }
        if (fin === null) return "no deadline"
        return Time.waitSay((Time.now - given) / 3600000, (fin - given) / 3600000)
    }

    Row {
        width: parent.width
        spacing: 14
        // --- the work you gave ----------------------------------------------------------------------------
        Box {
            id: workP
            objectName: "tasksWork"
            width: (parent.width - 14) * 8 / 12
            title: "The work you gave"
            sub: "one card per task, grouped by what you do about it; click a task for what to do on the right and its targets below, expand it for its dates"
            Repeater {
                model: page.groupsDef
                delegate: Group {
                    id: grp
                    required property var modelData
                    required property int index
                    readonly property var xs: page.inGroup(modelData[0])
                    spaced: page.groupsDef.slice(0, index).some(function (g) { return page.inGroup(g[0]).length > 0 })
                    visible: xs.length > 0
                    width: workP.innerW
                    late: modelData[0] === "late"
                    title: modelData[1] + " · " + xs.length
                    sub: modelData[2]
                    Repeater {
                        model: grp.xs
                        delegate: Card {
                            id: tc
                            required property var modelData
                            readonly property int n: page.items(modelData).length
                            objectName: "task_" + modelData.id
                            width: grp.cardW
                            actW: 176
                            midW: 130
                            icon: "checksquare"
                            hot: modelData.k === "late"
                            tint: grp.late
                            opacity: modelData.k === "done" ? 0.7 : 1
                            title: modelData.description_raw
                            line: modelData.assignee_name + (page.hostOf(modelData) ? " on " + page.hostOf(modelData) : "") + " · " + page.found(modelData) + " of " + n + " target" + (n === 1 ? "" : "s") + " found"
                                  + (modelData.assigner_account_id !== falcon.accountId ? " · from " + modelData.assigner_name : "")
                            line2: page.quiet(modelData) && modelData.k !== "done" ? "Nothing seen for " + (page.lastSign(modelData) === null ? "as long as it has existed" : Time.waitLen((Time.now - page.lastSign(modelData)) / 3600000)) : ""
                            picked: page.cur !== null && page.cur.id === modelData.id
                            expandable: true
                            expanded: page.openId === modelData.id
                            onOpen: page.sel = modelData.id
                            onToggle: { page.sel = modelData.id; page.openId = expanded ? null : modelData.id }
                            mid: Row {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 10
                                Txt {
                                    width: 96
                                    horizontalAlignment: Text.AlignRight
                                    anchors.verticalCenter: parent.verticalCenter
                                    readonly property bool over: tc.modelData.k !== "done" && tc.modelData.k !== "verify" && Time.past(tc.modelData.final_deadline_at)
                                    text: page.barSay(tc.modelData)
                                    font.pixelSize: 12
                                    font.weight: over ? Font.DemiBold : Font.Normal
                                    color: over ? Theme.crit : Theme.text2
                                }
                            }
                            // opened: its dates (tk-facts: 120px labels, at most 420 wide)
                            Column {
                                y: 2
                                width: Math.min(parent.width, 420)
                                Repeater {
                                    model: [["Given", Time.atDay(tc.modelData.created_at) + " by " + page.by(tc.modelData)], ["Started", tc.modelData.started_at ? Time.atDay(tc.modelData.started_at) : "not yet"]]
                                           .concat(tc.modelData.soft_deadline_at ? [["Soft deadline", Time.atDay(tc.modelData.soft_deadline_at)]] : [])
                                           .concat([["Final deadline", tc.modelData.final_deadline_at ? Time.atDay(tc.modelData.final_deadline_at) : "none"],
                                                    ["Handed in", tc.modelData.k === "verify" ? "yes" : tc.modelData.k === "done" ? "closed" : "not yet"]])
                                    delegate: Item {
                                        required property var modelData
                                        required property int index
                                        width: parent.width
                                        height: fv.height + 10
                                        Txt { y: 5; width: 120; text: modelData[0]; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                                        Txt { id: fv; x: 132; y: 5; width: parent.width - 132; text: modelData[1]; font.pixelSize: 13 }
                                        Rectangle { visible: index < tc.modelData.factRows - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            Quiet { visible: page.tasks.length === 0; text: "No tasks yet. Give one below." }
        }

        // --- the picked task, and your to-dos (iq-col: the to-dos fill what is left of the column) -----------------
        Column {
            id: rightCol
            width: (parent.width - 14) * 4 / 12
            spacing: 14
            Box {
                id: ctl
                objectName: "taskControls"
                width: parent.width
                title: page.cur ? page.cur.description_raw : "No task picked"
                sub: page.cur ? page.cur.assignee_name + (page.hostOf(page.cur) ? " on " + page.hostOf(page.cur) : "") : ""
                Quiet { visible: page.cur === null; text: "Pick a task on the left." }
                Facts {
                    visible: page.cur !== null
                    rows: !page.cur ? [] : [
                        ["State", page.stateWord[page.cur.k], page.cur.k === "late" ? (Time.past(page.cur.final_deadline_at) ? Time.waitLen((Time.now - Time.ms(page.cur.final_deadline_at)) / 3600000) + " past its deadline" : "nothing seen for two days")
                                                          : page.cur.k === "verify" ? "every target was found" : page.cur.k === "done" ? "closed" : "signs of progress"],
                        ["Progress", page.found(page.cur) + " of " + page.items(page.cur).length + " targets found", page.lastSign(page.cur) ? "last sign " + Time.atDay(page.lastSign(page.cur)) : "no sign yet"],
                        ["Deadline", page.cur.final_deadline_at ? Time.atDay(page.cur.final_deadline_at) : "none", page.cur.soft_deadline_at ? "soft deadline " + Time.atDay(page.cur.soft_deadline_at) : "no soft deadline"],
                        ["Given", page.cur.assigner_account_id === falcon.accountId ? "By you" : "By " + page.cur.assigner_name, Time.atDay(page.cur.created_at)]]
                }
                // the verdict (tk-do): what it waits on, then its buttons at the right; only the person who gave it closes it
                Rectangle {
                    visible: page.cur !== null
                    width: parent.width
                    height: doCol.height + 20
                    radius: Theme.radius
                    color: Theme.surface2
                    Column {
                        id: doCol
                        x: 12; y: 10
                        width: parent.width - 24
                        spacing: 8
                        Txt {
                            visible: !page.asking
                            width: parent.width
                            color: Theme.text3; wrapMode: Text.WordWrap; elide: Text.ElideNone; font.pixelSize: 13
                            text: !page.cur ? "" : page.cur.k === "verify" ? "Every target was found. Any Admin can close it."
                                  : page.cur.k === "late" ? (Time.past(page.cur.final_deadline_at) ? "Past its deadline." : "Nothing seen for two days.")
                                  : page.cur.k === "done" ? "Closed. Nothing more to do." : "Not handed in yet; your verdict comes when it is."
                        }
                        Field { visible: page.asking; width: parent.width; placeholderText: page.cur ? "What is missing? " + page.cur.assignee_name + " sees this." : ""; text: page.why; onTextEdited: page.why = text }
                        Row {
                            anchors.right: parent.right
                            spacing: 8
                            visible: children.length > 0
                            Btn { visible: !page.asking && page.cur !== null && page.cur.k === "verify"; small: true; text: "Incomplete"; onClicked: page.asking = true }
                            Btn { visible: !page.asking && page.cur !== null && page.cur.k === "verify"; small: true; kind: "primary"; text: "Complete"; onClicked: page.verdict("complete") }
                            Btn { visible: !page.asking && page.cur !== null && page.cur.k === "late"; small: true; kind: "primary"; text: page.cur ? "Remind " + page.cur.assignee_name : ""
                                  onClicked: falcon.call("task.remind", { task_id: page.cur.id }, function (ok, r) { if (ok) Msg.ok("Reminded"); else Msg.failed(r && r.message ? r.message : "Not done") }) }
                            Btn { visible: page.asking; small: true; text: "Cancel"; onClicked: { page.asking = false; page.why = "" } }
                            Btn { visible: page.asking; small: true; kind: "primary"; text: "Send back"; enabled: page.why.trim() !== ""; onClicked: page.verdict("incomplete") }
                        }
                    }
                }
                Pulse { parent: ctl; key: page.loading ? null : page.pickedId }
            }
            Box {
                id: tdBox
                objectName: "yourTodos"
                width: parent.width
                readonly property var open: page.todos.filter(function (t) { return !t.done })
                readonly property real natural: implicitHeight
                height: Math.max(implicitHeight, workP.implicitHeight - ctl.implicitHeight - 14)
                title: "Your to-dos · " + open.length
                sub: "reminders for yourself, soonest first; only you see them"
                Repeater {
                    model: page.todos.slice().sort(function (a, b) { return (a.done - b.done) || ((Time.ms(a.due_at) || 9e15) - (Time.ms(b.due_at) || 9e15)) })
                    delegate: SuRow {
                        required property var modelData
                        icon: modelData.done ? "checksquare" : "square"
                        title: modelData.text
                        done: !!modelData.done
                        line: modelData.done ? "done" + (modelData.done_at ? " " + Time.at(modelData.done_at) : "") : modelData.due_at ? "due " + Time.at(modelData.due_at) + (modelData.overdue ? ", past its date" : "") : "no date"
                        lineHot: !modelData.done && !!modelData.overdue
                        act: modelData.done ? "Undo" : "Done"
                        actKind: modelData.done ? "text" : "default"
                        onActed: page.todoDone(modelData, !modelData.done)
                    }
                }
                Quiet { visible: page.todos.length === 0; icon: "check"; text: "Nothing to remember." }
                Row {
                    width: parent.width
                    spacing: 8
                    topPadding: 4
                    Field { objectName: "todoText"; width: parent.width - addB.width - 8; placeholderText: "Remind yourself of something"; text: page.tdt; onTextEdited: page.tdt = text; onAccepted: if (page.tdt.trim()) page.addTodo() }
                    Btn { id: addB; text: "Add"; enabled: page.tdt.trim() !== ""; onClicked: page.addTodo() }
                }
                Txt { text: { var d = new Date(Time.now); d.setDate(d.getDate() + 1); d.setHours(17, 0, 0, 0); return "Due " + Time.at(d) + "; to pick another time, add it on the Calendar." } color: Theme.text3; font.pixelSize: 12; width: parent.width }
            }
        }
    }

    // --- the picked task's targets (a hairline panel, as the concept keeps it) ------------------------------------
    Panel {
        id: targets
        objectName: "taskTargets"
        width: parent.width
        title: page.cur ? "Targets · " + page.cur.description_raw : "Targets"
        sub: "what done looks like, and the signs of progress for each"
        padTop: 6
        extra: HowChecking { who: page.cur ? page.cur.assignee_name || "" : "" }
        TaskChart {
            visible: page.cur !== null
            width: parent.width
            task: page.curDetail
            handedIn: page.cur !== null && page.cur.k === "verify"
            host: page.curHost ? page.curHost.host : ""
        }
        Quiet { visible: page.cur === null; icon: "arrowu"; text: "Pick a task above to see its targets here." }
        Loading { parent: targets; on: page.loading && page.cur !== null; under: targets.headerHeight; text: "Loading its targets" }
        Pulse { parent: targets; key: page.loading ? null : page.pickedId }
    }

    // --- give a task: a few careful steps, so it has its own page ------------------------------------------------
    Box {
        objectName: "giveTask"
        width: parent.width
        accentFoot: true
        title: "Give a task"
        sub: "it takes a few careful steps, so it has its own page"
        Item {
            width: parent.width
            height: Math.max(steps.height, giveB.height)
            Row {
                id: steps
                width: parent.width - giveB.width - 18
                spacing: 14
                Repeater {
                    model: [["Say what needs doing", "in plain words, as you would tell the person"], ["Check the proposal", "the system proposes who, what done looks like and the deadlines; nothing is guessed silently"], ["Confirm", "nothing is given until you do; the person is told at once"]]
                    delegate: Item {
                        required property var modelData
                        required property int index
                        width: (steps.width - 28) / 3
                        height: sc.height
                        Rectangle { width: 22; height: 22; radius: 11; color: Theme.accentSoft
                                    Txt { anchors.centerIn: parent; text: index + 1; color: Theme.accent; font.pixelSize: 12; font.weight: Font.DemiBold; elide: Text.ElideNone } }
                        Column {
                            id: sc
                            x: 30
                            width: parent.width - 30
                            spacing: 2
                            Txt { width: parent.width; text: modelData[0]; font.weight: Font.DemiBold }
                            Txt { width: parent.width; text: modelData[1]; color: Theme.text3; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                        }
                    }
                }
            }
            Btn { id: giveB; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; kind: "primary"; text: "Give a task"; onClicked: Nav.go("tasks", "new") }
        }
    }
}
