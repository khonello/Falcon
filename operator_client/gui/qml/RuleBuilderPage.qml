import QtQuick
import "."

// A RULE OF THE ORGANISATION (the Super User's), new, from a pattern, or edited: the pattern drawn on top and
// following what is set below; what kind of rule, when, then / within or the count and its line, who it
// applies to, what happens when it is broken, its name; on the right what it would have done to the record.
// Saved to the Engine's rule store (rules.create / rules.update); a built-in rule is shown, not changed.
Page {
    id: page
    objectName: "ruleBuilder"
    bare: true

    readonly property string sub: Nav.sub ? String(Nav.sub) : "new"
    readonly property var editing: { if (sub.indexOf("edit-") !== 0) return null; var c = sub.slice(5); for (var i = 0; i < Rules.all.length; i++) if (Rules.all[i].id === c) return Rules.all[i]; return null }
    readonly property var tpl: { if (sub.indexOf("from-") !== 0) return null; var k = sub.slice(5); for (var i = 0; i < Rules.templates.length; i++) if (Rules.templates[i].id === k) return Rules.templates[i]; return null }
    readonly property bool ro: editing !== null && editing.locked
    readonly property bool found: sub === "new" || editing !== null || tpl !== null
    property var s: Rules.blank()
    property bool filled: false
    property var actions: []              // the action library, for "run an action"
    property var tried: null              // rules.try for the saved rule under the line set here

    function fill() {
        if (filled) return
        if (editing) { s = Rules.toPattern(editing); filled = true }
        else if (tpl) { s = Object.assign(Rules.blank(), tpl.state, { name: tpl.name, resp: Object.assign(Rules.blank().resp, tpl.state.resp || {}) }); filled = true }
        else if (sub === "new") { s = Rules.blank(); filled = true }
    }
    onEditingChanged: fill()
    onTplChanged: fill()
    Component.onCompleted: {
        fill()
        if (!Rules.list.length) Rules.load()
        falcon.call("control.action_list", {}, function (ok, r) {
            var a = ok ? (r.actions || {}) : {}, out = []
            ;["control", "monitoring", "custom"].forEach(function (k) { (a[k] || []).forEach(function (x) { out.push({ value: x.id, label: x.name }) }) })
            page.actions = out
        })
    }
    function set(k, v) { var x = Object.assign({}, s); x[k] = v; s = x }
    function setResp(k, v) { var r = Object.assign({}, s.resp); r[k] = v; set("resp", r) }
    readonly property int limMin: s.within ? Math.round(s.within.n * Rules.units[s.within.unit]) : 0

    // what the changed line would have done to the saved rule's record (the Engine replays its last 30 days)
    function retry() {
        tried = null
        if (!editing || editing.locked || editing.shape === "never" || editing.shape !== s.shape) return
        var pl = { rule_id: editing.rid }
        if (s.shape === "follow") pl.within = limMin; else pl.limit = { n: s.limit.n }
        falcon.call("rules.try", pl, function (ok, r) { page.tried = ok ? r : null })
    }
    onSChanged: againTry.restart()
    Timer { id: againTry; interval: 300; onTriggered: page.retry() }

    readonly property string missing: ro ? "Built-in rules cannot be changed." : !s.name.trim() ? "Give it a name."
        : s.shape === "follow" && !(s.within.n >= 1) ? "Say how long it has." : s.resp.action && !s.resp.actionId ? "Pick the action to run."
        : s.depts !== "all" && !s.depts.length ? "Pick at least one department." : ""

    Confirm { id: confirm; page: page }
    function leave() { Nav.go("rules", editing ? editing.id : null) }
    function save() {
        var spec = Rules.toSpec(s)
        var done = function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not saved"); return }
            Msg.ok(editing ? "Rule changed. Deviations already recorded keep the rule as it was" : "Rule saved and on")
            Rules.load(); Nav.go("rules", r.rule ? r.rule.code : editing ? editing.id : null)
        }
        if (editing) falcon.call("rules.update", Object.assign({ rule_id: editing.rid }, spec), done)
        else falcon.call("rules.create", Object.assign({ shape: s.shape }, spec), done)
    }

    Panel {
        visible: !page.found
        width: parent.width
        title: "Rule not found"
        Txt { text: "There is no rule " + page.sub + "."; color: Theme.text3 }
        Link { text: "Back to the rules"; onClicked: Nav.go("rules") }
    }

    Rectangle {
        visible: page.found && page.ro
        width: parent.width; height: 48; radius: 6; color: Theme.alpha(Theme.med, 0.10)
        Row { x: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 10
              Icon { name: "lock"; size: 16; color: Theme.text2; anchors.verticalCenter: parent.verticalCenter }
              Txt { textFormat: Text.StyledText; text: "<b>Built into Falcon.</b> <font color='" + Theme.text2 + "'>You can see how it works, not change it or switch it off.</font>"; elide: Text.ElideNone } }
    }

    Panel {
        visible: page.found
        width: parent.width
        title: "The pattern"
        sub: "left to right · the dashed branch is where a deviation is noted · it follows what you set below"
        PatternGraph { width: parent.width; s: Object.assign({}, page.s, { resp: Object.assign({}, page.s.resp, { actionName: (page.actions.filter(function (a) { return a.value === page.s.resp.actionId })[0] || {}).label }) }) }
    }

    component FieldRow: Row {
        property string label: ""
        default property alias inner: fr.data
        spacing: 0
        Txt { width: 130; text: parent.label; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
        Row { id: fr; spacing: 10; anchors.verticalCenter: parent.verticalCenter }
    }
    component Head: Txt { font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66; color: Theme.text3 }

    EditorShell {
        visible: page.found
        width: parent.width
        problem: page.missing
        saveLabel: page.editing ? "Save changes" : "Save rule"
        onCancel: page.leave()
        onSave: page.save()
        leftPane: Rectangle {
            width: parent.width
            height: form.height + 28
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.border
            Column {
                id: form
                x: 14; y: 14
                width: parent.width - 28
                spacing: 18
                Column {
                    width: parent.width; spacing: 10
                    Head { text: "WHAT KIND OF RULE" }
                    Row {
                        width: parent.width; spacing: 10
                        Repeater {
                            model: ["never", "follow", "limit"]
                            Choice { required property var modelData; width: (parent.width - 20) / 3; on: page.s.shape === modelData; icon: Rules.shapes[modelData].icon
                                     title: Rules.shapes[modelData].w; desc: Rules.shapes[modelData].d; disabled: page.ro || page.editing !== null && page.s.shape !== modelData
                                     onClicked: page.set("shape", modelData) }
                        }
                    }
                    Txt { visible: page.editing !== null && !page.ro; text: "What kind of rule it is cannot change once it is saved."; color: Theme.text3; font.pixelSize: 12 }
                }
                Column {
                    width: parent.width; spacing: 12
                    FieldRow { visible: page.s.shape !== "limit"; label: "When"
                               Select { width: 420; enabled: !page.ro; value: page.s.trigger
                                        options: (page.s.shape === "never" ? ["file", "second", "cert", "outhours"] : ["help", "report", "version", "task", "seat"]).map(function (k) { return { value: k, label: Rules.trig[k] } })
                                        onPicked: function (v) { page.set("trigger", v); if (page.s.shape === "follow") page.set("expect", ({ help: "answer", report: "addressed", version: "updated", task: "seen", seat: "appoint" })[v]) } } }
                    FieldRow { visible: page.s.shape === "follow"; label: "Then"
                               Select { width: 420; enabled: !page.ro; value: page.s.expect
                                        options: [({ help: "answer", report: "addressed", version: "updated", task: "seen", seat: "appoint" })[page.s.trigger] || "answer"].map(function (k) { return { value: k, label: Rules.exp[k] } })
                                        onPicked: function (v) { page.set("expect", v) } } }
                    FieldRow { visible: page.s.shape === "follow"; label: "Within"
                               Num { width: 90; enabled: !page.ro; from: 1; to: 999; value: page.s.within.n; onChanged: function (v) { page.set("within", { n: v, unit: page.s.within.unit }) } }
                               Select { width: 110; enabled: !page.ro; value: page.s.within.unit; options: ["minutes", "hours", "days"]; onPicked: function (v) { page.set("within", { n: page.s.within.n, unit: v }) } } }
                    FieldRow { visible: page.s.shape === "limit"; label: "Count"
                               Select { width: 420; enabled: !page.ro; value: page.s.reading; options: Rules.readings; onPicked: function (v) { page.set("reading", v) } } }
                    FieldRow { visible: page.s.shape === "limit"; label: "No more than"
                               Num { width: 90; enabled: !page.ro; from: 0; to: 999; value: page.s.limit.n; onChanged: function (v) { page.set("limit", { n: v, per: page.s.limit.per }) } }
                               Txt { text: "per"; color: Theme.text2; anchors.verticalCenter: parent.verticalCenter }
                               Select { width: 110; enabled: !page.ro; value: page.s.limit.per; options: ["hour", "day", "week"]; onPicked: function (v) { page.set("limit", { n: page.s.limit.n, per: v }) } } }
                    FieldRow { label: "Applies to"
                               Select { width: 300; enabled: !page.ro; value: page.s.who; options: Object.keys(Rules.whol).map(function (k) { return { value: k, label: Rules.whol[k] } }); onPicked: function (v) { page.set("who", v) } }
                               Segmented { enabled: !page.ro; value: page.s.depts === "all" ? "all" : "some"; options: [{ value: "all", label: "Every department" }, { value: "some", label: "Some departments" }]
                                           onPicked: function (v) { page.set("depts", v === "all" ? "all" : []) } } }
                    FieldRow { visible: page.s.depts !== "all"; label: "Departments"
                               Select { width: 520; enabled: !page.ro; multiple: true; search: true; placeholder: "Which departments?"; values: page.s.depts === "all" ? [] : page.s.depts
                                        options: Fleet.depts.map(function (d) { return { value: d.id, label: d.name } }); onPicked: function (v) { page.set("depts", v) } } }
                }
                Column {
                    width: parent.width; spacing: 8
                    Head { text: "WHEN IT IS BROKEN" }
                    Check { text: "Record it on the deviations list, with who, when and what was around it"; checked: true; enabled: false }
                    Check { text: "Tell you"; controlled: true; checked: !!page.s.resp.report; enabled: !page.ro; onToggled: function (on) { page.setResp("report", on) } }
                    Check { text: "Tell the department's Admin"; controlled: true; checked: !!page.s.resp.admin; enabled: !page.ro; onToggled: function (on) { page.setResp("admin", on) } }
                    Row { spacing: 10
                          Check { text: "Run an action"; controlled: true; checked: !!page.s.resp.action; enabled: !page.ro; onToggled: function (on) { page.setResp("action", on) }; anchors.verticalCenter: parent.verticalCenter }
                          Select { visible: !!page.s.resp.action; width: 260; search: true; enabled: !page.ro; value: page.s.resp.actionId || null; placeholder: "Action to run"
                                   options: page.actions; onPicked: function (v) { page.setResp("actionId", v) } } }
                    Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                          text: "A deviation is a record. Falcon does not punish anyone, and an action runs only if you chose it here." }
                }
                FieldRow { visible: !page.ro; label: "Name"
                           Field { width: 440; text: page.s.name; placeholderText: "Say what the rule keeps"; onTextEdited: page.set("name", text) } }
            }
        }
        rightPane: Panel {
            width: parent.width
            title: "If it had been on"
            Column {
                width: parent.width
                spacing: 8
                readonly property bool replay: page.tried !== null && page.tried.would_remain !== undefined
                Row { spacing: 8
                      Txt { text: parent.parent.replay ? Theme.fmt(page.tried.would_remain) : page.editing ? Theme.fmt(page.editing.n || 0) : "—"; font.pixelSize: 26; font.weight: Font.DemiBold; elide: Text.ElideNone }
                      Txt { anchors.baseline: parent.children[0].baseline; color: Theme.text2; elide: Text.ElideNone
                            text: parent.parent.replay ? "deviation" + (page.tried.would_remain === 1 ? "" : "s") + " in the last 30 days" : page.editing ? "deviation" + ((page.editing.n || 0) === 1 ? "" : "s") + " this week" : "no record yet" } }
                Rectangle {
                    visible: parent.replay && page.tried.would_clear > 0
                    width: parent.width; height: tc.height + 20; radius: 6
                    color: Theme.alpha(Theme.ser1, 0.09); border.width: 1; border.color: Theme.alpha(Theme.ser1, 0.35)
                    Txt { id: tc; x: 12; y: 10; width: parent.width - 24; wrapMode: Text.WordWrap; elide: Text.ElideNone; font.pixelSize: 12
                          text: page.tried ? Theme.fmt(page.tried.would_clear) + " fewer than the saved rule: it would have cleared " + page.tried.would_clear + " of the " + page.tried.deviations + "." : "" }
                }
                Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                      text: (page.editing ? (page.editing.shape === "never" ? "A rule that must never be broken has no line to move: every time is a deviation." : "Replayed against what the record held for this rule.")
                                          : "A new rule is measured from when it is switched on; there is no record of it to replay yet.")
                            + " Deviations already recorded keep the rule as it was." }
            }
        }
    }
}
