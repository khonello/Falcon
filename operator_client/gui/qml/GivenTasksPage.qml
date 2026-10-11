import QtQuick
import "."

// TASKS, AT THE SUPER USER'S LEVEL: work given to departments. No checks -- such work is rarely a file or
// a program. Every Admin told marks it seen, ongoing or done; the furthest any has got is where it
// stands; only the Super User calls it complete. The list, the task beside it with that decision, and
// how far each Admin has got drawn under both. New task opens a drawer.
Page {
    id: page
    objectName: "tasksView"

    property var tasks: []
    property string f: ""
    property var sel: Nav.sub && String(Nav.sub).indexOf("dt:") === 0 ? Number(String(Nav.sub).slice(3)) : null
    property string note: ""

    function load() { falcon.call("task.dept_list", {}, function (ok, r) { page.tasks = ok ? (r.tasks || []) : [] }) }
    Component.onCompleted: load()
    Connections { target: falcon; function onPushReceived(type) { if (/^task\.dept/.test(type)) page.load() } }

    readonly property var cats: ({ verify: ["Ready to complete", "A department marked it done. Only you can complete it."], late: ["Late", "Past its deadline and not done."],
                                   unseen: ["Not seen yet", "Nobody told has opened it."], track: ["Under way", "Seen or ongoing, before its deadline."] })
    function catOf(t) { return t.standing === "done" ? "verify" : Time.past(t.deadline_at) ? "late" : t.standing === "told" ? "unseen" : "track" }
    readonly property var open: tasks.filter(function (t) { return t.standing !== "complete" })
        .sort(function (a, b) { var o = ["verify", "late", "unseen", "track"]; return o.indexOf(page.catOf(a)) - o.indexOf(page.catOf(b)) || Time.ms(a.deadline_at) - Time.ms(b.deadline_at) })
    readonly property var rows: open.filter(function (t) { return (f === "" || page.catOf(t) === f) && (t.title + " " + Fleet.deptName(t.department_id) + " D-" + t.id).toLowerCase().indexOf(list.query.toLowerCase()) >= 0 })
    readonly property var t: { for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; return rows.length ? rows[0] : null }
    readonly property var dstate: ({ told: ["Not seen yet", Theme.text4], seen: ["Seen", Theme.ser1], ongoing: ["Ongoing", Theme.med], done: ["Done", Theme.ok], complete: ["Complete", Theme.ok] })
    function standingText(x) {
        var adm = x.admins || [], who = adm.filter(function (a) { return a.state === x.standing }).map(function (a) { return a.name }), seen = adm.filter(function (a) { return a.state !== "told" }).length
        return x.standing === "done" ? "Done · " + (who[0] || "") : x.standing === "ongoing" ? "Ongoing · " + who.join(", ") : x.standing === "seen" ? "Seen by " + seen + " of " + adm.length : "Not seen · " + adm.length + " told"
    }

    function complete() { falcon.call("task.dept_complete", { task_id: t.id }, function (ok, r) { if (!ok) { Msg.failed(r.message || "Not done"); return } Msg.ok("Marked complete, with your name and the time"); page.sel = null; page.load() }) }
    function back() { falcon.call("task.dept_reopen", { task_id: t.id, note: note.trim() }, function (ok, r) { if (!ok) { Msg.failed(r.message || "Not sent"); return } Msg.ok("Sent back as ongoing"); page.note = ""; page.load() }) }

    Strip {
        width: parent.width
        on: page.f === "" ? null : page.f
        onPick: function (k) { page.f = k === null ? "" : k }
        items: ["verify", "late", "unseen", "track"].map(function (k) {
            var n = page.open.filter(function (x) { return page.catOf(x) === k }).length
            return { key: k, label: page.cats[k][0], value: Theme.fmt(n), delta: k === "late" && n ? "past the deadline" : k === "verify" && n ? "only you can complete" : "", dc: k === "late" && n ? Theme.crit : undefined }
        })
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            title: page.f ? page.cats[page.f][0] : "Given to departments"
            sub: page.f ? Theme.fmt(page.rows.length) : "most urgent first · click one to see it on the right"
            subLink: page.f ? "show all " + page.open.length : ""
            onSubLinkClicked: page.f = ""
            placeholder: "Filter by task or department"
            actionLabel: "New task"
            onAction: newTask.start()
            rows: page.rows
            pick: page.t ? page.t.id : null
            onPicked: function (k) { page.sel = k; page.note = "" }
            icon: "checksquare"
            nameTitle: "Task"
            nameText: function (x) { return x.title }
            nameLine: function (x) { return "D-" + x.id + " · " + Fleet.deptName(x.department_id) }
            cols: [{ title: "Told", text: function (x) { return Theme.listNames((x.admins || []).map(function (a) { return a.name })) } },
                   { title: "Deadline", width: 150, bar: function (x) { var a = Time.ms(x.created_at), b = Time.ms(x.deadline_at); return { v: Math.max(0, Math.min(1, (Time.now - a) / Math.max(1, b - a))), max: 1, text: Time.left(x.deadline_at) } } }]
            now: function (x) { var k = page.catOf(x); return k === "verify" ? ["Ready to complete", "good"] : k === "late" ? ["Past its deadline", "bad"] : k === "unseen" ? ["Not seen yet", "wait"] : ["Under way", "good"] }
            showEmpty: page.open.length === 0
            emptyIcon: "checksquare"
            emptyTitle: "Nothing given to a department"
            emptyText: "A task goes to a department's Admins. They say how far it has got; only you call it complete."
            emptyAct: "New task"
            onEmptyAction: newTask.start()
        }
        SidePanel {
            width: (parent.width - 14) * 4 / 12
            showEmpty: page.t === null
            emptyIcon: "checksquare"
            emptyTitle: "Nothing given"
            emptyText: "Give a department a task; it shows here when you pick it."
            title: page.t ? page.t.title : ""
            sub: page.t && page.sel === page.t.id ? "the one you picked" : "the most urgent · click another"
            facts: page.t ? [["Department", Fleet.deptName(page.t.department_id)], ["Told", Theme.listNames((page.t.admins || []).map(function (a) { return a.name }))],
                             ["Given", Time.atDay(page.t.created_at)], ["Deadline", Time.atDay(page.t.deadline_at) + " · " + Time.left(page.t.deadline_at), Time.past(page.t.deadline_at) ? Theme.crit : null],
                             ["Where it stands", page.dstate[page.t.standing][0], page.dstate[page.t.standing][1]]] : []
            actions: Btn { iconName: "edit"; text: "Edit"; enabled: false; tip: "Changing a department task is not built in the Engine yet" }
            Column {
                width: parent.width
                spacing: 8
                Txt { text: "YOUR DECISION"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Column {
                    visible: page.t !== null && page.t.standing === "done"
                    width: parent.width
                    spacing: 8
                    Txt { width: parent.width; text: (page.t ? Fleet.deptName(page.t.department_id) : "") + " marked it done. Only you can complete it."; color: Theme.text2; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                    Field { width: parent.width; height: Theme.controlSm; placeholderText: "A note for them, if you send it back"; text: page.note; onTextEdited: page.note = text }
                    Row { width: parent.width; spacing: 8
                          Btn { width: (parent.width - 8) / 2; text: "Not done yet"; enabled: page.note.trim() !== ""; onClicked: page.back() }
                          Btn { width: (parent.width - 8) / 2; kind: "primary"; text: "Complete"; onClicked: page.complete() } }
                }
                Txt { visible: page.t !== null && page.t.standing !== "done"; text: "Nobody has marked it done yet."; color: Theme.text3; font.pixelSize: 12 }
                Repeater {
                    model: page.t ? (page.t.notes || []) : []
                    Txt { required property var modelData; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text2; font.pixelSize: 12
                          text: "“" + modelData.text + "” · " + (modelData.by || "") + ", " + Time.at(modelData.at) }
                }
            }
        }
    }

    Panel {
        visible: page.t !== null
        width: parent.width
        title: page.t ? "How far it has got · " + page.t.title : ""
        sub: page.t ? Fleet.deptName(page.t.department_id) + " · the same task as on the right" : ""
        TaskPath { width: parent.width; task: page.t }
    }

    // --- give a department a task -------------------------------------------------------------------
    Drawer {
        id: newTask
        page: page
        width: 480
        title: "Give a department a task"
        property string text: ""
        property int dept: 0
        property string who: "all"
        property var some: []
        property string dueKey: "fri"
        property var due: null
        readonly property var dd: Fleet.dept(dept)
        readonly property var told: dd ? (who === "all" ? dd.admins : dd.admins.filter(function (a) { return newTask.some.indexOf(a.account_id) >= 0 })) : []
        function quick(k) {
            var d = new Date(Time.now)
            if (k === "today") d.setHours(17, 0, 0, 0)
            else if (k === "fri") { d.setDate(d.getDate() + ((5 - d.getDay() + 7) % 7 || 7)); d.setHours(17, 0, 0, 0) }
            else if (k === "week") { d.setDate(d.getDate() + 7); d.setHours(17, 0, 0, 0) }
            return d.toISOString()
        }
        function start() { text = ""; dept = 0; who = "all"; some = []; dueKey = "fri"; due = quick("fri"); open() }
        note: !text.trim() ? "Say what needs doing." : !dd ? "Pick a department." : who === "some" && !some.length ? "Pick at least one Admin." : ""
        footer: [
            Btn { text: "Cancel"; onClicked: newTask.close() },
            Btn { kind: "primary"; text: "Give it to them"; enabled: newTask.note === ""
                  onClicked: {
                      var p = { department_id: newTask.dept, title: newTask.text.trim(), deadline_at: newTask.due }
                      if (newTask.who === "some") p.admin_ids = newTask.some
                      falcon.call("task.dept_create", p, function (ok, r) {
                          if (!ok) { Msg.failed(r && r.message ? r.message : "Not given"); return }
                          Msg.ok("Given to " + newTask.dd.name + " · " + Theme.listNames(newTask.told.map(function (a) { return a.name })) + " told")
                          newTask.close(); page.load()
                      })
                  } }
        ]
        Column {
            width: parent.width; spacing: 6
            Txt { text: "WHAT NEEDS DOING"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
            TextArea2 { width: parent.width; minRows: 3; maxRows: 6; maxLength: 200; placeholder: "Collect the signed leave forms from every team"; text: newTask.text; onEdited: function (t) { newTask.text = t } }
        }
        Column {
            width: parent.width; spacing: 6
            Txt { text: "DEPARTMENT"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
            Select { width: parent.width; search: true; placeholder: "Which department?"; value: newTask.dept || null
                     options: Fleet.depts.map(function (d) { return { value: d.id, label: d.admins.length ? d.name : d.name + " · no Admin", disabled: !d.admins.length } })
                     onPicked: function (v) { newTask.dept = v; newTask.some = [] } }
            Column {
                visible: newTask.dd !== null && newTask.dd.admins.length > 1
                width: parent.width; spacing: 8; topPadding: 6
                Txt { text: "WHO IS TOLD"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Segmented { small: false; options: [{ value: "all", label: newTask.dd ? "Every Admin in " + newTask.dd.name + " (" + newTask.dd.admins.length + ")" : "" }, { value: "some", label: "Only some" }]
                            value: newTask.who; onPicked: function (v) { newTask.who = v } }
                Select { visible: newTask.who === "some"; width: parent.width; multiple: true; placeholder: "Which Admins?"; values: newTask.some
                         options: newTask.dd ? newTask.dd.admins.map(function (a) { return { value: a.account_id, label: a.name } }) : []
                         onPicked: function (v) { newTask.some = v } }
            }
            Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12; topPadding: 4
                  text: !newTask.dd ? "" : !newTask.dd.admins.length ? "A department with no Admin cannot take a task. Assign one first."
                        : newTask.told.length ? Theme.listNames(newTask.told.map(function (a) { return a.name }), 3) + (newTask.told.length === 1 ? " is" : " are") + " told as soon as you give it, on every page of their console until they mark it seen." : "Nobody picked yet." }
        }
        Column {
            width: parent.width; spacing: 8
            Txt { text: "DEADLINE"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
            Segmented { small: false; options: [{ value: "today", label: "End of today" }, { value: "fri", label: "Friday 17:00" }, { value: "week", label: "In a week" }, { value: "pick", label: "Pick a date" }]
                        value: newTask.dueKey; onPicked: function (v) { newTask.dueKey = v; if (v !== "pick") newTask.due = newTask.quick(v) } }
            DateTimeField { visible: newTask.dueKey === "pick"; width: 220; value: newTask.due; onChanged: function (v) { newTask.due = v } }
            Txt { text: "Due " + Time.date(newTask.due) + "."; color: Theme.text3; font.pixelSize: 12 }
        }
        Rectangle {
            width: parent.width; height: nn.height + 20; radius: 6; color: Theme.surface2
            Txt { id: nn; x: 12; y: 10; width: parent.width - 24; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                  text: "No checks are set: the Admins say how far it has got, and you decide when it is complete. Nothing is closed for you." }
        }
    }
}
