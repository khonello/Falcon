import QtQuick
import "."

// NEW RULE (and Edit), in four steps: When -> On -> Do -> Review. Steps at the top with Cancel beside
// them (it asks before discarding), one step's body, and Back / Next that waits for the step to be
// valid. The rule reads as one sentence the whole way through. The Do step offers only the action
// library: a new custom action is written on Actions, then used here.
Page {
    id: page
    objectName: "newRule"
    bare: true

    readonly property int editId: Nav.sub && String(Nav.sub).indexOf("edit-") === 0 ? Number(String(Nav.sub).slice(5)) : 0
    property int step: 0
    property string kind: "Event"
    property string ev: "usb.inserted"
    property string mtr: "cpu"
    property int val: 90
    property int mins: 5
    property var days: [0, 1, 2, 3, 4]
    property string at: "09:00"
    property string scope: Nav.boss ? "all" : "all"
    property int dept: 0
    property var hosts: []
    property var acts: []                  // action ids, in order
    property string name: ""
    property bool idle: false
    property var lib: []                   // the action library, flattened
    property var original: null
    property var existing: []              // the rules there are, to start from a copy
    property string base: "blank"

    readonly property var eventChoices: ["usb.inserted", "resource.violation", "user.login", "user.logout", "system.idle", "program.launched", "file.modified", "network.disconnected", "flow.failed"]
    Component.onCompleted: {
        falcon.call("control.action_list", {}, function (ok, r) {
            var a = ok ? (r.actions || {}) : {}, out = []
            ;["control", "monitoring", "custom"].forEach(function (k) { (a[k] || []).forEach(function (x) { out.push(Object.assign({ cat: k }, x)) }) })
            page.lib = out
            if (!page.editId && out.length && !page.acts.length) page.acts = [out.filter(function (x) { return x.builtin_type === "notify" })[0] || out[0]].map(function (x) { return x.id })
        })
        falcon.call("control.event_list", {}, function (ok, r) {
            page.existing = ok ? (r.events || []) : []
            if (!page.editId) return
            var e = page.existing.filter(function (x) { return x.id === page.editId })[0]
            if (!e) return
            page.load(e)
        })
    }
    // fill the builder from a rule: itself when editing, or a copy of it to start from
    function load(e) {
            var s = e.condition_spec || {}, m = s.match || {}
            page.original = e
            page.kind = Auto.kind(s.type)
            if (page.kind === "Event") page.ev = s.type
            if (s.type === "threshold.cpu" || s.type === "threshold.memory") { page.mtr = s.type === "threshold.cpu" ? "cpu" : "memory"; page.val = m.percent || 90; page.mins = Math.round((m.duration_s || 0) / 60) }
            if (s.type === "time.recurring") { page.at = m.at || "09:00"; page.days = m.days || [0, 1, 2, 3, 4] }
            page.scope = s.pc_ids && s.pc_ids.length ? "pick" : "all"
            page.hosts = s.pc_ids || []
            page.acts = (e.actions || []).map(function (a) { return a.id })
            page.name = e.name || ""          // a rule without a name keeps being worded from what it watches
    }
    function startFrom(v) {
        base = String(v); step = 0
        if (v === "blank") { kind = "Event"; ev = "usb.inserted"; scope = "all"; hosts = []; name = ""
                             acts = lib.length ? [(lib.filter(function (x) { return x.builtin_type === "notify" })[0] || lib[0]).id] : []; return }
        var e = existing.filter(function (x) { return String(x.id) === String(v) })[0]
        if (e) { load(e); name = "Copy of " + Auto.nameOf(e) }
    }
    readonly property string type: kind === "Event" ? ev : kind === "Threshold" ? (mtr === "cpu" ? "threshold.cpu" : "threshold.memory") : "time.recurring"
    readonly property var match: kind === "Threshold" ? { percent: val, duration_s: mins * 60 } : kind === "Schedule" ? { at: at, days: days } : {}
    readonly property var targets: scope === "all" ? Fleet.machines : scope === "dept" ? Fleet.inDept(dept) : Fleet.machines.filter(function (m) { return page.hosts.indexOf(m.pc_id) >= 0 })
    readonly property string whenTxt: Auto.whenOf({ condition_spec: { type: type, match: match } })
    readonly property string whereTxt: scope === "all" ? "any machine" : scope === "dept" ? "a " + Fleet.deptName(dept) + " machine" : targets.map(function (m) { return m.host }).join(", ") || "no machines yet"
    function actName(id) { var a = lib.filter(function (x) { return x.id === id })[0]; return a ? a.name : "an action" }
    readonly property string doTxt: acts.length ? acts.map(page.actName).join(", then ") : ""
    readonly property var problems: [kind === "Schedule" && !days.length ? "Pick at least one day." : "", targets.length ? "" : "Pick at least one machine.", acts.length ? "" : "Add at least one action.", ""]
    readonly property bool ok: problems.every(function (p) { return p === "" })

    Confirm { id: confirm; page: page }
    function cancel() {
        if (step === 0 && !editId) { Nav.go("automation"); return }
        confirm.ask({ title: page.editId ? "Stop editing this rule?" : "Stop creating this rule?", text: "Nothing has been saved. What you have set so far is discarded.",
                      ok: "Discard", cancel: "Keep going", danger: true }, function () { Nav.go("automation") })
    }
    function save() {
        var pcs = scope === "all" ? null : targets.map(function (m) { return m.pc_id })
        var done = function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not saved"); return }
            Msg.ok(page.editId ? "Changes saved" : "Rule saved and switched on"); Nav.go("automation")
        }
        // the name is saved with the rule (the Engine keeps it); without one the rule is worded from what it watches
        if (editId) falcon.call("control.event_update", { event_id: editId, match: match, pc_ids: pcs, action_ids: acts, name: name.trim() }, done)
        else falcon.call("control.event_create", { type: type, match: match, pc_ids: pcs, action_ids: acts, enabled: true, name: name.trim() }, done)
    }
    // Test on one machine: a saved rule runs as itself (control.event_test, recorded as run by hand, not a firing);
    // a rule not saved yet runs its actions by hand on the first machine that is online
    function testOnce() {
        var on = targets.filter(function (m) { return m.online })[0]
        if (!on || !acts.length) { Msg.warn("No machine it applies to is online"); return }
        if (editId) {
            falcon.call("control.event_test", { event_id: editId, pc_id: on.pc_id }, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Not run"); return }
                Msg.ok("Ran once on " + on.host + " · recorded as run by hand")
            })
            return
        }
        acts.forEach(function (a) { falcon.call("control.action_run", { action_id: a, pc_id: on.pc_id }, function () {}) })
        Msg.ok("Ran once on " + on.host + " · recorded as run by hand")
    }

    component Head: Column {
        property string t: ""
        property string d: ""
        width: parent ? parent.width : 0
        spacing: 2
        bottomPadding: 22
        Txt { text: parent.t; font.pixelSize: Theme.fTitle; font.weight: Font.DemiBold; width: parent.width }
        Txt { text: parent.d; color: Theme.text3; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone }
    }
    component FieldRow: Row {
        property string label: ""
        default property alias inner: fr.data
        spacing: 0
        Txt { width: 130; text: parent.label; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
        Row { id: fr; spacing: 10; anchors.verticalCenter: parent.verticalCenter }
    }

    Item {
        width: parent.width
        height: wiz.height
        Column {
            id: wiz
            width: Math.min(980, parent.width)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 14
            Row {
                visible: !page.editId && page.existing.length > 0
                width: parent.width
                spacing: 10
                clip: true
                Txt { text: "Start from"; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
                Segmented {
                    small: false
                    options: [{ value: "blank", label: "Blank" }].concat(page.existing.slice(0, 6).map(function (e) { return { value: String(e.id), label: Auto.nameOf(e) } }))
                    value: page.base
                    onPicked: function (v) { page.startFrom(v) }
                }
            }
            Rectangle {
                width: parent.width
                height: wcol.height
                radius: Theme.radius
                color: Theme.surface
                border.width: 1
                border.color: Theme.border
                Column {
                    id: wcol
                    width: parent.width
                    Item {
                        width: parent.width; height: 86
                        Steps {
                            x: 28; y: 20
                            width: parent.width - 28 - 130
                            current: page.step
                            steps: [{ title: "When", desc: "What starts the rule" }, { title: "On", desc: "Which machines it watches" },
                                    { title: "Do", desc: "What happens when it fires" }, { title: "Review", desc: "Name it and check it" }]
                                   .map(function (s, i) { return Object.assign({ error: i < page.step && page.problems[i] !== "" }, s) })
                            onPicked: function (i) { page.step = i }
                        }
                        Btn { kind: "text"; iconName: "close"; text: "Cancel"; anchors.right: parent.right; anchors.rightMargin: 20; y: 20; onClicked: page.cancel() }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
                    }
                    Column {
                        x: 28
                        width: parent.width - 56
                        topPadding: 32; bottomPadding: 36
                        spacing: 14
                        // step 1: when
                        Column {
                            visible: page.step === 0
                            width: parent.width
                            spacing: 14
                            Head { t: "When should this rule fire?"; d: page.editId ? "What starts a rule cannot change once it is saved; its details can." : "Pick what kind of thing starts it, then the details." }
                            Row {
                                width: parent.width
                                spacing: 12
                                Repeater {
                                    model: [["Event", "thunderbolt", "Something happens", "A device is plugged in, a file appears, someone signs in. Reported the moment it happens."],
                                            ["Threshold", "linechart", "A reading crosses a line", "CPU or memory stays above a level for a while. Checked every 30 seconds."],
                                            ["Schedule", "clock", "On a schedule", "At a time on chosen days, by the Engine's clock."]]
                                    Choice { required property var modelData; width: (parent.width - 24) / 3; on: page.kind === modelData[0]; icon: modelData[1]; title: modelData[2]; desc: modelData[3]
                                             disabled: page.editId > 0 && page.kind !== modelData[0]; onClicked: page.kind = modelData[0] }
                                }
                            }
                            Item { width: 1; height: 12 }
                            FieldRow { visible: page.kind === "Event"; label: "Event"
                                       Select { width: 380; enabled: !page.editId; value: page.ev; options: page.eventChoices.map(function (t) { var w = Auto.when[t]; return { value: t, label: w.charAt(0).toUpperCase() + w.slice(1) } })
                                                onPicked: function (v) { page.ev = v } } }
                            FieldRow { visible: page.kind === "Threshold"; label: "Reading"
                                       Select { width: 140; enabled: !page.editId; value: page.mtr; options: [{ value: "cpu", label: "CPU" }, { value: "memory", label: "Memory" }]; onPicked: function (v) { page.mtr = v } }
                                       Txt { text: "above"; color: Theme.text2; anchors.verticalCenter: parent.verticalCenter }
                                       Num { width: 96; value: page.val; from: 1; to: 100; onChanged: function (v) { page.val = v } }
                                       Txt { text: "%"; color: Theme.text2; anchors.verticalCenter: parent.verticalCenter } }
                            FieldRow { visible: page.kind === "Threshold"; label: "For at least"
                                       Num { width: 96; value: page.mins; from: 0; to: 120; onChanged: function (v) { page.mins = v } }
                                       Txt { text: "minutes"; color: Theme.text2; anchors.verticalCenter: parent.verticalCenter }
                                       Txt { text: "so a short spike does not fire it"; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } }
                            FieldRow { visible: page.kind === "Schedule"; label: "Days"
                                       Repeater { model: Auto.dayNames
                                                  Check { required property var modelData; required property int index; text: modelData; controlled: true; checked: page.days.indexOf(index) >= 0
                                                          onToggled: function (on) { var d = page.days.filter(function (x) { return x !== index }); if (on) d.push(index); page.days = d.sort() } } } }
                            FieldRow { visible: page.kind === "Schedule"; label: "At"
                                       Select { width: 120; value: page.at; options: { var o = []; for (var i = 0; i < 48; i++) o.push(Time.pad(Math.floor(i / 2)) + ":" + (i % 2 ? "30" : "00")); return o }
                                                onPicked: function (v) { page.at = v } } }
                        }
                        // step 2: on
                        Column {
                            visible: page.step === 1
                            width: parent.width
                            spacing: 14
                            Head { t: "Which machines should it watch?"; d: "The rule runs on each of these machines separately." }
                            Row {
                                width: parent.width
                                spacing: 12
                                Repeater {
                                    model: [["all", "global", "Every machine", "All " + Fleet.machines.length + " machines" + (Nav.boss ? "" : " in this department") + ", and any registered later."],
                                            ["dept", "apartment", "A department", "Every machine in one department."],
                                            ["pick", "desktop", "Machines I pick", "A fixed list. New machines are not added."]]
                                    Choice { required property var modelData; visible: Nav.boss || modelData[0] !== "dept"; width: (parent.width - 24) / (Nav.boss ? 3 : 2)
                                             on: page.scope === modelData[0]; icon: modelData[1]; title: modelData[2]; desc: modelData[3]; onClicked: page.scope = modelData[0] }
                                }
                            }
                            Item { width: 1; height: 12 }
                            FieldRow { visible: page.scope === "dept"; label: "Department"
                                       Select { width: 260; value: page.dept || null; options: Fleet.depts.map(function (d) { return { value: d.id, label: d.name + " · " + d.machines.length + " machines" } })
                                                onPicked: function (v) { page.dept = v } } }
                            FieldRow { visible: page.scope === "pick"; label: "Machines"
                                       Select { width: 520; multiple: true; search: true; placeholder: "Pick machines"; values: page.hosts
                                                options: Fleet.machines.map(function (m) { return { value: m.pc_id, label: m.host + " · " + (m.user || "no user") } })
                                                onPicked: function (v) { page.hosts = v } } }
                            Txt { text: Theme.many(page.targets.length, "machine"); color: Theme.text3 }
                            Flow {
                                width: parent.width
                                spacing: 6
                                Repeater { model: page.targets.slice(0, 40)
                                           Tag { required property var modelData; mono: true; text: modelData.host + (modelData.user ? "  " + modelData.user : ""); c: modelData.online ? Theme.text3 : Theme.text4 } }
                                More { n: page.targets.length - 40 }
                            }
                            Rectangle { visible: page.targets.some(function (m) { return !m.online }); width: parent.width; height: 36; radius: 5; color: Theme.surface2
                                        Txt { x: 12; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 12; color: Theme.text2
                                              text: page.targets.filter(function (m) { return !m.online }).map(function (m) { return m.host }).join(", ") + " offline. The rule applies to it when it comes back." } }
                        }
                        // step 3: do
                        Column {
                            visible: page.step === 2
                            width: parent.width
                            spacing: 12
                            Head { t: "What should it do?"; d: "Actions run in this order, each on its own with its own time limit. One failing never stops the others." }
                            Repeater {
                                model: page.acts
                                Rectangle {
                                    id: card
                                    required property var modelData
                                    required property int index
                                    readonly property var a: page.lib.filter(function (x) { return x.id === modelData })[0] || null
                                    width: parent.width
                                    height: ac.height + 28
                                    radius: Theme.radius
                                    color: Theme.surface
                                    border.width: 1
                                    border.color: Theme.border
                                    Column {
                                        id: ac
                                        x: 14; y: 14
                                        width: parent.width - 28
                                        spacing: 8
                                        Row {
                                            width: parent.width
                                            spacing: 10
                                            Rectangle { width: 22; height: 22; radius: 4; color: Theme.surface3; Txt { anchors.centerIn: parent; text: String(index + 1); mono: true; font.pixelSize: 12; elide: Text.ElideNone } }
                                            Select { width: 280; search: true; value: modelData
                                                     options: ["control", "monitoring", "custom"].reduce(function (o, c) {
                                                         var xs = page.lib.filter(function (x) { return x.cat === c }); if (!xs.length) return o
                                                         return o.concat([{ group: c.charAt(0).toUpperCase() + c.slice(1) }]).concat(xs.map(function (x) { return { value: x.id, label: x.name } })) }, [])
                                                     onPicked: function (v) { var a = page.acts.slice(); a[index] = v; page.acts = a } }
                                            Item { width: parent.width - 280 - 22 - 20 - 200; height: 1 }
                                            Txt { text: card.a ? "Time limit " + card.a.timeout_seconds + "s" : ""; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter; width: 110 }
                                            Btn { small: true; kind: "text"; iconName: "arrowu"; enabled: index > 0; onClicked: { var a = page.acts.slice(); var t = a[index - 1]; a[index - 1] = a[index]; a[index] = t; page.acts = a } }
                                            Btn { small: true; kind: "text"; iconName: "close"; onClicked: { var a = page.acts.slice(); a.splice(index, 1); page.acts = a } }
                                        }
                                        Row {
                                            x: 32
                                            spacing: 8
                                            Tag { text: card.a ? card.a.cat.charAt(0).toUpperCase() + card.a.cat.slice(1) : ""
                                                  c: card.a && card.a.cat === "custom" ? Theme.ser3 : card.a && card.a.cat === "control" ? Theme.ser4 : Theme.ser1 }
                                            Txt { text: card.a ? (card.a.description || "") : ""; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                                        }
                                    }
                                }
                            }
                            Row {
                                spacing: 16
                                Btn { iconName: "plus"; text: "Add action"; enabled: page.lib.length > 0; onClicked: page.acts = page.acts.concat([page.lib[0].id]) }
                                Txt { text: "From the action library · need something new? Write a custom action on Actions"; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                            }
                            Rectangle { visible: page.acts.some(function (id) { var a = page.lib.filter(function (x) { return x.id === id })[0]; return a && a.cat === "custom" })
                                        width: parent.width; height: 40; radius: 5; color: Theme.alpha(Theme.med, 0.10)
                                        Txt { x: 12; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 24; color: Theme.med; font.pixelSize: 12
                                              text: "Custom scripts run without a sandbox. The script is checked before it is sent and again on arrival, and every run is recorded." } }
                        }
                        // step 4: review
                        Column {
                            visible: page.step === 3
                            width: parent.width
                            spacing: 14
                            Head { t: page.editId ? "Check your changes" : "Name it and check it"; d: page.editId ? "Changes apply from the next firing. The record keeps the old version." : "Saved rules are switched on straight away." }
                            FieldRow { label: "Name"
                                       Field { width: 440; text: page.name; placeholderText: Auto.names[page.type] || "Name the rule"; onTextEdited: page.name = text } }
                            Rectangle {
                                width: parent.width
                                height: sent.height + 32
                                radius: 6
                                color: Theme.surface2
                                Txt { id: sent; x: 18; y: 16; width: parent.width - 36; wrapMode: Text.WordWrap; elide: Text.ElideNone; font.pixelSize: 16; textFormat: Text.RichText
                                      text: "<span style='color:" + Theme.text3 + "'>When</span> " + page.whenTxt + " <span style='color:" + Theme.text3 + "'>on</span> " + page.whereTxt
                                            + "<span style='color:" + Theme.text3 + "'>, do</span> " + (page.doTxt || "<span style='color:" + Theme.med + "'>nothing yet</span>") + "." }
                            }
                            Row {
                                width: parent.width
                                spacing: 28
                                Column {
                                    width: (parent.width - 28) / 2
                                    spacing: 6
                                    Txt { text: page.kind === "Schedule" ? "When it will run" : "If it had been on last week"; font.weight: Font.DemiBold }
                                    Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                                          text: page.kind === "Schedule" ? "The next three runs" : "Replaying a rule against last week needs the readings the Engine keeps, which the console cannot read yet." }
                                    Repeater {
                                        model: {
                                            if (page.kind !== "Schedule") return []
                                            var out = [], hh = +page.at.slice(0, 2), mm = +page.at.slice(3)
                                            for (var d = 0; d < 14 && out.length < 3; d++) {
                                                var t = new Date(Time.startOfDay(Time.now) + d * 86400000); t.setHours(hh, mm, 0, 0)
                                                if (t.getTime() > Time.now && page.days.indexOf((t.getDay() + 6) % 7) >= 0) out.push(t)
                                            }
                                            return out
                                        }
                                        Txt { required property var modelData; text: Time.atDay(modelData); mono: true }
                                    }
                                }
                                Grid {
                                    width: (parent.width - 28) / 2
                                    columns: 2
                                    rowSpacing: 12
                                    columnSpacing: 20
                                    Repeater {
                                        model: [["Machines", String(page.targets.length)], ["Actions per firing", String(page.acts.length * (page.kind === "Schedule" ? page.targets.length : 1))],
                                                ["Longest time limit", page.acts.length ? Math.max.apply(null, page.acts.map(function (id) { var a = page.lib.filter(function (x) { return x.id === id })[0]; return a ? a.timeout_seconds : 0 })) + "s" : "—"]]
                                        Column { required property var modelData; width: 150
                                                 Txt { text: modelData[0]; color: Theme.text3; font.pixelSize: 12 }
                                                 Txt { text: modelData[1]; font.weight: Font.Medium } }
                                    }
                                }
                            }
                            Repeater { model: page.problems.filter(function (p) { return p !== "" })
                                       Rectangle { required property var modelData; width: parent.width; height: 36; radius: 5; color: Theme.alpha(Theme.med, 0.10)
                                                   Txt { x: 12; anchors.verticalCenter: parent.verticalCenter; text: modelData; color: Theme.med; font.pixelSize: 12 } } }
                        }
                    }
                    Rectangle { width: parent.width; height: 1; color: Theme.border }
                    Item {
                        width: parent.width; height: 58
                        Txt { x: 28; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 360; color: Theme.text3; font.pixelSize: 12
                              text: page.step < 3 ? "When " + page.whenTxt + " on " + page.whereTxt + (page.doTxt ? ", do " + page.doTxt : "") : "" }
                        Row {
                            anchors.right: parent.right
                            anchors.rightMargin: 28
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 8
                            Btn { visible: page.step > 0; text: "Back"; onClicked: page.step-- }
                            Btn { visible: page.step < 3; kind: "primary"; enabled: page.problems[page.step] === ""; text: "Next: " + ["When", "On", "Do", "Review"][page.step + 1]; onClicked: page.step++ }
                            Btn { visible: page.step === 3; enabled: page.ok; text: "Test on one machine"; onClicked: page.testOnce() }
                            Btn { visible: page.step === 3; kind: "primary"; enabled: page.ok; text: page.editId ? "Save changes" : "Save rule"; onClicked: page.save() }
                        }
                    }
                }
            }
        }
    }
}
