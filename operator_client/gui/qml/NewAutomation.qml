import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// MAKING AN AUTOMATION (boards AU08-AU10), three steps in place of the page.
//
//   1 When   fill the sentence -- When [a file] [is changed] -- or start from an example beside it
//   2 Where  the details the trigger needs, each with its own control: a tier or a folder; days and a clock;
//            a level drawn against where the machines sit now; the machines, picked as marks, never typed
//   3 Do     the library ticked, grouped by what each does; the chosen ones in order; the whole automation
//            read back as one sentence, then saved switched on or off
//
// Changing an existing automation opens the same steps filled in. Its trigger's kind can change too: the
// Engine keeps an event's type, so a changed type is saved as a new automation and the old one switched off.
ColumnLayout {
    id: root

    property var tree: []
    property var actions: []
    property var editing: null              // the event being changed, or null for a new one
    property int step: 1
    property string kind: "file"
    property string type: "file.modified"
    property var match: ({})
    property var pcIds: null                // null = every machine in the department
    property var actionIds: []
    property var folders: []
    property var levels: null
    property bool showAll: false
    signal done(int id)
    signal cancelled()

    spacing: 16

    // --- starting -------------------------------------------------------------------------------------
    function start(ev) {
        editing = ev
        step = 1
        showAll = false
        if (ev) {
            type = ev.condition_spec.type
            kind = Automate.kindOf(type)
            match = JSON.parse(JSON.stringify(ev.condition_spec.match || {}))
            pcIds = ev.condition_spec.pc_ids ? ev.condition_spec.pc_ids.slice() : null
            actionIds = ev.actions.map(function (a) { return a.id })
        } else {
            kind = "file"; type = "file.modified"; match = {}; pcIds = null; actionIds = []
        }
    }
    function setKind(k) {
        kind = k
        type = Automate.verbs[k][0].type
        match = defaults(type)
    }
    function setType(t) { type = t; match = defaults(t) }
    function defaults(t) {
        if (t === "time.recurring") return { at: "18:00", days: [0, 1, 2, 3, 4] }
        if (t === "time.scheduled") { var d = new Date(); d.setDate(d.getDate() + 1); d.setHours(9, 0, 0, 0); return { at: d.toISOString() } }
        if (t === "threshold.cpu") return { percent: 85, duration_s: 300 }
        if (t === "threshold.memory") return { percent: 90 }
        if (t === "system.idle") return { seconds: 600 }
        return {}
    }
    function put(key, value) {
        var m = {}; for (var k in match) m[k] = match[k]
        if (value === undefined || value === null || value === "") delete m[key]; else m[key] = value
        match = m
    }
    // examples to start from: only triggers the Engine really detects, with the action that fits
    readonly property var examples: [
        { text: "Warn me when a restricted file is changed", sub: "files", type: "file.modified", match: { tier: "restricted" }, wants: ["notify"] },
        { text: "Snapshot a USB drive when it is plugged in", sub: "USB drives", type: "usb.inserted", match: {}, wants: ["usb_contents"] },
        { text: "Lock every screen at 18:00 on weekdays", sub: "a time", type: "time.recurring", match: { at: "18:00", days: [0, 1, 2, 3, 4] }, wants: ["lock_session"] },
        { text: "Tell me when someone signs in", sub: "people", type: "user.login", match: {}, wants: ["notify"] },
        { text: "Read the load when the processor stays busy", sub: "the machine", type: "threshold.cpu", match: { percent: 85, duration_s: 300 }, wants: ["system_metrics"] },
        { text: "Notify me when a task's final deadline passes", sub: "tasks", type: "task.deadline_final", match: {}, wants: ["notify"] }
    ]
    function useExample(ex) {
        type = ex.type
        kind = Automate.kindOf(ex.type)
        match = JSON.parse(JSON.stringify(ex.match))
        actionIds = actions.filter(function (a) { return ex.wants.indexOf(a.builtin_type) >= 0 }).slice(0, 1).map(function (a) { return a.id })
        step = 2
    }

    // --- machines --------------------------------------------------------------------------------------
    readonly property var machines: {
        var out = []
        for (var i = 0; i < tree.length; i++)
            for (var j = 0; j < tree[i].workers.length; j++) {
                var w = tree[i].workers[j]
                if (w.pc_id) out.push({ pc_id: w.pc_id, hostname: w.hostname, name: w.name,
                                        label: String(w.hostname || "").split("-").pop() })
            }
        return out
    }
    readonly property bool machineBound: !(type.indexOf("task.") === 0 || type === "flow.failed" || type === "resource.violation")
    function picked(pcId) { return pcIds === null || pcIds.indexOf(pcId) >= 0 }
    function toggle(pcId) {
        var cur = pcIds === null ? machines.map(function (m) { return m.pc_id }) : pcIds.slice()
        var i = cur.indexOf(pcId)
        if (i >= 0) cur.splice(i, 1); else cur.push(pcId)
        pcIds = cur.length === machines.length ? null : cur
    }
    readonly property int pickedCount: pcIds === null ? machines.length : pcIds.length
    readonly property string whereWords: !machineBound ? "" : pcIds === null ? "every machine"
                                         : pcIds.length === 1 ? machines.filter(function (m) { return m.pc_id === pcIds[0] }).map(function (m) { return m.hostname })[0] || "1 machine"
                                         : pcIds.length + " machines"
    function loadFolders() {
        var pc = pcIds && pcIds.length ? pcIds[0] : (machines.length ? machines[0].pc_id : 0)
        if (!pc) return
        falcon.call("index.folders", { pc_id: pc }, function (ok, r) { root.folders = ok ? r.folders : [] })
    }
    onStepChanged: {
        if (step === 2 && kind === "file") loadFolders()
        if (step === 2 && kind === "machine")
            falcon.call("control.levels", pcIds ? { pc_ids: pcIds } : {}, function (ok, r) { root.levels = ok ? r : null })
    }

    // --- actions ----------------------------------------------------------------------------------------
    function actionById(id) { for (var i = 0; i < actions.length; i++) if (actions[i].id === id) return actions[i]; return null }
    function tick(id) {
        var c = actionIds.slice(), i = c.indexOf(id)
        if (i >= 0) c.splice(i, 1); else c.push(id)
        actionIds = c
    }
    function moveUp(i) { if (i <= 0) return; var c = actionIds.slice(); var t = c[i - 1]; c[i - 1] = c[i]; c[i] = t; actionIds = c }

    // --- the sentence, read back --------------------------------------------------------------------------
    readonly property var parts: {
        var p = [{ w: "When" }, { slot: Automate.kindText(kind), tone: "accent", step: 1 }, { w: Automate.verbOf(type).split(" ")[0] === "is" ? "is" : "" },
                 { slot: Automate.verbOf(type).replace(/^is /, ""), tone: "accent", step: 1 }]
        var m = match
        if (kind === "file") {
            if (m.tier) p.push({ w: "in" }, { slot: Automate.tierText(m.tier), tone: "danger", step: 2 })
            else if (m.path_prefix) p.push({ w: "in" }, { slot: Automate.folderName(m.path_prefix), tone: "danger", step: 2 })
        }
        if (type === "time.recurring") p.push({ w: m.interval_s ? "" : "at" }, { slot: m.interval_s ? "every " + Automate.minutes(m.interval_s) : Automate.days(m.days).toLowerCase() + " " + m.at, tone: "warn", step: 2 })
        if (type === "time.scheduled") p.push({ w: "on" }, { slot: Qt.formatDateTime(new Date(m.at), "d MMM, HH:mm"), tone: "warn", step: 2 })
        if (type === "threshold.cpu" || type === "threshold.memory") p.push({ w: "above" }, { slot: m.percent + " %", tone: "warn", step: 2 })
        if (type === "system.idle") p.push({ w: "for" }, { slot: Automate.minutes(m.seconds), tone: "warn", step: 2 })
        if (kind === "program" && m.process) p.push({ w: "—" }, { slot: m.process, tone: "warn", step: 2 })
        if (machineBound) p.push({ w: "on" }, { slot: whereWords, tone: "accent", step: 2 })
        return p.filter(function (x) { return x.w !== "" })
    }
    readonly property var doParts: {
        var p = []
        for (var i = 0; i < actionIds.length; i++) {
            var a = actionById(actionIds[i])
            p.push({ w: i === 0 ? "do" : "then" }, { slot: Automate.actionName(a), tone: "ok", step: 3 })
        }
        return p
    }

    function save(enabled) {
        var payload = { type: type, match: match, pc_ids: machineBound ? pcIds : null, action_ids: actionIds, enabled: enabled }
        if (editing && editing.condition_spec.type === type) {
            falcon.call("control.event_update", { event_id: editing.id, match: match, pc_ids: payload.pc_ids,
                                                  action_ids: actionIds, enabled: enabled }, function (ok, r) {
                if (!ok) { shell.notify(r.message, true); return }
                shell.notify("Saved", false); root.done(r.event.id)
            })
            return
        }
        var old = editing
        falcon.call("control.event_create", payload, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            if (old) falcon.call("control.event_delete", { event_id: old.id }, function () {})
            shell.notify(enabled ? "Saved and switched on" : "Saved, switched off", false)
            root.done(r.event.id)
        })
    }

    // =====================================================================================================
    Item {
        Layout.fillWidth: true
        Layout.preferredHeight: 48
        Column {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4
            Row {
                spacing: 6
                Txt { text: "Automation"; color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody
                      MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: root.cancelled() } }
                Icon { name: "chev"; color: Qt.rgba(1, 1, 1, 0.45); size: 12; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: root.editing ? "Change it" : "New automation"; color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
            }
            Row {
                spacing: 12
                Txt { text: root.editing ? "Change the automation" : "New automation"; color: "#ffffff"; font.pixelSize: Theme.fTitle; font.weight: Font.Bold
                      anchors.verticalCenter: parent.verticalCenter }
                Txt { text: "step " + root.step + " of 3"; color: Theme.accent; font.pixelSize: Theme.fBody; anchors.verticalCenter: parent.verticalCenter }
            }
        }
        Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "Esc to go back"
              color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody }
    }

    // the three steps
    Row {
        Layout.fillWidth: true
        spacing: 18
        Repeater {
            model: [{ n: 1, t: "When", s: "what happens" }, { n: 2, t: "Where", s: "which machines, which files" }, { n: 3, t: "Do", s: "which actions" }]
            delegate: Row {
                required property var modelData
                required property int index
                spacing: 18
                Rectangle { visible: index > 0; width: 60; height: 1; color: Theme.line2; anchors.verticalCenter: parent.verticalCenter }
                Row {
                    spacing: 10
                    Rectangle {
                        width: 26; height: 26; radius: 13
                        color: root.step === modelData.n ? Theme.accent : root.step > modelData.n ? Theme.okSoft : Qt.rgba(1, 1, 1, 0.06)
                        Txt { anchors.centerIn: parent; visible: root.step <= modelData.n; text: String(modelData.n); font.pixelSize: Theme.fMeta; font.weight: Font.Bold
                              color: root.step === modelData.n ? Theme.frameA : Theme.faint }
                        Icon { anchors.centerIn: parent; visible: root.step > modelData.n; name: "check"; size: 13; color: Theme.ok }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        Txt { text: modelData.t; color: root.step >= modelData.n ? Theme.ink : Theme.faint; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                        Txt { text: modelData.s; color: Theme.faint; font.pixelSize: Theme.fMeta }
                    }
                }
                TapHandler { enabled: modelData.n < root.step; onTapped: root.step = modelData.n }
            }
        }
    }

    // ---------------------------------------------------------------------------------------------------
    // STEP 1: When
    RowLayout {
        visible: root.step === 1
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 20
        GridCell {
            id: whenCell
            objectName: "newAutoWhen"
            Layout.fillWidth: true
            Layout.preferredWidth: 3
            Layout.fillHeight: true
            topAlign: true
            title: "When"
            narration: ({ brief: "fill the sentence", tone: "accent", state: "ok" })
            ColumnLayout {
                width: parent.width
                height: whenCell.room
                spacing: 14
                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    Txt { text: "When"; color: Theme.dim; font.pixelSize: 19; height: 34; verticalAlignment: Text.AlignVCenter }
                    SentenceSlot {
                        objectName: "newAutoKind"
                        text: Automate.kindText(root.kind); fontSize: 18
                        onClicked: kindMenu.open()
                        Menu { id: kindMenu; y: parent.height + 4
                               Repeater { model: Automate.kinds
                                          delegate: MenuItem { required property var modelData; text: modelData.text; onTriggered: root.setKind(modelData.key) } } }
                    }
                    Txt { visible: Automate.verbOf(root.type).indexOf("is ") === 0; text: "is"; color: Theme.dim; font.pixelSize: 19; height: 34; verticalAlignment: Text.AlignVCenter }
                    SentenceSlot {
                        objectName: "newAutoVerb"
                        text: Automate.verbOf(root.type).replace(/^is /, ""); fontSize: 18
                        onClicked: verbMenu.open()
                        Menu { id: verbMenu; y: parent.height + 4
                               Repeater { model: Automate.verbs[root.kind] || []
                                          delegate: MenuItem { required property var modelData; text: modelData.text; onTriggered: root.setType(modelData.type) } } }
                    }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
                Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fBody
                      text: Automate.kinds.map(function (k) { return k.text }).join(" · ") }
                Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta
                      text: "The first blank chooses what kind of thing happens; the rest follow from it. A file being opened cannot be seen, so it is not offered." }
                Item { Layout.fillHeight: true }
                RowLayout {
                    Layout.fillWidth: true
                    GBtn { text: "Cancel"; onClicked: root.cancelled() }
                    Item { Layout.fillWidth: true }
                    TBtn { objectName: "newAutoNext"; text: "Next: where"; iconName: "chev"; onClicked: root.step = 2 }
                }
            }
        }
        GridCell {
            objectName: "newAutoExamples"
            Layout.fillWidth: true
            Layout.preferredWidth: 2
            Layout.fillHeight: true
            topAlign: true
            title: "Start from an example"
            narration: ({ brief: "six common ones", state: "ok" })
            Column {
                width: parent.width
                spacing: 8
                Txt { text: "Or start from one of these, and change what you need."; color: Theme.dim; font.pixelSize: Theme.fBody }
                Repeater {
                    model: root.examples
                    delegate: InfoCard {
                        required property var modelData
                        width: parent.width
                        iconName: Automate.iconFor(modelData.type); iconTone: "accent"
                        title: modelData.text; line: modelData.sub
                        stateWord: "use"; stateTone: "accent"
                        onClicked: root.useExample(modelData)
                    }
                }
            }
        }
    }

    // ---------------------------------------------------------------------------------------------------
    // STEP 2: Where
    RowLayout {
        visible: root.step === 2
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 20
        ColumnLayout {
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            Layout.fillHeight: true
            spacing: 20
            GridCell {
                objectName: "newAutoDetail"
                Layout.fillWidth: true
                Layout.preferredHeight: root.kind === "machine" ? 300 : 230
                topAlign: true
                title: root.kind === "file" ? "Where the file is" : root.kind === "time" ? "When, exactly"
                       : root.kind === "machine" ? (root.type === "system.idle" ? "How long idle" : "How busy") : root.kind === "program" ? "Which program" : "Nothing more to choose"
                narration: ({ brief: root.kind === "file" ? "a tier, or a folder" : root.kind === "machine" ? "set against what is normal" : "", tone: "danger", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 12

                    // a file: a tier, or a folder from the index
                    Column {
                        visible: root.kind === "file"
                        width: parent.width
                        spacing: 10
                        Row {
                            spacing: 6
                            Repeater {
                                model: Automate.tiers
                                delegate: Choice { required property var modelData; text: modelData.text; tone: modelData.tone
                                                   on: root.match.tier === modelData.key
                                                   onPicked: { root.put("path_prefix", null); root.put("tier", root.match.tier === modelData.key ? null : modelData.key) } }
                            }
                        }
                        Txt { text: "or a folder"; color: Theme.faint; font.pixelSize: Theme.fMeta }
                        SentenceSlot {
                            text: root.match.path_prefix ? Automate.folderName(root.match.path_prefix) : "any folder"
                            tone: root.match.path_prefix ? "danger" : "accent"; dashed: !root.match.path_prefix
                            onClicked: folderMenu.open()
                            Menu { id: folderMenu; y: parent.height + 4
                                   MenuItem { text: "any folder"; onTriggered: root.put("path_prefix", null) }
                                   Repeater { model: root.folders
                                              delegate: MenuItem { required property var modelData; text: modelData.name + "   (" + modelData.files + " files)"
                                                                   onTriggered: { root.put("tier", null); root.put("path_prefix", modelData.path) } } } }
                        }
                    }

                    // a time: days and a clock, or every few minutes
                    Column {
                        visible: root.type === "time.recurring"
                        width: parent.width
                        spacing: 10
                        Row {
                            spacing: 6
                            Repeater {
                                model: Automate.dayNames
                                delegate: Choice { required property var modelData; required property int index; text: modelData
                                                   on: !root.match.interval_s && (root.match.days || []).indexOf(index) >= 0
                                                   onPicked: { var d = (root.match.days || []).slice(); var i = d.indexOf(index)
                                                               if (i >= 0) d.splice(i, 1); else d.push(index)
                                                               root.put("interval_s", null); root.put("days", d.sort()); if (!root.match.at) root.put("at", "18:00") } }
                            }
                        }
                        Row {
                            spacing: 8
                            Txt { text: "at"; color: Theme.faint; font.pixelSize: Theme.fBody; anchors.verticalCenter: parent.verticalCenter }
                            Clock { value: root.match.at || "18:00"; onChosen: function (v) { root.put("interval_s", null); root.put("at", v) } }
                        }
                        Row {
                            spacing: 6
                            Txt { text: "or every"; color: Theme.faint; font.pixelSize: Theme.fBody; anchors.verticalCenter: parent.verticalCenter }
                            Repeater {
                                model: [900, 1800, 3600]
                                delegate: Choice { required property var modelData; text: Automate.minutes(modelData)
                                                   on: root.match.interval_s === modelData
                                                   onPicked: root.match = { interval_s: modelData } }
                            }
                        }
                    }
                    Column {
                        visible: root.type === "time.scheduled"
                        width: parent.width
                        spacing: 10
                        Row {
                            spacing: 6
                            Repeater {
                                model: 7
                                delegate: Choice {
                                    required property int index
                                    readonly property date day: { var d = new Date(); d.setDate(d.getDate() + index); return d }
                                    text: index === 0 ? "Today" : index === 1 ? "Tomorrow" : Qt.formatDate(day, "ddd d")
                                    on: !!root.match.at && Qt.formatDate(new Date(root.match.at), "yyyyMMdd") === Qt.formatDate(day, "yyyyMMdd")
                                    onPicked: { var d = new Date(root.match.at || Date.now()); var n = new Date(day)
                                                n.setHours(d.getHours(), d.getMinutes(), 0, 0); root.put("at", n.toISOString()) }
                                }
                            }
                        }
                        Row {
                            spacing: 8
                            Txt { text: "at"; color: Theme.faint; font.pixelSize: Theme.fBody; anchors.verticalCenter: parent.verticalCenter }
                            Clock { value: root.match.at ? Qt.formatDateTime(new Date(root.match.at), "HH:mm") : "09:00"
                                    onChosen: function (v) { var d = new Date(root.match.at || Date.now()); d.setHours(parseInt(v.split(":")[0]), parseInt(v.split(":")[1]), 0, 0)
                                                             root.put("at", d.toISOString()) } }
                        }
                    }

                    // the machine: a level, drawn against where these machines sit now
                    Level {
                        visible: root.type === "threshold.cpu" || root.type === "threshold.memory"
                        width: parent.width
                        what: root.type === "threshold.cpu" ? "The processor" : "Memory in use"
                        value: root.match.percent || 85
                        normal: root.levels ? (root.type === "threshold.cpu" ? root.levels.cpu : root.levels.memory) : null
                        onMoved: function (v) { root.put("percent", v) }
                    }
                    Row {
                        visible: root.type === "threshold.cpu"
                        spacing: 6
                        Txt { text: "and stays there for"; color: Theme.faint; font.pixelSize: Theme.fBody; anchors.verticalCenter: parent.verticalCenter }
                        Repeater {
                            model: [60, 300, 900, 3600]
                            delegate: Choice { required property var modelData; text: Automate.minutes(modelData); tone: "warn"
                                               on: root.match.duration_s === modelData; onPicked: root.put("duration_s", modelData) }
                        }
                    }
                    Row {
                        visible: root.type === "system.idle"
                        spacing: 6
                        Txt { text: "untouched for"; color: Theme.faint; font.pixelSize: Theme.fBody; anchors.verticalCenter: parent.verticalCenter }
                        Repeater {
                            model: [300, 600, 1800, 3600]
                            delegate: Choice { required property var modelData; text: Automate.minutes(modelData); tone: "warn"
                                               on: root.match.seconds === modelData; onPicked: root.put("seconds", modelData) }
                        }
                    }

                    // a program: its name, as it shows in the task list
                    Column {
                        visible: root.kind === "program"
                        width: parent.width
                        spacing: 8
                        TextField {
                            id: processField
                            width: Math.min(parent.width, 320)
                            placeholderText: "any program, or a name like excel.exe"
                            text: root.match.process || ""
                            onEditingFinished: root.put("process", text.trim())
                        }
                        Txt { text: "Leave it empty for any program."; color: Theme.faint; font.pixelSize: Theme.fMeta }
                    }

                    Txt { visible: ["usb", "user", "network", "work"].indexOf(root.kind) >= 0; width: parent.width; wrapMode: Text.WordWrap
                          color: Theme.dim; font.pixelSize: Theme.fBody
                          text: root.kind === "work" ? "It watches your own tasks and flows; nothing more to choose here."
                                                     : "Any " + Automate.kindText(root.kind).replace(/^(a|the) /, "") + " counts; choose the machines below." }
                }
            }
            GridCell {
                objectName: "newAutoMachines"
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "Which machines"
                narration: ({ brief: root.machineBound ? "picked, never typed" : "", tone: "accent", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 12
                    visible: root.machineBound
                    PagedRow {
                        objectName: "newAutoMarks"
                        width: parent.width
                        height: 98
                        itemWidth: 72
                        spacing: 10
                        model: root.machines
                        delegate: MachineMark {
                            property var modelData: ({})
                            size: 58
                            label: modelData.label || ""
                            name: modelData.name || ""
                            status: root.picked(modelData.pc_id) ? "chosen" : "free"
                            TapHandler { onTapped: root.toggle(parent.modelData.pc_id) }
                        }
                    }
                    Txt { color: Theme.dim; font.pixelSize: Theme.fBody
                          text: root.pickedCount + " of " + root.machines.length + " machines. Click one to add or take it away." }
                    Row {
                        spacing: 8
                        GBtn { text: "Every machine here"; small: true; onClicked: root.pcIds = null }
                        GBtn { text: "None"; small: true; onClicked: root.pcIds = [] }
                    }
                }
                Txt { visible: !root.machineBound; width: parent.width; wrapMode: Text.WordWrap; color: Theme.dim; font.pixelSize: Theme.fBody
                      text: "Tasks and flows are not tied to one machine: it runs its actions where the task or flow is." }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            Layout.fillHeight: true
            spacing: 20
            GridCell {
                id: soFarCell
            objectName: "newAutoSoFar"
                Layout.fillWidth: true
                Layout.preferredHeight: 230
                topAlign: true
                title: "So far"
                narration: ({ state: "ok" })
                ColumnLayout {
                    width: parent.width
                    height: soFarCell.room
                    Txt { text: "It reads"; color: Theme.faint; font.pixelSize: Theme.fMeta }
                    Reads { Layout.fillWidth: true; parts: root.parts; onJump: function (s) { root.step = s } }
                    Item { Layout.fillHeight: true }
                    RowLayout {
                        Layout.fillWidth: true
                        GBtn { text: "Back"; onClicked: root.step = 1 }
                        Item { Layout.fillWidth: true }
                        TBtn { objectName: "newAutoNext2"; text: "Next: do"; iconName: "chev"; enabled: !root.machineBound || root.pickedCount > 0
                               onClicked: root.step = 3 }
                    }
                }
            }
            GridCell {
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "Good to know"
                narration: ({ state: "ok" })
                Column {
                    width: parent.width
                    spacing: 10
                    Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                          text: ["time", "machine"].indexOf(root.kind) >= 0 ? "Falcon checks this about once a minute."
                                                                             : "Falcon hears about this the moment it happens." }
                    Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.dim; font.pixelSize: Theme.fBody
                          text: root.kind === "file" ? "Only files in the folders Falcon watches on each machine. A restricted file is caught wherever a copy of it turns up, not only in its folder."
                                : root.kind === "machine" ? "It fires only past the line, and then not again for five minutes, so a busy spell is one warning, not dozens."
                                : root.kind === "time" ? "The actions run on each machine you pick, at the same moment."
                                : root.kind === "work" ? "It fires once for each task or flow it happens to."
                                : "Each machine tells Falcon itself, so a machine that is switched off tells nothing." }
                }
            }
        }
    }

    // ---------------------------------------------------------------------------------------------------
    // STEP 3: Do
    RowLayout {
        visible: root.step === 3
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 20
        GridCell {
            objectName: "newAutoLibrary"
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            Layout.fillHeight: true
            topAlign: true
            title: "Pick what it does"
            narration: ({ brief: "grouped, with what each does", state: root.actions.length ? "ok" : "empty",
                          note: "No actions yet", sentence: "Make one on the Actions page first." })
            Column {
                width: parent.width
                spacing: 4
                Repeater {
                    model: [{ k: "control", t: "CONTROL" }, { k: "monitoring", t: "MONITORING" }, { k: "custom", t: "CUSTOM" }]
                    delegate: Column {
                        id: group
                        required property var modelData
                        readonly property var items: root.actions.filter(function (a) { return a.kind === modelData.k })
                        readonly property int limit: root.showAll ? 99 : 4
                        width: parent.width
                        spacing: 0
                        visible: items.length > 0
                        Item { width: 1; height: 8 }
                        Item {
                            width: parent.width; height: 20
                            Txt { text: group.modelData.t; color: Theme.accent; font.pixelSize: Theme.fMeta; font.weight: Font.Bold }
                            Txt { anchors.right: parent.right; text: String(group.items.length); color: Theme.faint; font.pixelSize: Theme.fMeta }
                        }
                        Repeater {
                            model: group.items.slice(0, group.limit)
                            delegate: Item {
                                required property var modelData
                                readonly property bool ticked: root.actionIds.indexOf(modelData.id) >= 0
                                width: parent.width; height: 35
                                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                                Rectangle {
                                    id: box
                                    width: 17; height: 17; radius: 4; anchors.verticalCenter: parent.verticalCenter
                                    color: parent.ticked ? Theme.accentSoft : "transparent"
                                    border.width: 1.2; border.color: parent.ticked ? Theme.accent : Theme.line2
                                    Icon { anchors.centerIn: parent; visible: parent.parent.ticked; name: "check"; size: 12; color: Theme.accent }
                                }
                                Icon { id: aIcon; x: 30; anchors.verticalCenter: parent.verticalCenter; name: Automate.actionIcon(modelData); size: 15; color: Theme.dim }
                                Txt { x: 56; anchors.verticalCenter: parent.verticalCenter; text: Automate.actionName(modelData); color: Theme.ink
                                      font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                                Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: Automate.actionDoes(modelData)
                                      color: Theme.faint; font.pixelSize: Theme.fMeta }
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.tick(modelData.id) }
                            }
                        }
                        Txt { visible: group.items.length > group.limit; topPadding: 6; text: "+ " + (group.items.length - group.limit) + " more"
                              color: Theme.accent; font.pixelSize: Theme.fMeta
                              MouseArea { anchors.fill: parent; anchors.margins: -4; cursorShape: Qt.PointingHandCursor; onClicked: root.showAll = true } }
                    }
                }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            Layout.fillHeight: true
            spacing: 20
            GridCell {
                objectName: "newAutoOrder"
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(180, 110 + root.actionIds.length * 53)
                topAlign: true
                title: "In order"
                narration: ({ brief: root.actionIds.length === 0 ? "none yet" : root.actionIds.length === 1 ? "one action" : root.actionIds.length + " actions",
                              tone: root.actionIds.length ? "ok" : "warn", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 0
                    Repeater {
                        model: root.actionIds
                        delegate: Item {
                            required property var modelData
                            required property int index
                            readonly property var a: root.actionById(modelData)
                            width: parent.width; height: 53
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                            Row {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 12
                                Txt { text: String(index + 1); width: 14; color: Theme.faint; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                                      anchors.verticalCenter: parent.verticalCenter }
                                Icon { name: Automate.actionIcon(a); size: 17; color: Theme.ok; anchors.verticalCenter: parent.verticalCenter }
                                Column {
                                    Txt { text: Automate.actionName(a); color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                                    Txt { text: Automate.actionTiming(a); color: Theme.faint; font.pixelSize: Theme.fMeta }
                                }
                            }
                            Row {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 14
                                Icon { visible: index > 0; name: "chevu"; size: 14; color: Theme.dim
                                       TapHandler { onTapped: root.moveUp(index) } }
                                Icon { name: "x"; size: 13; color: Theme.faint
                                       TapHandler { onTapped: root.tick(modelData) } }
                            }
                        }
                    }
                    Txt { topPadding: 10; width: parent.width; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta
                          text: root.actionIds.length ? "They run in this order, each on its own. One failing does not stop the next."
                                                      : "Tick what it should do on the left." }
                }
            }
            GridCell {
                id: readsCell
            objectName: "newAutoReads"
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "It reads"
                narration: ({ brief: "the whole automation", tone: "accent", state: "ok" })
                ColumnLayout {
                    width: parent.width
                    height: readsCell.room
                    Reads { Layout.fillWidth: true; parts: root.parts.concat(root.doParts); onJump: function (s) { root.step = s } }
                    Item { Layout.fillHeight: true }
                    RowLayout {
                        Layout.fillWidth: true
                        GBtn { text: "Back"; onClicked: root.step = 2 }
                        Item { Layout.fillWidth: true }
                        GBtn { text: "Save, switched off"; enabled: root.actionIds.length > 0; onClicked: root.save(false) }
                        TBtn { objectName: "newAutoSave"; text: "Save and switch on"; iconName: "check"; enabled: root.actionIds.length > 0
                               onClicked: root.save(true) }
                    }
                }
            }
        }
    }

    // --- small parts ------------------------------------------------------------------------------------

    // one choice among a few: plain words, the chosen one on a soft tone
    component Choice: Rectangle {
        id: ch
        property string text: ""
        property string tone: "accent"
        property bool on: false
        signal picked()
        width: chLabel.implicitWidth + 20; height: 28; radius: 7
        color: on ? (tone === "danger" ? Theme.dangerSoft : tone === "warn" ? Theme.warnSoft : tone === "ok" ? Theme.okSoft : Theme.accentSoft) : "transparent"
        Txt { id: chLabel; anchors.centerIn: parent; text: ch.text; font.pixelSize: Theme.fBody; font.weight: ch.on ? Font.DemiBold : Font.Normal
              color: ch.on ? Theme.tone(ch.tone) : Theme.dim }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: ch.picked() }
    }

    // a clock, as two picks: the hour, then the minutes
    component Clock: Row {
        id: clk
        property string value: "18:00"
        signal chosen(string v)
        spacing: 2
        SentenceSlot { text: clk.value.split(":")[0]; tone: "warn"; fontSize: 18; onClicked: hours.open()
                       Menu { id: hours; y: parent.height + 4; height: 320
                              Repeater { model: 24; delegate: MenuItem { required property int index; text: (index < 10 ? "0" : "") + index
                                                                        onTriggered: clk.chosen(text + ":" + clk.value.split(":")[1]) } } } }
        Txt { text: ":"; color: Theme.warn; font.pixelSize: 18; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
        SentenceSlot { text: clk.value.split(":")[1]; tone: "warn"; fontSize: 18; onClicked: mins.open()
                       Menu { id: mins; y: parent.height + 4
                              Repeater { model: ["00", "15", "30", "45"]; delegate: MenuItem { required property var modelData; text: modelData
                                                                                             onTriggered: clk.chosen(clk.value.split(":")[0] + ":" + modelData) } } } }
    }

    // the level, redrawn against what is normal: the band where these machines sit now, the line, and the part
    // past the line (where it would fire) striped
    component Level: Column {
        id: lv
        property string what: ""
        property int value: 85
        property var normal: null           // [low, high] now, or null when no machine has reported
        signal moved(int v)
        spacing: 8
        Txt { text: lv.what + ", across these machines"; color: Theme.dim; font.pixelSize: Theme.fBody }
        Item {
            width: parent.width; height: 58
            Txt { x: track.x + track.width * lv.value / 100 - width / 2; y: 0; text: lv.value + " %"; color: Theme.warn
                  font.pixelSize: Theme.fSection; font.weight: Font.Bold }
            Rectangle {
                id: track
                y: 28; width: parent.width; height: 10; radius: 5; color: Qt.rgba(1, 1, 1, 0.06)
                Rectangle { visible: lv.normal !== null; x: lv.normal ? track.width * lv.normal[0] / 100 : 0; height: parent.height; radius: 5
                            width: lv.normal ? Math.max(8, track.width * (lv.normal[1] - lv.normal[0]) / 100) : 0; color: Theme.ok; opacity: 0.55 }
                Item {
                    x: track.width * lv.value / 100; width: track.width - x; height: parent.height; clip: true
                    Row { spacing: 5; Repeater { model: 60; delegate: Rectangle { width: 3; height: 16; y: -3; rotation: 30; color: Theme.warn; opacity: 0.8 } } }
                }
                Rectangle { x: track.width * lv.value / 100 - 2; y: -6; width: 4; height: 22; radius: 2; color: "#ffffff" }
                MouseArea {
                    anchors.fill: parent; anchors.margins: -10; cursorShape: Qt.SizeHorCursor
                    function set(mx) { lv.moved(Math.max(5, Math.min(99, Math.round((mx - 10) / track.width * 100)))) }
                    onPressed: function (m) { set(m.x) }
                    onPositionChanged: function (m) { if (pressed) set(m.x) }
                }
            }
            Txt { y: 44; text: "0"; color: Theme.faint; font.pixelSize: Theme.fMeta; monospace: true }
            Txt { y: 44; anchors.right: parent.right; text: "100"; color: Theme.faint; font.pixelSize: Theme.fMeta; monospace: true }
            Txt { visible: lv.normal !== null; y: 44; x: lv.normal ? track.width * lv.normal[0] / 100 : 0; color: Theme.ok; font.pixelSize: Theme.fMeta
                  text: lv.normal ? "now " + Math.round(lv.normal[0]) + "–" + Math.round(lv.normal[1]) + " %" : "" }
        }
        Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta
              text: lv.normal === null ? "No machine has reported its level yet, so there is nothing to set it against."
                    : "It fires only in the striped part, past the line: keep it well clear of where the machines sit now." }
    }

    // the sentence as it stands; each blank goes back to the step that fills it
    component Reads: Flow {
        id: rd
        property var parts: []
        signal jump(int s)
        spacing: 7
        Repeater {
            model: rd.parts
            delegate: Loader {
                required property var modelData
                sourceComponent: modelData.slot !== undefined ? slotPart : wordPart
                Component { id: wordPart; Txt { text: modelData.w; color: Theme.dim; font.pixelSize: 17; height: 32; verticalAlignment: Text.AlignVCenter } }
                Component { id: slotPart; SentenceSlot { text: modelData.slot; tone: modelData.tone; fontSize: 16; onClicked: rd.jump(modelData.step) } }
            }
        }
    }
}
