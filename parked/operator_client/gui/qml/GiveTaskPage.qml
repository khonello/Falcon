import QtQuick
import "."

// NEW TASK, AT THE SUPER USER'S LEVEL: give a department a task (14 Oct 2026: a page, as every other New is,
// no longer a drawer over the list). What needs doing, the department, who in it is told and the deadline on
// the left; on the right, what those Admins will see the moment it is given. No checks are set: the Admins
// say how far it has got and only the Super User completes it.
Page {
    id: page
    objectName: "giveTask"
    bare: true

    property string text: ""
    property int dept: 0
    property string who: "all"
    property var some: []
    property string dueKey: "fri"
    property var due: quick("fri")
    readonly property var dd: Fleet.dept(dept)
    readonly property var told: !dd ? [] : who === "all" || dd.admins.length < 2 ? dd.admins
        : dd.admins.filter(function (a) { return page.some.indexOf(a.account_id) >= 0 })
    function quick(k) {
        var d = new Date(Time.now)
        if (k === "today") d.setHours(17, 0, 0, 0)
        else if (k === "fri") { d.setDate(d.getDate() + ((5 - d.getDay() + 7) % 7 || 7)); d.setHours(17, 0, 0, 0) }
        else if (k === "week") { d.setDate(d.getDate() + 7); d.setHours(17, 0, 0, 0) }
        return d.toISOString()
    }
    readonly property string problem: !text.trim() ? "Say what needs doing." : !dd ? "Pick a department." : !told.length ? "Pick at least one Admin." : ""
    function presence(a) { return a.session && a.session.occupied_via === "traversal" ? "inside a machine" : a.online ? "at their desk" : "not signed in" }

    Confirm { id: confirm; page: page }
    function cancel() {
        if (!text.trim() && !dept) { Nav.go("tasks"); return }
        confirm.ask({ title: "Stop giving this task?", ok: "Discard", cancel: "Keep going", danger: true, text: "Nothing has been given. What you have written is discarded." },
                    function () { Nav.go("tasks") })
    }
    function save() {
        var p = { department_id: dept, title: text.trim(), deadline_at: due }
        if (who === "some" && dd.admins.length > 1) p.admin_ids = some
        var name = dd.name, names = Theme.listNames(told.map(function (a) { return a.name }))
        falcon.call("task.dept_create", p, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not given"); return }
            Msg.ok("Given to " + name + " · " + names + " told")
            Nav.go("tasks", r && r.task ? "dt:" + r.task.id : undefined)
        })
    }

    component Head: Txt { color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66; elide: Text.ElideNone }

    EditorShell {
        width: parent.width
        ratio: 7 / 12
        problem: page.problem
        note: page.dd ? "Given to " + page.dd.name + " as soon as you press it" : ""
        saveLabel: "Give it to them"
        onCancel: page.cancel()
        onSave: page.save()
        leftPane: Panel {
            width: parent.width
            title: "Give a department a task"
            sub: "its Admins say how far it has got; only you complete it"
            pad: 20
            Column {
                width: parent.width
                spacing: 22
                Column {
                    width: parent.width; spacing: 8
                    Head { text: "WHAT NEEDS DOING" }
                    TextArea2 { objectName: "giveText"; width: parent.width; minRows: 3; maxRows: 6; maxLength: 200; placeholder: "Collect the signed leave forms from every team"
                                text: page.text; onEdited: function (t) { page.text = t } }
                }
                Column {
                    width: parent.width; spacing: 8
                    Head { text: "DEPARTMENT" }
                    Select { width: Math.min(420, parent.width); search: true; placeholder: "Which department?"; value: page.dept || null
                             options: Fleet.depts.map(function (d) { return { value: d.id, label: d.admins.length ? d.name : d.name + " · no Admin", disabled: !d.admins.length } })
                             onPicked: function (v) { page.dept = v; page.some = [] } }
                    Txt { visible: !page.dd; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                          text: "A department with no Admin cannot take a task. Assign one first, from Departments." }
                }
                Column {
                    visible: page.dd !== null && page.dd.admins.length > 1
                    width: parent.width; spacing: 8
                    Head { text: "WHO IS TOLD" }
                    Segmented { small: false; options: [{ value: "all", label: page.dd ? "Every Admin in " + page.dd.name + " (" + page.dd.admins.length + ")" : "" }, { value: "some", label: "Only some" }]
                                value: page.who; onPicked: function (v) { page.who = v } }
                    Select { visible: page.who === "some"; width: Math.min(420, parent.width); multiple: true; placeholder: "Which Admins?"; values: page.some
                             options: page.dd ? page.dd.admins.map(function (a) { return { value: a.account_id, label: a.name + " · " + page.presence(a) } }) : []
                             onPicked: function (v) { page.some = v } }
                }
                Column {
                    width: parent.width; spacing: 8
                    Head { text: "DEADLINE" }
                    Segmented { small: false; options: [{ value: "today", label: "End of today" }, { value: "fri", label: "Friday 17:00" }, { value: "week", label: "In a week" }, { value: "pick", label: "Pick a date" }]
                                value: page.dueKey; onPicked: function (v) { page.dueKey = v; if (v !== "pick") page.due = page.quick(v) } }
                    DateTimeField { visible: page.dueKey === "pick"; width: 220; value: page.due; onChanged: function (v) { page.due = v } }
                    Txt { text: "Due " + Time.date(page.due) + "."; color: Theme.text3; font.pixelSize: 12 }
                }
            }
        }
        rightPane: Panel {
            width: parent.width
            title: "What they see"
            sub: "the moment you give it"
            Column {
                width: parent.width
                spacing: 16
                // the strip across the top of every page of their console, as it will read
                Rectangle {
                    width: parent.width; height: 40; radius: 6
                    color: Theme.accentSoft; border.width: 1; border.color: Theme.alpha(Theme.accent, 0.35)
                    Row {
                        x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 12
                        Icon { name: "notification"; size: 15; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter }
                        Txt { id: stripHead; text: "New task from the Super User"; font.weight: Font.DemiBold; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                        Txt { text: page.text.trim() || "What needs doing"; color: page.text.trim() ? Theme.text : Theme.text4
                              width: Math.max(0, Math.min(implicitWidth, parent.parent.width - 24 - 15 - stripHead.width - stripDue.width - 36)); anchors.verticalCenter: parent.verticalCenter }
                        Txt { id: stripDue; mono: true; elide: Text.ElideNone; text: "due " + Time.atDay(page.due).replace("Today", "today"); anchors.verticalCenter: parent.verticalCenter }
                    }
                }
                Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                      text: "On every page of their console until they mark it seen. You see when each of them does." }
                Column {
                    width: parent.width; spacing: 6
                    Row { spacing: 6
                          Head { text: "TOLD" }
                          Txt { visible: page.told.length > 0; text: String(page.told.length); color: Theme.text4; font.pixelSize: 11; elide: Text.ElideNone } }
                    Repeater {
                        model: page.told
                        PersonRow { required property var modelData; width: parent.width; name: modelData.name
                                    sub: page.presence(modelData) + (modelData.hostname ? " · " + modelData.hostname : "")
                                    dot: modelData.session && modelData.session.occupied_via === "traversal" ? Theme.ser3 : modelData.online ? Theme.ok : Theme.text4 }
                    }
                    Txt { visible: !page.told.length; width: parent.width; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                          text: page.dd ? "Nobody picked yet." : "Pick a department to see who is told." }
                    Txt { visible: page.dd !== null && page.who === "some" && page.dd.admins.length > 1 && page.told.length > 0; width: parent.width; topPadding: 4
                          color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                          text: page.dd ? "The others in " + page.dd.name + " do not see it." : "" }
                }
                Rectangle {
                    width: parent.width; height: nn.height + 20; radius: 6; color: Theme.surface2
                    Txt { id: nn; x: 12; y: 10; width: parent.width - 24; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                          text: "No checks are set: the Admins say how far it has got, and you decide when it is complete. Nothing is closed for you." }
                }
            }
        }
    }
}
