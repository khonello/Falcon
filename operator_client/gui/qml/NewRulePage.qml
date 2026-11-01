import QtQuick
import "."

// NEW RULE (and Edit), on one page, the way New flow is (docs/design/concepts-admin.html): a panel of three steps in the order the rule reads (When, On, Do),
// each step a column with its controls on top and a live look at what it is setting at the foot; then the name and the checks; Save at the bottom. A step shows
// complete (a filled mark) or what is missing (an amber ring and the words), so nothing reads as done before it is. A new rule starts blank: nothing chosen, no
// machine, no action. The Do column shows an action's own time limit (the library keeps it; this page does not change it).
Page {
    id: page
    objectName: "newRule"
    bare: true

    readonly property int editId: Nav.sub && String(Nav.sub).indexOf("edit-") === 0 ? Number(String(Nav.sub).slice(5)) : 0
    property string kind: ""                // "" until the first choice: Event | Threshold | Schedule
    property string ev: ""
    property string mtr: "cpu"
    property int val: 90
    property int mins: 5
    property var days: [0, 1, 2, 3, 4]
    property string at: "09:00"
    property string scope: ""               // "" until chosen: all | dept | pick
    property int dept: 0
    property var hosts: []
    property var acts: []                  // action ids, in order
    property string name: ""
    property bool idle: false
    property var lib: []                   // the action library, flattened
    property var original: null
    property var existing: []              // the rules there are, to start from a copy
    property string base: ""
    property var firings: []               // what an existing rule did in the last week, for the When look

    readonly property var eventChoices: ["usb.inserted", "resource.violation", "user.login", "user.logout", "system.idle", "program.launched", "file.modified", "network.disconnected", "flow.failed"]
    Component.onCompleted: {
        falcon.call("control.action_list", {}, function (ok, r) {
            var a = ok ? (r.actions || {}) : {}, out = []
            ;["control", "monitoring", "custom"].forEach(function (k) { (a[k] || []).forEach(function (x) { out.push(Object.assign({ cat: k }, x)) }) })
            page.lib = out
        })
        falcon.call("control.event_list", {}, function (ok, r) {
            page.existing = ok ? (r.events || []) : []
            if (!page.editId) return
            var e = page.existing.filter(function (x) { return x.id === page.editId })[0]
            if (!e) return
            page.load(e)
            falcon.call("control.event_history", { event_id: e.id }, function (ok2, r2) { page.firings = ok2 ? (r2.firings || []) : [] })
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
        base = v ? String(v) : ""
        if (!v) { kind = ""; ev = ""; mtr = "cpu"; val = 90; mins = 5; days = [0, 1, 2, 3, 4]; at = "09:00"; scope = ""; hosts = []; acts = []; name = ""; idle = false; return }
        var e = existing.filter(function (x) { return String(x.id) === String(v) })[0]
        if (e) { load(e); name = "Copy of " + Auto.nameOf(e) }
    }
    readonly property string type: kind === "Event" ? ev : kind === "Threshold" ? (mtr === "cpu" ? "threshold.cpu" : "threshold.memory") : kind === "Schedule" ? "time.recurring" : ""
    readonly property var match: kind === "Threshold" ? { percent: val, duration_s: mins * 60 } : kind === "Schedule" ? { at: at, days: days } : {}
    readonly property var targets: scope === "all" ? Fleet.machines : scope === "dept" ? Fleet.inDept(dept) : scope === "pick" ? Fleet.machines.filter(function (m) { return page.hosts.indexOf(m.pc_id) >= 0 }) : []
    readonly property string whenTxt: type === "" ? "…" : Auto.whenOf({ condition_spec: { type: type, match: match } })
    readonly property string whereTxt: scope === "" ? "…" : scope === "all" ? "any machine" : scope === "dept" ? "a " + Fleet.deptName(dept) + " machine" : targets.map(function (m) { return m.host }).join(", ") || "no machines yet"
    function actOf(id) { return lib.filter(function (x) { return x.id === id })[0] || null }
    function actName(id) { var a = actOf(id); return a ? a.name : "an action" }
    readonly property string doTxt: acts.length ? acts.map(page.actName).join(", then ") : ""
    readonly property var problems: [
        kind === "" ? "Pick what should start it." : kind === "Event" && ev === "" ? "Pick what happens." : kind === "Schedule" && !days.length ? "Pick at least one day." : "",
        targets.length ? "" : scope === "" ? "Pick which machines it watches." : "Pick at least one machine.",
        acts.length ? "" : "Add at least one action."]
    readonly property bool ok: problems.every(function (p) { return p === "" })
    readonly property var sums: [
        kind === "Event" ? (Auto.when[ev] || ev) : kind === "Threshold" ? (mtr === "cpu" ? "CPU" : "Memory") + " above " + val + "%, for " + Theme.many(mins, "minute")
                                                 : "At " + at + ", " + (days.length === 7 ? "every day" : days.length === 5 && days.indexOf(5) < 0 && days.indexOf(6) < 0 ? "on weekdays" : days.map(function (d) { return Auto.dayNames[d] }).join(", ")),
        scope === "all" ? "Every machine · " + targets.length : Theme.many(targets.length, "machine") + " picked",
        doTxt]

    Confirm { id: confirm; page: page }
    function cancel() {
        var clean = !editId && kind === "" && scope === "" && !acts.length && name === ""
        if (clean) { Nav.go("automation"); return }
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
    // the next three runs of a schedule, as the Engine's clock will read it
    readonly property var nextRuns: {
        if (kind !== "Schedule") return []
        var out = [], hh = +at.slice(0, 2), mm = +at.slice(3)
        for (var d = 0; d < 14 && out.length < 3; d++) {
            var t = new Date(Time.startOfDay(Time.now) + d * 86400000); t.setHours(hh, mm, 0, 0)
            if (t.getTime() > Time.now && days.indexOf((t.getDay() + 6) % 7) >= 0) out.push(t)
        }
        return out
    }
    // how many times an existing rule fired on each of the last seven days
    readonly property var week: {
        var out = [0, 0, 0, 0, 0, 0, 0], today = Time.startOfDay(Time.now)
        firings.forEach(function (f) { var d = Math.round((today - Time.startOfDay(Time.ms(f.at))) / 86400000); if (d >= 0 && d < 7) out[6 - d]++ })
        return out
    }
    readonly property int weekTotal: week.reduce(function (a, b) { return a + b }, 0)

    // the small-caps caption of a look, with a word at the right
    component Cap: Item {
        property string t: ""
        property string aside: ""
        width: parent ? parent.width : 0
        height: 16
        Txt { text: parent.t; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66; elide: Text.ElideNone }
        Txt { anchors.right: parent.right; text: parent.aside; color: Theme.text3; font.pixelSize: Theme.fSmall; elide: Text.ElideNone }
    }
    function dot(s) { return s === "healthy" ? Theme.ok : s === "offline" ? Theme.text4 : Fleet.sevColor(s) }
    // a small labelled control: the words over the control
    component Lab: Column {
        property string t: ""
        spacing: 4
        Txt { text: parent.t; color: Theme.text3; font.pixelSize: Theme.fSmall; elide: Text.ElideNone }
    }

    Column {
        id: col
        width: page.w
        spacing: 14

        // ================= the rule: three steps, three columns =================
        Panel {
            width: parent.width
            flush: true
            title: page.editId ? "Editing " + (page.original ? Auto.nameOf(page.original) : "the rule") : "The rule"
            sub: page.editId ? "it keeps running as it was until you save" : "what starts it, where it runs and what it does"
            extra: Select {
                visible: !page.editId && page.existing.length > 0
                width: 230
                small: true
                placeholder: "Start from a copy of a rule"
                value: page.base === "" ? null : page.base
                options: page.existing.slice(0, 12).map(function (e) { return { value: String(e.id), label: "Copy of " + Auto.nameOf(e) } })
                onPicked: function (v) { page.startFrom(v) }
            }

            Column {
                width: parent.width

                // --- the steps, in the order the rule reads ---
                Item {
                    id: steps
                    width: parent.width
                    height: 64
                    Rectangle { anchors.fill: parent; color: Theme.surface2 }
                    Row { Repeater {
                        model: ["When", "On", "Do"]
                        delegate: Item {
                            required property string modelData
                            required property int index
                            readonly property bool bad: page.problems[index] !== ""
                            width: steps.width / 3
                            height: steps.height
                            Rectangle { visible: index > 0; width: 1; height: parent.height; color: Theme.border }
                            Rectangle {
                                x: 18; anchors.verticalCenter: parent.verticalCenter
                                width: 32; height: 32; radius: 16
                                color: bad ? "transparent" : Theme.accent
                                border.width: 2
                                border.color: bad ? Theme.med : Theme.accent
                                Icon { visible: !bad; anchors.centerIn: parent; name: "check"; size: 15; color: Theme.inverse; weight: 2.4 }
                                Txt { visible: bad; anchors.centerIn: parent; text: String(index + 1); font.weight: Font.DemiBold; color: Theme.med; elide: Text.ElideNone }
                            }
                            Column {
                                x: 62; anchors.verticalCenter: parent.verticalCenter
                                width: parent.width - 62 - 40
                                Txt { text: modelData; font.weight: Font.DemiBold; font.pixelSize: Theme.fLead; width: parent.width }
                                Txt { text: bad ? page.problems[index] : page.sums[index]; color: bad ? Theme.med : Theme.text3; width: parent.width; font.pixelSize: Theme.fSmall }
                            }
                            Icon { visible: index < 2; anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter; name: "right"; size: 14; color: Theme.text4 }
                        }
                    } }
                }
                Rectangle { width: parent.width; height: 1; color: Theme.border }

                // --- the three columns, each its controls over its look ---
                Row {
                    id: cols
                    width: parent.width
                    readonly property real lookH: 240
                    readonly property real colH: Math.max(Theme.ruleColumnH, Math.max(whenTop.height, onTop.height, doTop.height) + lookH + 56)

                    // ---------- When ----------
                    Item {
                        width: cols.width / 3; height: cols.colH
                        Column {
                            id: whenTop
                            x: 18; y: 16
                            width: parent.width - 36
                            spacing: 10
                            Item {
                                width: parent.width; height: tabsWhen.implicitHeight
                                Tabs {
                                    id: tabsWhen
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    width: Math.min(implicitWidth, parent.width)
                                    tabs: page.editId ? [{ key: page.kind, label: page.kind === "Event" ? "An event" : page.kind === "Threshold" ? "A reading" : "A schedule" }]
                                                      : [{ key: "Event", label: "An event" }, { key: "Threshold", label: "A reading" }, { key: "Schedule", label: "A schedule" }]
                                    current: page.kind
                                    onPicked: function (k) { page.kind = k }
                                }
                            }
                            Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: Theme.fSmall
                                  text: page.kind === "Event" ? "A device is plugged in, a file appears, someone signs in. Reported the moment it happens."
                                      : page.kind === "Threshold" ? "CPU or memory stays above a level for a while. Checked every 30 seconds."
                                      : page.kind === "Schedule" ? "At a time on chosen days, by the Engine's clock." : "Pick what should start this rule." }
                            Lab { visible: page.kind === "Event"; t: "Event"; width: parent.width
                                  Select { width: Math.min(330, parent.width); enabled: !page.editId; placeholder: "Pick an event"; value: page.ev === "" ? null : page.ev
                                           options: page.eventChoices.map(function (t) { var w = Auto.when[t]; return { value: t, label: w.charAt(0).toUpperCase() + w.slice(1) } })
                                           onPicked: function (v) { page.ev = v } } }
                            Lab { visible: page.kind === "Threshold"; t: "Reading"; width: parent.width
                                  Row {
                                      spacing: 8
                                      Select { width: 96; enabled: !page.editId; value: page.mtr; options: [{ value: "cpu", label: "CPU" }, { value: "memory", label: "Memory" },
                                                                                                          { value: "disk", label: "Disk · not watched by the Engine yet", disabled: true },
                                                                                                          { value: "network", label: "Network · not watched by the Engine yet", disabled: true }]; onPicked: function (v) { page.mtr = v } }
                                      Txt { text: "above"; color: Theme.text2; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
                                      Num { width: 66; value: page.val; from: 1; to: 100; onChanged: function (v) { page.val = v } }
                                      Txt { text: "%"; color: Theme.text2; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
                                      Txt { text: "for"; color: Theme.text2; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
                                      Num { width: 58; value: page.mins; from: 0; to: 120; onChanged: function (v) { page.mins = v } }
                                      Txt { text: "min"; color: Theme.text2; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
                                  } }
                            Txt { visible: page.kind === "Threshold"; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: Theme.fSmall
                                  text: "A short spike does not fire it: the reading has to stay above the line for that long." }
                            Lab { visible: page.kind === "Schedule"; t: "Days"; width: parent.width
                                  Flow { width: parent.width; spacing: 10
                                         Repeater { model: Auto.dayNames
                                                    Check { required property var modelData; required property int index; text: modelData; controlled: true; checked: page.days.indexOf(index) >= 0
                                                            onToggled: function (on) { var d = page.days.filter(function (x) { return x !== index }); if (on) d.push(index); page.days = d.sort() } } } } }
                            Lab { visible: page.kind === "Schedule"; t: "At"; width: parent.width
                                  Select { width: 120; value: page.at; options: { var o = []; for (var i = 0; i < 48; i++) o.push(Time.pad(Math.floor(i / 2)) + ":" + (i % 2 ? "30" : "00")); return o }
                                           onPicked: function (v) { page.at = v } } }
                        }
                        // the look: a saved rule's last week, a schedule's next runs, or what is missing
                        Item {
                            x: 18; y: parent.height - cols.lookH - 20
                            width: parent.width - 36; height: cols.lookH
                            Rectangle { width: parent.width; height: 1; color: Theme.split }
                            Column {
                                y: 14; width: parent.width; spacing: 8
                                Cap { t: page.kind === "Schedule" ? "NEXT RUNS" : "LAST 7 DAYS"; aside: page.kind === "Schedule" ? "by the Engine's clock" : page.editId ? "what it did" : "" }
                                Txt { visible: page.kind === ""; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; text: "Pick what should start this rule to see what it would do." }
                                Txt { visible: page.kind !== "" && page.kind !== "Schedule" && !page.editId; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3
                                      text: "A new rule has no history yet. Save it, and its firings appear here as they happen." }
                                Repeater {
                                    model: page.kind === "Schedule" ? page.nextRuns : []
                                    Row { required property var modelData; width: parent.width
                                          Txt { text: Time.atDay(modelData); mono: true; elide: Text.ElideNone } }
                                }
                                Txt { visible: page.kind === "Schedule" && page.nextRuns.length === 0; color: Theme.med; text: "Pick at least one day." }
                                Row {
                                    visible: page.kind !== "" && page.kind !== "Schedule" && page.editId > 0
                                    spacing: 6
                                    Txt { text: String(page.weekTotal); font.pixelSize: Theme.fDay; font.weight: Font.DemiBold; elide: Text.ElideNone; anchors.baseline: wk.baseline }
                                    Txt { id: wk; text: page.weekTotal === 1 ? "time it fired" : "times it fired"; color: Theme.text2; elide: Text.ElideNone }
                                }
                                Row {
                                    visible: page.kind !== "" && page.kind !== "Schedule" && page.editId > 0
                                    spacing: 6; height: 56
                                    Repeater {
                                        model: page.week
                                        Item { required property int modelData; required property int index; width: (parent.width - 36) / 7; height: 56
                                               Rectangle { anchors.bottom: parent.bottom; width: parent.width; radius: 3; height: Math.max(3, modelData / Math.max(1, Math.max.apply(null, page.week)) * 52)
                                                           color: modelData ? Auto.kindColor(page.kind) : Theme.surface3 } }
                                    }
                                }
                            }
                        }
                    }

                    // ---------- On ----------
                    Item {
                        width: cols.width / 3; height: cols.colH
                        Rectangle { width: 1; height: parent.height; color: Theme.border }
                        Column {
                            id: onTop
                            x: 18; y: 16
                            width: parent.width - 36
                            spacing: 10
                            Item {
                                width: parent.width; height: tabsOn.implicitHeight
                                Tabs {
                                    id: tabsOn
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    width: Math.min(implicitWidth, parent.width)
                                    tabs: [{ key: "all", label: "Every machine" }, { key: "dept", label: "A department" }, { key: "pick", label: "Pick machines" }]
                                    current: page.scope
                                    onPicked: function (k) { page.scope = k }
                                }
                            }
                            Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: Theme.fSmall
                                  text: page.scope === "all" ? "All " + Fleet.machines.length + " machines, and any registered later."
                                      : page.scope === "dept" ? "Every machine in one department, including new ones."
                                      : page.scope === "pick" ? "A fixed list. New machines are not added." : "Choose which machines it watches." }
                            Lab { visible: page.scope === "dept"; t: "Department"; width: parent.width
                                  Select { width: 250; value: page.dept || null; options: Fleet.depts.map(function (d) { return { value: d.id, label: d.name + " · " + d.machines.length + " machines" } })
                                           onPicked: function (v) { page.dept = v } } }
                            Lab { visible: page.scope === "pick"; t: "Machines"; width: parent.width
                                  Select { width: parent.width; multiple: true; search: true; placeholder: "Pick machines"; values: page.hosts
                                           options: Fleet.machines.map(function (m) { return { value: m.pc_id, label: m.host + " · " + (m.user || "no user") } })
                                           onPicked: function (v) { page.hosts = v } } }
                            Rectangle { visible: page.targets.some(function (m) { return !m.online }); width: parent.width; height: 36; radius: 5; color: Theme.surface2
                                        Txt { x: 12; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 24; font.pixelSize: Theme.fSmall; color: Theme.text2
                                              text: page.targets.filter(function (m) { return !m.online }).map(function (m) { return m.host }).join(", ") + " offline. The rule applies to it when it comes back." } }
                        }
                        Item {
                            x: 18; y: parent.height - cols.lookH - 20
                            width: parent.width - 36; height: cols.lookH
                            Rectangle { width: parent.width; height: 1; color: Theme.split }
                            Column {
                                y: 14; width: parent.width; spacing: 6
                                Cap { t: "MACHINES"; aside: Theme.many(page.targets.length, "machine") }
                                Txt { visible: page.targets.length === 0; color: Theme.text3; text: "None yet." }
                                Flickable {
                                    visible: page.targets.length > 0
                                    width: parent.width; height: 184
                                    contentWidth: width; contentHeight: mrows.height
                                    clip: true
                                    boundsBehavior: Flickable.StopAtBounds
                                    Column {
                                        id: mrows
                                        width: parent.width
                                        Repeater {
                                            model: page.targets
                                            Item {
                                                required property var modelData
                                                width: mrows.width; height: 29
                                                Rectangle { x: 0; anchors.verticalCenter: parent.verticalCenter; width: 8; height: 8; radius: 4; color: page.dot(modelData.status) }
                                                Txt { x: 18; anchors.verticalCenter: parent.verticalCenter; text: modelData.host; mono: true; font.pixelSize: Theme.fSmall; width: 70 }
                                                Txt { x: 92; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 92 - 80; text: modelData.user || "no one signed in"; color: Theme.text3; font.pixelSize: Theme.fSmall }
                                                Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: Fleet.words[modelData.status] || ""; color: Theme.text3; font.pixelSize: Theme.fTiny; elide: Text.ElideNone }
                                                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.split }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // ---------- Do ----------
                    Item {
                        width: cols.width / 3; height: cols.colH
                        Rectangle { width: 1; height: parent.height; color: Theme.border }
                        Column {
                            id: doTop
                            x: 18; y: 16
                            width: parent.width - 36
                            spacing: 0
                            Txt { visible: page.acts.length === 0; width: parent.width; color: Theme.text3; text: "No actions yet. Add one."; bottomPadding: 8 }
                            Repeater {
                                model: page.acts
                                Item {
                                    id: card
                                    required property var modelData
                                    required property int index
                                    readonly property var a: page.actOf(modelData)
                                    width: doTop.width
                                    height: cc.height + 20
                                    Rectangle { visible: index > 0; width: parent.width; height: 1; color: Theme.split }
                                    Column {
                                        id: cc
                                        y: 10; width: parent.width; spacing: 8
                                        Row {
                                            width: parent.width; spacing: 6
                                            Rectangle { width: 22; height: 22; radius: 4; color: Theme.surface3; anchors.verticalCenter: parent.verticalCenter
                                                        Txt { anchors.centerIn: parent; text: String(index + 1); mono: true; font.pixelSize: 12; elide: Text.ElideNone } }
                                            Select { width: parent.width - 22 - 62 - 52 - 18; search: true; value: modelData; anchors.verticalCenter: parent.verticalCenter
                                                     options: ["control", "monitoring", "custom"].reduce(function (o, c) {
                                                         var xs = page.lib.filter(function (x) { return x.cat === c }); if (!xs.length) return o
                                                         return o.concat([{ group: c.charAt(0).toUpperCase() + c.slice(1) }]).concat(xs.map(function (x) { return { value: x.id, label: x.name } })) }, [])
                                                     onPicked: function (v) { var a = page.acts.slice(); a[index] = v; page.acts = a } }
                                            Column {
                                                width: 62
                                                Txt { text: "Time limit"; color: Theme.text3; font.pixelSize: Theme.fTiny; elide: Text.ElideNone }
                                                Txt { text: card.a ? card.a.timeout_seconds + "s" : "—"; mono: true; height: Theme.control; verticalAlignment: Text.AlignVCenter; elide: Text.ElideNone }
                                            }
                                            Btn { small: true; kind: "text"; iconName: "arrowu"; enabled: index > 0; anchors.verticalCenter: parent.verticalCenter; onClicked: { var a = page.acts.slice(); var t = a[index - 1]; a[index - 1] = a[index]; a[index] = t; page.acts = a } }
                                            Btn { small: true; kind: "text"; iconName: "close"; anchors.verticalCenter: parent.verticalCenter; onClicked: { var a = page.acts.slice(); a.splice(index, 1); page.acts = a } }
                                        }
                                        Txt { x: 28; width: parent.width - 28; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: Theme.fSmall
                                              text: card.a ? card.a.cat.charAt(0).toUpperCase() + card.a.cat.slice(1) + " · " + (card.a.description || "") : "" }
                                    }
                                }
                            }
                            Rectangle { width: parent.width; height: 1; color: Theme.border }
                            Item { width: 1; height: 12 }
                            Btn { width: parent.width; iconName: "plus"; text: "Add an action"; enabled: page.lib.length > 0
                                  onClicked: page.acts = page.acts.concat([page.lib[0].id]) }
                            Item { width: 1; height: 12 }
                            Rectangle { width: parent.width; height: 1; color: Theme.split }
                            Item { width: 1; height: 12 }
                            Check { text: "Only run while the machine is idle"; controlled: true; checked: page.idle; onToggled: function (on) { page.idle = on } }
                            Item { visible: page.acts.some(function (id) { var a = page.actOf(id); return a && a.cat === "custom" }); width: 1; height: 12 }
                            Rectangle { visible: page.acts.some(function (id) { var a = page.actOf(id); return a && a.cat === "custom" })
                                        width: parent.width; height: 52; radius: 5; color: Theme.alpha(Theme.med, 0.10)
                                        Txt { x: 12; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 24; wrapMode: Text.WordWrap; color: Theme.med; font.pixelSize: Theme.fSmall; elide: Text.ElideNone
                                              text: "Custom scripts run without a sandbox. The script is checked before it is sent and again on arrival, and every run is recorded." } }
                        }
                        Item {
                            x: 18; y: parent.height - cols.lookH - 20
                            width: parent.width - 36; height: cols.lookH
                            Rectangle { width: parent.width; height: 1; color: Theme.split }
                            Flickable {
                                y: 14; width: parent.width; height: parent.height - 14
                                contentWidth: width; contentHeight: dl.height
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                Column {
                                    id: dl
                                    width: parent.width; spacing: 6
                                    Cap { t: "WHAT IT WILL DO"; aside: page.acts.length ? Theme.many(page.acts.length * (page.kind === "Schedule" ? page.targets.length : 1), "action run") + " per firing" : "" }
                                    Txt { visible: page.acts.length === 0; color: Theme.text3; text: "Nothing yet." }
                                    Repeater {
                                        model: page.acts
                                        Column {
                                            required property var modelData
                                            width: dl.width
                                            readonly property var a: page.actOf(modelData)
                                            Txt { text: page.actName(modelData); font.weight: Font.Medium; font.pixelSize: Theme.fSmall; width: parent.width }
                                            Txt { text: a ? (a.description || "") : ""; color: Theme.text3; font.pixelSize: Theme.fSmall; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                                            Item { width: 1; height: 6 }
                                            Rectangle { width: parent.width; height: 1; color: Theme.split }
                                        }
                                    }
                                    Txt { visible: page.acts.length > 0; color: Theme.text3; font.pixelSize: Theme.fSmall; topPadding: 4
                                          text: "Longest time limit " + Math.max.apply(null, page.acts.map(function (id) { var a = page.actOf(id); return a ? a.timeout_seconds : 0 })) + "s" + (page.idle ? " · only while the machine is idle" : "") }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ================= the name and the checks =================
        Panel {
            width: parent.width
            title: "Name it and check it"
            sub: page.editId ? "changes apply from the next firing; the record keeps the old version" : "saved rules are switched on straight away"
            Column {
                width: parent.width
                spacing: 18
                Row {
                    spacing: 0
                    Txt { width: 130; text: "Name"; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                    Field { width: 440; text: page.name; placeholderText: page.type === "" ? "Name this rule" : (Auto.names[page.type] || "Name the rule"); onTextEdited: page.name = text }
                }
                Rectangle {
                    width: parent.width
                    height: sent.height + 28
                    radius: 6
                    color: Theme.surface2
                    Txt { id: sent; x: 16; y: 14; width: parent.width - 32; wrapMode: Text.WordWrap; elide: Text.ElideNone; font.pixelSize: Theme.fLead; textFormat: Text.RichText
                          text: "<span style='color:" + Theme.text3 + "'>When</span> " + page.whenTxt + " <span style='color:" + Theme.text3 + "'>on</span> " + page.whereTxt
                                + "<span style='color:" + Theme.text3 + "'>, do</span> " + (page.doTxt || "<span style='color:" + Theme.med + "'>nothing yet</span>")
                                + (page.idle ? "<span style='color:" + Theme.text3 + "'>, only while idle</span>" : "") + "." }
                }
                Grid {
                    width: parent.width
                    columns: 4
                    rowSpacing: 12
                    columnSpacing: 20
                    Repeater {
                        model: [["Machines", String(page.targets.length)], ["Actions per firing", String(page.acts.length * (page.kind === "Schedule" ? page.targets.length : 1))],
                                ["Longest time limit", page.acts.length ? Math.max.apply(null, page.acts.map(function (id) { var a = page.actOf(id); return a ? a.timeout_seconds : 0 })) + "s" : "—"]]
                        Column { required property var modelData; width: (col.width - 28 - 60) / 4
                                 Txt { text: modelData[0]; color: Theme.text3; font.pixelSize: Theme.fSmall }
                                 Txt { text: modelData[1]; font.weight: Font.Medium } }
                    }
                }
            }
        }

        // ================= the bar: what is missing, Cancel, Test, Save =================
        Rectangle {
            width: parent.width
            height: 56
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.borderStrong
            Txt { x: 16; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 420; color: page.ok ? Theme.text3 : Theme.med; font.pixelSize: Theme.fSmall
                  text: page.ok ? (page.editId ? "Changes apply from the next firing. The record keeps the old version." : "Saved rules are switched on straight away.") : page.problems.filter(function (p) { return p !== "" })[0] }
            Row {
                anchors.right: parent.right
                anchors.rightMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Btn { text: "Cancel"; onClicked: page.cancel() }
                Btn { enabled: page.ok; text: "Test on one machine"; onClicked: page.testOnce() }
                Btn { kind: "primary"; enabled: page.ok; text: page.editId ? "Save changes" : "Save rule"; onClicked: page.save() }
            }
        }
    }
}
