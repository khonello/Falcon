import QtQuick
import "."

// TASKS (an Admin's console). What a task needs from you decides where it sits: to verify first, then
// overdue, then quiet, then on track. A click selects; the task shows beside the list with your
// verdict and its history, and its targets under both. "From the Super User" lists the department
// tasks given to you: say how far you have got; only the Super User calls one complete.
Page {
    id: page
    objectName: "tasksView"

    property var tasks: []
    property var detail: ({})          // task id -> task.get view
    property var deptTasks: []
    property string f: ""
    property string tab: Nav.sub && String(Nav.sub).indexOf("dt:") === 0 ? "su" : "mine"
    property var sel: null
    property var suSel: Nav.sub && String(Nav.sub).indexOf("dt:") === 0 ? Number(String(Nav.sub).slice(3)) : null
    property bool asking: false
    property string why: ""

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
        falcon.call("task.dept_list", {}, function (ok, r) { page.deptTasks = ok ? (r.tasks || []) : [] })
    }
    Component.onCompleted: load()
    Connections {
        target: falcon
        function onPushReceived(type, payload) { if (/^task/.test(type)) reload.restart() }
    }
    Timer { id: reload; interval: 300; onTriggered: page.load() }

    readonly property var cats: ({
        verify: ["To verify", "only you can close them"], overdue: ["Overdue", "past the final deadline"],
        quiet: ["Quiet", "nothing seen for two days"], track: ["On track", "with signs of progress"], done: ["Completed", "closed by whoever gave it"]
    })
    readonly property var order: ["verify", "overdue", "quiet", "track", "done"]
    function items(t) { var d = detail[t.id]; return d && d.items ? d.items : [] }
    function found(t) { return items(t).filter(function (i) { return i.status === "passed" }).length }
    function lastSign(t) {
        var d = detail[t.id], ex = d && d.expectations ? d.expectations : [], m = null
        ex.forEach(function (e) { var x = Time.ms(e.observed_at); if (m === null || x > m) m = x })
        return m
    }
    function cat(t) {
        if (t.status === "completed") return "done"
        var its = items(t)
        if (its.length && its.every(function (i) { return i.status === "passed" })) return "verify"
        if (t.final_deadline_at && Time.past(t.final_deadline_at)) return "overdue"
        var ls = lastSign(t)
        if (Time.now - Time.ms(t.created_at) > 48 * 3600000 && (ls === null || Time.now - ls > 48 * 3600000)) return "quiet"
        return "track"
    }
    readonly property var all: tasks.map(function (t) { return Object.assign({ k: page.cat(t), key: t.id }, t) })
        .sort(function (x, y) { return order.indexOf(x.k) - order.indexOf(y.k) || (Time.ms(x.final_deadline_at) || 9e15) - (Time.ms(y.final_deadline_at) || 9e15) })
    readonly property var rows: all.filter(function (x) {
        return (f === "" || x.k === f) && (x.id + " " + x.description_raw + " " + x.assignee_name).toLowerCase().indexOf(list.query.toLowerCase()) >= 0
    })
    readonly property var cur: { for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; return rows.length ? rows[0] : null }
    readonly property var curDetail: cur ? detail[cur.id] || null : null
    readonly property var curHost: cur ? Fleet.byAccount(cur.assignee_account_id) : null
    function n(k) { return all.filter(function (x) { return x.k === k }).length }
    function due(t, k) {
        if (k === "done") return "Closed"
        if (k === "verify") return "Handed in"
        if (!t.final_deadline_at) return "No deadline"
        return Time.left(t.final_deadline_at)
    }

    // the Super User's tasks to this Admin
    readonly property var mine: deptTasks.filter(function (t) { return t.standing !== "complete" })
        .sort(function (a, b) { return (a.my_state === "told" ? 0 : 1) - (b.my_state === "told" ? 0 : 1) })
    readonly property var suCur: { for (var i = 0; i < mine.length; i++) if (mine[i].id === suSel) return mine[i]; return mine.length ? mine[0] : null }
    readonly property var stWord: ({ told: "Not seen yet", seen: "Seen", ongoing: "Ongoing", done: "Done" })

    function verdict(outcome) {
        falcon.call("task.verify", { task_id: cur.id, outcome: outcome, reason: why.trim() }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not recorded"); return }
            Msg.ok(outcome === "complete" ? "Marked complete" : "Sent back as incomplete · " + cur.assignee_name + " sees it")
            page.asking = false; page.why = ""; page.load()
        })
    }
    function setMy(id, v) {
        falcon.call("task.dept_mark", { task_id: id, state: v }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not marked"); return }
            Msg.ok("Marked " + page.stWord[v].toLowerCase() + " · the Super User sees it"); page.load()
        })
    }

    Strip {
        width: parent.width
        on: page.f === "" ? null : page.f
        onPick: function (k) { page.f = k === null ? "" : k }
        items: ["verify", "overdue", "quiet", "track"].map(function (k) {
            return { key: k, label: page.cats[k][0], value: Theme.fmt(page.n(k)), delta: page.cats[k][1], dc: k === "overdue" && page.n(k) ? Theme.crit : undefined }
        })
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            visible: page.tab === "mine"
            width: (parent.width - 14) * 8 / 12
            title: page.f ? page.cats[page.f][0] : "Tasks"
            sub: page.f ? Theme.fmt(page.rows.length) : "what needs you first · click one to see it on the right"
            subLink: page.f ? "every task" : ""
            onSubLinkClicked: page.f = ""
            placeholder: "Find a task or person"
            tools: Segmented {
                visible: page.mine.length > 0
                options: [{ value: "mine", label: "Tasks" }, { value: "su", label: "From the Super User · " + page.mine.length }]
                value: page.tab
                onPicked: function (v) { page.tab = v }
            }
            actionLabel: "New task"
            onAction: Nav.go("tasks", "new")
            rows: page.rows
            pick: page.cur ? page.cur.id : null
            onPicked: function (k) { page.sel = k; page.asking = false }
            icon: "checksquare"
            nameTitle: "Task"
            nameText: function (r) { return r.description_raw }
            nameLine: function (r) {
                var m = Fleet.byAccount(r.assignee_account_id)
                return "T-" + r.id + " · " + r.assignee_name + (m ? " on " + m.host : "") + (r.assigner_account_id !== falcon.accountId ? " · from " + r.assigner_name : "")
            }
            cols: [
                { title: "Targets", width: 160, bar: function (r) { var n = page.items(r).length; return { v: page.found(r), max: Math.max(1, n), text: n ? page.found(r) + " of " + n + " found" : r.verification_mode === "none" ? "by hand" : "—" } } },
                { title: "Deadline", width: 150, text: function (r) { return page.due(r, r.k) } }
            ]
            now: function (r) { return [page.cats[r.k][0], r.k === "overdue" ? "bad" : r.k === "quiet" || r.k === "done" ? "wait" : "good"] }
            showEmpty: page.tasks.length === 0
            emptyIcon: "checksquare"
            emptyTitle: "No tasks yet"
            emptyText: "Describe a piece of work in plain words. The system proposes who, what done looks like and when; nothing is created until you confirm it."
            emptyAct: "New task"
            onEmptyAction: Nav.go("tasks", "new")
        }
        ListPanel {
            visible: page.tab === "su"
            width: (parent.width - 14) * 8 / 12
            title: "From the Super User"
            sub: "only they close these · say how far you have got on the right"
            tools: Segmented {
                options: [{ value: "mine", label: "Tasks" }, { value: "su", label: "From the Super User · " + page.mine.length }]
                value: page.tab
                onPicked: function (v) { page.tab = v }
            }
            rows: page.mine
            pick: page.suCur ? page.suCur.id : null
            onPicked: function (k) { page.suSel = k }
            icon: "notification"
            nameTitle: "Task"
            nameText: function (t) { return t.title }
            nameLine: function (t) { return "D-" + t.id + " · given " + Time.atDay(t.created_at) }
            cols: [{ title: "Deadline", width: 150, text: function (t) { return Time.left(t.deadline_at) } }]
            nowTitle: "Your mark"
            now: function (t) { return [t.my_state === "told" ? "New" : page.stWord[t.my_state], t.my_state === "told" ? "bad" : t.my_state === "done" ? "good" : "wait"] }
        }

        // the task beside the list
        SidePanel {
            visible: page.tab === "mine"
            width: (parent.width - 14) * 4 / 12
            readonly property var t: page.cur
            readonly property bool late: t && t.k !== "done" && t.k !== "verify" && t.final_deadline_at && Time.past(t.final_deadline_at)
            showEmpty: t === null
            emptyIcon: "checksquare"
            emptyText: "Pick a task in the list."
            title: t ? t.description_raw : ""
            sub: t && page.sel === t.id ? "the one you picked" : "the first in the list · click another"
            facts: t ? [["Task", "T-" + t.id + " · " + page.cats[t.k][0]], ["Who", t.assignee_name + (page.curHost ? " on " + page.curHost.host : "")], ["Given by", t.assigner_name],
                        ["Given", Time.atDay(t.created_at)], ["Started", t.started_at ? Time.atDay(t.started_at) : "Not yet"]]
                        .concat(t.soft_deadline_at ? [["Soft deadline", Time.atDay(t.soft_deadline_at), Theme.med]] : [])
                        .concat([["Final deadline", t.final_deadline_at ? Time.atDay(t.final_deadline_at) : "None", late ? Theme.crit : null],
                                 [t.k === "done" || t.k === "verify" ? "Handed in" : late ? "Late by" : "Time left",
                                  t.k === "done" ? "Closed" : t.k === "verify" ? "Yes" : t.final_deadline_at ? Time.span((Time.ms(t.final_deadline_at) - Time.now) / 3600000) : "—", late ? Theme.crit : null]]) : []
            actions: [
                Btn { kind: "text"; text: page.curHost ? "Open " + page.curHost.host + "'s page →" : ""; visible: page.curHost !== null; onClicked: Nav.go("machines", page.curHost.host) },
                Btn { visible: page.cur && page.cur.k !== "done" && !page.asking && page.cur.assigner_account_id === falcon.accountId; text: "Incomplete"; onClicked: page.asking = true },
                Btn { visible: page.cur && page.cur.k !== "done" && !page.asking && page.cur.assigner_account_id === falcon.accountId; kind: "primary"; text: "Complete"; onClicked: page.verdict("complete") }
            ]

            Column {
                width: parent.width
                spacing: 12
                Txt { text: "YOUR VERDICT"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Row {
                    spacing: 6
                    Txt { text: page.cur ? String(page.found(page.cur)) : ""; font.pixelSize: 22; font.weight: Font.DemiBold; elide: Text.ElideNone }
                    Txt { text: page.cur ? "of " + page.items(page.cur).length + " targets found" : ""; color: Theme.text3; anchors.baseline: parent.children[0].baseline; elide: Text.ElideNone }
                }
                Txt {
                    width: parent.width
                    color: Theme.text3; font.pixelSize: 12
                    text: page.cur ? (page.lastSign(page.cur) !== null ? "Last sign of progress " + Time.atDay(page.lastSign(page.cur)) : "No signs of progress yet") : ""
                }
                Txt {
                    readonly property var waiting: page.cur ? page.items(page.cur).filter(function (i) { return i.status !== "passed" }) : []
                    width: parent.width
                    wrapMode: Text.WordWrap
                    elide: Text.ElideNone
                    font.pixelSize: 12
                    color: waiting.some(function (i) { return i.status === "failed" }) ? Theme.med : Theme.text2
                    text: !page.cur ? "" : page.items(page.cur).length === 0 ? (page.cur.verification_mode === "none" ? "Nothing is watched. You judge it when the work is in." : "")
                          : waiting.length ? waiting.map(function (i) { return i.target_type === "program" ? i.program_name : (i.proposed_filename || i.proposed_path) }).join(", ")
                                             + (waiting.some(function (i) { return i.status === "failed" }) ? " missing at the deadline." : " not seen yet.")
                          : "Everything the task named has been found. Whether it is good enough is for you to judge."
                }
                Column {
                    visible: page.asking
                    width: parent.width
                    spacing: 8
                    TextArea2 { width: parent.width; placeholder: "What is missing? " + (page.cur ? page.cur.assignee_name : "They") + " sees this."; text: page.why; onEdited: function (t) { page.why = t } }
                    Row {
                        anchors.right: parent.right
                        spacing: 8
                        Btn { text: "Cancel"; onClicked: page.asking = false }
                        Btn { kind: "primary"; text: "Send back"; enabled: page.why.trim() !== ""; onClicked: page.verdict("incomplete") }
                    }
                }
                Txt { text: "HISTORY"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66; topPadding: 4 }
                Repeater {
                    model: {
                        var t = page.cur; if (!t) return []
                        var out = [[Time.ms(t.created_at), "Assigned by " + (t.assigner_account_id === falcon.accountId ? "you" : t.assigner_name)]]
                        if (t.started_at) out.push([Time.ms(t.started_at), t.assignee_name + " started the task"])
                        var d = page.detail[t.id]
                        ;(d && d.expectations ? d.expectations : []).slice(0, 4).forEach(function (e) { out.push([Time.ms(e.observed_at), String(e.signal_type).replace(/[._]/g, " ")]) })
                        if (t.completed_at) out.push([Time.ms(t.completed_at), "Closed as complete"])
                        return out.sort(function (a, b) { return b[0] - a[0] })
                    }
                    Item {
                        required property var modelData
                        width: parent.width; height: 26
                        Txt { width: 50; anchors.verticalCenter: parent.verticalCenter; mono: true; color: Theme.text3; font.pixelSize: 12
                              text: Time.sameDay(modelData[0], Time.now) ? Time.hhmm(modelData[0]) : Time.dayName(modelData[0]) }
                        Rectangle { x: 56; width: 7; height: 7; radius: 4; color: Theme.ser6; anchors.verticalCenter: parent.verticalCenter }
                        Txt { x: 70; width: parent.width - 70; anchors.verticalCenter: parent.verticalCenter; text: modelData[1]; color: Theme.text2 }
                    }
                }
            }
        }
        SidePanel {
            visible: page.tab === "su"
            width: (parent.width - 14) * 4 / 12
            readonly property var t: page.suCur
            showEmpty: t === null
            emptyIcon: "notification"
            emptyText: "Nothing from the Super User."
            title: t ? t.title : ""
            sub: "from the Super User · only they close it"
            facts: t ? [["Task", "D-" + t.id], ["Given", Time.atDay(t.created_at)], ["Deadline", Time.left(t.deadline_at), Time.past(t.deadline_at) ? Theme.crit : null],
                        ["Told", Theme.many(t.told, "Admin")], ["Your mark", t.my_state === "told" ? "Not marked yet" : page.stWord[t.my_state]]] : []
            Column {
                width: parent.width
                spacing: 8
                Txt { text: "HOW FAR YOU HAVE GOT"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Segmented {
                    width: parent.width
                    block: true
                    small: false
                    enabled: !Nav.inside
                    options: [{ value: "seen", label: "Seen" }, { value: "ongoing", label: "Ongoing" }, { value: "done", label: "Done" }]
                    value: page.suCur && page.suCur.my_state !== "told" ? page.suCur.my_state : null
                    onPicked: function (v) { page.setMy(page.suCur.id, v) }
                }
                Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                      text: "The Super User sees your mark at once. Only they call it complete." }
            }
        }
    }

    Panel {
        visible: page.tab === "mine" && page.cur !== null
        width: parent.width
        title: page.cur ? "Targets · " + page.cur.description_raw : ""
        sub: "what done looks like, and the signs of progress for each"
        TaskChart {
            width: parent.width
            task: page.curDetail
            handedIn: page.cur !== null && page.cur.k === "verify"
            host: page.curHost ? page.curHost.host : ""
        }
    }
}
