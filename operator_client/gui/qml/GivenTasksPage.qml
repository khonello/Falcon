import QtQuick
import "."

// TASKS, AT THE SUPER USER'S LEVEL: what has been given to each department, and how far it has got. This is a view, not a workbench: the organisation by department, each card a bar of
// where its tasks stand and a few of them as lines. The Super User does two things here and only two: give a department a task (its own page), and call a task complete once the
// department says it is done (or send it back). A click on a line opens the task in a narrow drawer. No checks: such work is rarely a file or a program.
Page {
    id: page
    objectName: "tasksView"

    property var tasks: []
    property var cur: null                       // the task open in the drawer
    property string note: ""

    function load() { falcon.call("task.dept_list", {}, function (ok, r) { page.tasks = ok ? (r.tasks || []) : [] }) }
    Component.onCompleted: load()
    Connections { target: falcon; function onConnected() { page.load() } function onPushReceived(type) { if (/^task\.dept/.test(type)) page.load() } }

    function catOf(t) { return t.standing === "done" ? "verify" : Time.past(t.deadline_at) ? "late" : t.standing === "told" ? "unseen" : "track" }
    readonly property var tone: ({ verify: Theme.accent, late: Theme.crit, unseen: Theme.text4, track: Theme.ok })
    readonly property var open: tasks.filter(function (t) { return t.standing !== "complete" })
    function inDept(id) {
        var o = ["verify", "late", "unseen", "track"]
        return open.filter(function (t) { return t.department_id === id })
            .sort(function (a, b) { return o.indexOf(page.catOf(a)) - o.indexOf(page.catOf(b)) || Time.ms(a.deadline_at) - Time.ms(b.deadline_at) })
    }
    function segsOf(list) { return ["verify", "late", "unseen", "track"].map(function (k) { return { n: list.filter(function (t) { return page.catOf(t) === k }).length, c: page.tone[k] } }) }
    function aside(t) {
        var k = catOf(t)
        return k === "verify" ? "Done · yours to close" : k === "late" ? Time.left(t.deadline_at) : t.standing === "ongoing" ? "Ongoing" : t.standing === "seen" ? "Seen" : "Not seen"
    }
    readonly property int ready: open.filter(function (t) { return page.catOf(t) === "verify" }).length
    readonly property int late: open.filter(function (t) { return page.catOf(t) === "late" }).length
    readonly property var dstate: ({ told: ["Not seen yet", Theme.text4], seen: ["Seen", Theme.ser1], ongoing: ["Ongoing", Theme.med], done: ["Done", Theme.ok], complete: ["Complete", Theme.ok] })

    function complete() { falcon.call("task.dept_complete", { task_id: cur.id }, function (ok, r) { if (!ok) { Msg.failed(r.message || "Not done"); return } Msg.ok("Marked complete, with your name and the time"); drawer.close(); page.load() }) }
    function back() { falcon.call("task.dept_reopen", { task_id: cur.id, note: note.trim() }, function (ok, r) { if (!ok) { Msg.failed(r.message || "Not sent"); return } Msg.ok("Sent back as ongoing"); page.note = ""; drawer.close(); page.load() }) }
    function show(t) { page.note = ""; page.cur = t; drawer.open() }

    // --- the head: one line of where things stand, and the one thing to do -------------------------------------------------------------------------------------
    Item {
        width: parent.width
        height: 34
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 18
            Txt { text: Theme.fmt(page.open.length) + " open"; font.weight: Font.DemiBold; elide: Text.ElideNone }
            Row { spacing: 6; visible: page.ready > 0; Rectangle { width: 8; height: 8; radius: 2; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter } Txt { text: page.ready + " done, yours to close"; color: Theme.text2; elide: Text.ElideNone } }
            Row { spacing: 6; visible: page.late > 0; Rectangle { width: 8; height: 8; radius: 2; color: Theme.crit; anchors.verticalCenter: parent.verticalCenter } Txt { text: page.late + " past their date"; color: Theme.text2; elide: Text.ElideNone } }
            Row { spacing: 6; Rectangle { width: 8; height: 8; radius: 2; color: Theme.ok; anchors.verticalCenter: parent.verticalCenter } Txt { text: "under way"; color: Theme.text3; elide: Text.ElideNone } }
            Row { spacing: 6; Rectangle { width: 8; height: 8; radius: 2; color: Theme.text4; anchors.verticalCenter: parent.verticalCenter } Txt { text: "not seen"; color: Theme.text3; elide: Text.ElideNone } }
        }
        Btn { objectName: "giveTask"; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; kind: "primary"; iconName: "plus"; text: "Give a task"; onClicked: Nav.go("tasks", "new") }
    }

    // --- the organisation, a card a department ----------------------------------------------------------------------------------------------------------------
    Grid {
        objectName: "deptCards"
        width: parent.width
        columns: 2
        columnSpacing: 14
        rowSpacing: 14
        Repeater {
            model: Fleet.depts
            DeptCard {
                required property var modelData
                readonly property var mine: page.inDept(modelData.id)
                width: (page.w - 14) / 2
                title: modelData.name
                sub: modelData.admins.length ? Theme.listNames(modelData.admins.map(function (a) { return a.name })) : ""
                noAdmin: modelData.admins.length === 0
                segs: page.segsOf(mine)
                total: mine.length ? Theme.fmt(mine.length) + " open" : ""
                Column {
                    width: parent.width
                    Repeater {
                        model: mine.slice(0, 4)
                        DeptLine { required property var modelData; dot: page.tone[page.catOf(modelData)]; text: modelData.title; aside: page.aside(modelData); asideTone: page.catOf(modelData) === "late" ? Theme.crit : page.catOf(modelData) === "verify" ? Theme.accent : Theme.text3
                                   onClicked: page.show(modelData) }
                    }
                    Item { visible: mine.length > 4; width: parent.width; height: 26
                           More { x: 6; anchors.verticalCenter: parent.verticalCenter; n: mine.length - 4; what: "tasks"; onClicked: page.show(mine[4]) } }
                    Item { visible: mine.length === 0; width: parent.width; height: 60
                           Txt { anchors.centerIn: parent; text: modelData.admins.length ? "Nothing given to this department" : "No Admin to take a task"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
                }
            }
        }
    }
    Empty { visible: Fleet.loaded && Fleet.depts.length === 0; width: parent.width; h: 200; icon: "apartment"; title: "No departments yet"; text: "Tasks are given to a department's Admins." }

    // --- one task, in a narrow drawer ----------------------------------------------------------------------------------------------------------------------
    Drawer {
        id: drawer
        page: page
        width: 460
        title: page.cur ? page.cur.title : ""
        Column {
            width: parent.width
            spacing: 14
            Column {
                width: parent.width
                Repeater {
                    model: page.cur ? [["Department", Fleet.deptName(page.cur.department_id)], ["Told", Theme.listNames((page.cur.admins || []).map(function (a) { return a.name }))],
                                       ["Given", Time.atDay(page.cur.created_at)], ["Deadline", Time.atDay(page.cur.deadline_at) + " · " + Time.left(page.cur.deadline_at)],
                                       ["Where it stands", page.dstate[page.cur.standing][0]]] : []
                    Item {
                        required property var modelData
                        width: parent.width; height: 30
                        Txt { width: 110; anchors.verticalCenter: parent.verticalCenter; text: modelData[0]; color: Theme.text3 }
                        Txt { x: 122; width: parent.width - 122; anchors.verticalCenter: parent.verticalCenter; text: modelData[1]; color: modelData[0] === "Deadline" && page.cur && Time.past(page.cur.deadline_at) ? Theme.crit : Theme.text }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
            }
            Column {
                visible: page.cur !== null && page.cur.standing === "done"
                width: parent.width
                spacing: 8
                Txt { text: "YOUR DECISION"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Txt { width: parent.width; text: (page.cur ? Fleet.deptName(page.cur.department_id) : "") + " marked it done. Only you can complete it."; color: Theme.text2; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                Field { objectName: "taskNote"; width: parent.width; height: Theme.controlSm; placeholderText: "A note for them, if you send it back"; text: page.note; onTextEdited: page.note = text }
                Row { width: parent.width; spacing: 8
                      Btn { objectName: "taskBack"; width: (parent.width - 8) / 2; text: "Not done yet"; enabled: page.note.trim() !== ""; onClicked: page.back() }
                      Btn { objectName: "taskComplete"; width: (parent.width - 8) / 2; kind: "primary"; text: "Complete"; onClicked: page.complete() } }
            }
            Txt { visible: page.cur !== null && page.cur.standing !== "done"; text: "Nobody has marked it done yet."; color: Theme.text3; font.pixelSize: 12 }
            Column {
                visible: page.cur !== null
                width: parent.width
                spacing: 6
                Txt { text: "HOW FAR EACH ADMIN HAS GOT"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Repeater {
                    model: page.cur ? (page.cur.admins || []) : []
                    Row {
                        required property var modelData
                        spacing: 8
                        Rectangle { width: 8; height: 8; radius: 2; color: (page.dstate[modelData.state] || page.dstate.told)[1]; anchors.verticalCenter: parent.verticalCenter }
                        Txt { text: modelData.name + " · " + (page.dstate[modelData.state] || page.dstate.told)[0]; color: Theme.text2; elide: Text.ElideNone }
                    }
                }
            }
            Repeater {
                model: page.cur ? (page.cur.notes || []) : []
                Txt { required property var modelData; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text2; font.pixelSize: 12
                      text: "“" + modelData.text + "” · " + (modelData.by || "") + ", " + Time.at(modelData.at) }
            }
        }
    }
}
