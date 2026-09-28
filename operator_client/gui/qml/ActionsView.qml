import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "."

// ACTIONS (boards AU05-AU07), an Admin's own page. A library and a workbench:
//
//   left   the library, grouped Control / Monitoring / Custom, each with what it does. Built-ins not set up yet
//          are listed faintly beneath their group: choosing one sets it up.
//   right  the chosen action's own settings -- only what THIS action needs, each with the control that need
//          calls for (AU06); When it runs; Try it on one machine
//   custom a script FILE dropped or chosen (never typed), the check said in words, then the same When / Try (AU07)
//
// What an action cannot be told yet (a lock's length and message, how long a notice stays up, a restart's
// warning time, the programs to pick from) is not offered: see design/ENGINE-WORK.md.
Item {
    id: root

    property string mode: "library"         // library | custom
    property var builtin: ({})
    property var actions: []                // stored, flattened with .kind
    property var events: []                 // to say "used in N automations"
    property var tree: []
    property var sel: null                  // the chosen stored action, or a draft {id: 0, builtin_type, kind}
    property var draft: ({})                // the settings being edited: {name, params, timeout_seconds, timing}
    property bool dirty: false
    property int tryPc: 0
    property var trial: null                // {execution_id, hostname, status, output}
    property string clock: ""

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("control.action_list", {}, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            root.builtin = r.builtin
            var flat = []
            ;["control", "monitoring", "custom"].forEach(function (k) { r.actions[k].forEach(function (a) { a.kind = k; flat.push(a) }) })
            root.actions = flat
            if (root.sel && root.sel.id) { var again = flat.filter(function (a) { return a.id === root.sel.id })[0]; if (again) root.choose(again) }
            else if (!root.sel && flat.length) root.choose(flat[0])
        })
        falcon.call("control.event_list", {}, function (ok, r) { if (ok) root.events = r.events })
        falcon.call("hierarchy.tree", {}, function (ok, r) {
            if (!ok) return
            root.tree = r.departments
            if (!root.tryPc && root.machines.length) root.tryPc = root.machines[0].pc_id
        })
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onScopeChanged() { if (falcon.isConnected) root.refresh() }
        function onPushReceived(type, p) {
            if (type === "action.status" && root.trial && p.execution_id === root.trial.execution_id) root.readTrial()
        }
    }
    Keys.onEscapePressed: root.mode = "library"
    focus: true

    // --- the library ------------------------------------------------------------------------------------
    readonly property var groups: [{ k: "control", t: "CONTROL" }, { k: "monitoring", t: "MONITORING" }, { k: "custom", t: "CUSTOM" }]
    function storedIn(k) { return actions.filter(function (a) { return a.kind === k }) }
    // built-ins of this group that are not set up yet
    function unsetIn(k) {
        var have = actions.map(function (a) { return a.builtin_type })
        var out = []
        for (var t in builtin) if (builtin[t].category === k && have.indexOf(t) < 0) out.push({ id: 0, kind: k, action_kind: k, builtin_type: t })
        return out
    }
    // the library as ONE flat list -- a heading row, then its actions, at one pitch, so the cell can page
    readonly property var libraryRows: {
        var out = []
        for (var g = 0; g < groups.length; g++) {
            var k = groups[g].k
            var stored = storedIn(k)
            var all = stored.concat(unsetIn(k))
            out.push({ head: groups[g].t, count: stored.length })
            for (var i = 0; i < all.length; i++) out.push({ action: all[i] })
            if (k === "custom" && stored.length === 0)
                out.push({ note: (falcon && falcon.role === "admin") ? "None yet. Add your own with New custom action."
                                                                    : "None yet. Only the Admin adds their own scripts." })
        }
        return out
    }
    function usedIn(id) { return events.filter(function (e) { return e.actions.some(function (a) { return a.id === id }) }).length }
    function choose(a) {
        mode = "library"
        sel = a
        draft = { name: a.id ? a.name : Automate.actionName(a), params: JSON.parse(JSON.stringify(a.params || defaults(a.builtin_type))),
                  timeout_seconds: a.timeout_seconds || 60, timing: a.timing || { mode: "immediate" } }
        dirty = false
        trial = null
    }
    function defaults(t) {
        if (t === "notify") return { message: "" }
        if (t === "lock_session") return { duration_s: 900 }
        if (t === "rename_file") return { path: "", new_name: "" }
        if (t === "kill_process") return { name: "" }
        if (t === "start_process") return { command: "" }
        if (t === "restore_file" || t === "snapshot_file" || t === "file_activity") return { path: "" }
        return {}
    }
    function setParam(k, v) { var p = {}; for (var x in draft.params) p[x] = draft.params[x]; p[k] = v; setDraft("params", p) }
    function setDraft(k, v) { var d = {}; for (var x in draft) d[x] = draft[x]; d[k] = v; draft = d; dirty = true; if (sel && sel.id) autosave() }
    // what the chosen action still needs before it can be saved
    readonly property var missing: {
        if (!sel || sel.kind === "custom") return []
        var need = (builtin[sel.builtin_type] || { params: [] }).params
        return need.filter(function (n) { var v = draft.params ? draft.params[n] : undefined; return v === undefined || v === null || String(v).trim() === "" })
    }
    // a stored action saves as it is changed (a moment after the last change), once nothing is missing
    Timer { id: saveSoon; interval: 700; onTriggered: root.saveNow() }
    function autosave() { if (missing.length === 0) saveSoon.restart() }
    function saveNow() {
        if (!sel) return
        if (sel.id) {
            falcon.call("control.action_update", { action_id: sel.id, params: draft.params, timeout_s: draft.timeout_seconds,
                                                   timing: draft.timing, name: draft.name }, function (ok, r) {
                if (!ok) { shell.notify(r.message, true); return }
                root.dirty = false
                shell.notify("Saved", false)
            })
            return
        }
        falcon.call("control.action_create", { kind: sel.kind, builtin_type: sel.builtin_type, params: draft.params, name: draft.name,
                                               timeout_s: draft.timeout_seconds, timing: draft.timing }, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            shell.notify(Automate.actionName(r.action) + " is in the library", false)
            root.sel = r.action
            root.refresh()
        })
    }

    // --- machines and trying one --------------------------------------------------------------------------
    readonly property var machines: {
        var out = []
        for (var i = 0; i < tree.length; i++)
            for (var j = 0; j < tree[i].workers.length; j++) if (tree[i].workers[j].pc_id) out.push(tree[i].workers[j])
        return out
    }
    function machineOf(pcId) { return machines.filter(function (m) { return m.pc_id === pcId })[0] || null }
    function tryIt() {
        falcon.call("control.action_run", { action_id: sel.id, pc_id: tryPc }, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            var e = r.executions[0]
            root.trial = { execution_id: e.execution_id, hostname: e.hostname, status: e.execution_id ? "pending" : "delayed", output: [],
                           at: Qt.formatDateTime(new Date(), "HH:mm") }
        })
    }
    function readTrial() {
        if (!trial || !trial.execution_id) return
        falcon.call("control.execution", { execution_id: trial.execution_id }, function (ok, r) {
            if (!ok) return
            var t = {}; for (var k in root.trial) t[k] = root.trial[k]
            t.status = r.execution.status; t.terminated_reason = r.execution.terminated_reason; t.output = r.output
            root.trial = t
        })
    }

    // --- a custom action ---------------------------------------------------------------------------------
    property string scriptPath: ""
    property string scriptText: ""
    property var check: null                 // {ok, problems}
    property string customName: ""
    property string customDoes: ""
    readonly property string language: /\.ps1$/i.test(scriptPath) ? "powershell" : "python"
    function newCustom() {
        mode = "custom"; sel = null; scriptPath = ""; scriptText = ""; check = null; customName = ""; customDoes = ""
        draft = { timeout_seconds: 60, timing: { mode: "immediate" }, params: {} }
        trial = null
    }
    function takeScript(url) {
        var path = decodeURIComponent(String(url).replace(/^file:\/{2,3}/, ""))
        if (!/\.(py|ps1)$/i.test(path)) { shell.notify("A script is a .py or .ps1 file", true); return }
        var text = falcon.readFile(path)
        if (text.indexOf("__error__:") === 0) { shell.notify(text.substring(10), true); return }
        scriptPath = path
        scriptText = text
        check = falcon.validateScript(language, text)
        if (!customName) {
            var base = path.replace(/\\/g, "/").split("/").pop().replace(/\.(py|ps1)$/i, "").replace(/[_-]+/g, " ")
            customName = base.charAt(0).toUpperCase() + base.slice(1)
        }
    }
    function saveCustom() {
        falcon.call("control.action_create", { kind: "custom", name: customName, language: language, script: scriptText,
                                               description: customDoes, timeout_s: draft.timeout_seconds, timing: draft.timing }, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            shell.notify(customName + " is in the library", false)
            root.refresh()
            root.choose(r.action)
        })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 22
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 16

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Column {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4
                Row {
                    spacing: 6
                    Txt { text: "Actions"; color: root.mode === "library" ? "#ffffff" : Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody
                          font.weight: root.mode === "library" ? Font.DemiBold : Font.Normal
                          MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: root.mode = "library" } }
                    Icon { visible: root.mode === "custom"; name: "chev"; color: Qt.rgba(1, 1, 1, 0.45); size: 12; anchors.verticalCenter: parent.verticalCenter }
                    Txt { visible: root.mode === "custom"; text: "New custom action"; color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                }
                Row {
                    spacing: 12
                    Txt { text: root.mode === "custom" ? "New custom action" : "Actions"; color: "#ffffff"; font.pixelSize: Theme.fTitle; font.weight: Font.Bold
                          anchors.verticalCenter: parent.verticalCenter }
                    Txt { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody
                          color: root.mode === "custom" ? Theme.warn : Qt.rgba(1, 1, 1, 0.55)
                          text: root.mode === "custom" ? "your own script" : root.actions.length + " in the library" }
                }
            }
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 16
                TBtn { objectName: "newCustomButton"; visible: root.mode === "library" && (falcon && falcon.role === "admin"); text: "New custom action"; iconName: "plus"
                       onClicked: root.newCustom() }
                Txt { text: root.mode === "library" ? root.clock : "Esc to go back"; color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody
                      anchors.verticalCenter: parent.verticalCenter }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            // ================================================================================================
            // the library (AU05) -- or, for a custom action, the script (AU07)
            GridCell {
                objectName: "actionsLibrary"
                visible: root.mode === "library"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "The library"
                narration: ({ brief: "grouped, with what each does", state: "ok" })
                // the library pages by its bottom edge -- a stack of rows in a fixed cell is paged, never
                // scrolled (PATTERNS 3, vertical). One flat model so every row keeps the same pitch.
                PagedColumn {
                    objectName: "actionsLibraryRows"
                    width: parent.width
                    height: libCell.room
                    itemHeight: 35
                    spacing: 0
                    step: 4
                    model: root.libraryRows
                    delegate: Item {
                        property var modelData: null
                        readonly property bool isHead: modelData && modelData.head !== undefined
                        readonly property bool isNote: modelData && modelData.note !== undefined
                        Row {
                            visible: isHead
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 6
                            width: parent.width
                            Txt { text: modelData && modelData.head ? modelData.head : ""
                                  color: modelData && modelData.head === "CUSTOM" ? Theme.warn
                                         : modelData && modelData.head === "MONITORING" ? Theme.ok : Theme.accent
                                  font.pixelSize: Theme.fMeta; font.weight: Font.Bold }
                            Item { width: parent.width - 120; height: 1 }
                            Txt { text: modelData && modelData.count !== undefined ? String(modelData.count) : ""
                                  color: Theme.faint; font.pixelSize: Theme.fMeta }
                        }
                        Txt {
                            visible: isNote
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width
                            text: modelData && modelData.note ? modelData.note : ""
                            color: Theme.faint; font.pixelSize: Theme.fMeta
                            wrapMode: Text.WordWrap; elide: Text.ElideRight
                        }
                        LibRow {
                            visible: !isHead && !isNote
                            width: parent.width
                            action: modelData && modelData.action ? modelData.action : null
                        }
                    }
                }
                id: libCell
            }

            GridCell {
                id: scriptCell
                objectName: "customScript"
                visible: root.mode === "custom"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "Your script"
                narration: ({ brief: !root.check ? "a .py or .ps1 file" : root.check.ok ? "checked, passed" : "checked, refused",
                              tone: !root.check ? "" : root.check.ok ? "ok" : "danger", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 14
                    Rectangle {
                        width: parent.width; height: 190; radius: 14
                        color: drop.containsDrag ? Theme.accentSoft : "transparent"
                        border.width: 1.2; border.color: drop.containsDrag ? Theme.accent : Theme.line2
                        DropArea { id: drop; anchors.fill: parent; onDropped: function (d) { if (d.hasUrls) root.takeScript(d.urls[0]) } }
                        Column {
                            anchors.centerIn: parent
                            spacing: 8
                            Rectangle { width: 44; height: 44; radius: 12; color: Theme.warnSoft; anchors.horizontalCenter: parent.horizontalCenter
                                        Icon { anchors.centerIn: parent; name: "terminal"; size: 20; color: Theme.warn } }
                            Txt { anchors.horizontalCenter: parent.horizontalCenter; color: Theme.ink; font.pixelSize: Theme.fRow; font.weight: Font.DemiBold
                                  text: root.scriptPath ? root.scriptPath.replace(/\\/g, "/").split("/").pop() : "Drop a script here" }
                            Txt { anchors.horizontalCenter: parent.horizontalCenter; color: Theme.faint; font.pixelSize: Theme.fMeta
                                  text: root.scriptPath ? (root.language === "powershell" ? "PowerShell" : "Python") + " · "
                                                          + root.scriptText.split("\n").length + " lines · drop another to replace it"
                                                        : "a .py or .ps1 file" }
                            GBtn { anchors.horizontalCenter: parent.horizontalCenter; text: "Choose a file"; small: true; onClicked: picker.open() }
                        }
                        FileDialog { id: picker; nameFilters: ["Scripts (*.py *.ps1)"]; onAccepted: root.takeScript(selectedFile) }
                    }
                    Txt { visible: root.check !== null; text: "Checked before it is saved"; color: Theme.dim; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
                    Repeater {
                        model: !root.check ? [] : root.check.ok
                               ? ["Uses only parts of Windows and the language that are allowed", "Reads cleanly; nothing in it is broken",
                                  "Checked again on each machine when it arrives"]
                               : root.check.problems
                        delegate: Row {
                            required property var modelData
                            spacing: 9
                            Icon { name: root.check.ok ? "check" : "x"; size: 13; color: root.check.ok ? Theme.ok : Theme.danger; anchors.verticalCenter: parent.verticalCenter }
                            Txt { text: modelData; width: scriptCell.width - 90; wrapMode: Text.WordWrap; font.pixelSize: Theme.fBody
                                  color: root.check.ok ? Theme.ok : Theme.danger }
                        }
                    }
                    Rectangle {
                        width: parent.width; height: warnText.implicitHeight + 26; radius: 10; color: Theme.warnSoft
                        Txt { id: warnText; anchors.fill: parent; anchors.margins: 13; wrapMode: Text.WordWrap; color: Theme.warn; font.pixelSize: Theme.fBody
                              text: "It runs on the machine with no fence around it. Only add scripts you trust, and try it on one machine first." }
                    }
                }
            }

            // ================================================================================================
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                spacing: 20

                // its settings (AU06) -- or, for a custom one, about it
                GridCell {
                    objectName: "actionSettings"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    topAlign: true
                    title: root.mode === "custom" ? "About it" : "Its settings"
                    narration: ({ brief: root.mode === "custom" ? "how it shows in the library" : "only what this action needs", tone: "accent",
                                  state: root.mode === "custom" || root.sel ? "ok" : "empty", note: "Nothing chosen", sentence: "Pick an action in the library." })
                    Column {
                        visible: root.mode === "library" && root.sel !== null
                        width: parent.width
                        spacing: 12
                        Item {
                            width: parent.width; height: 44
                            Rectangle { id: selIcon; width: 38; height: 38; radius: 10; color: Qt.rgba(1, 1, 1, 0.05); anchors.verticalCenter: parent.verticalCenter
                                        Icon { anchors.centerIn: parent; name: Automate.actionIcon(root.sel); size: 18; color: Theme.ink } }
                            Column {
                                anchors.left: selIcon.right; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter
                                spacing: 2
                                Txt { text: Automate.actionName(root.sel); color: Theme.ink; font.pixelSize: Theme.fSection; font.weight: Font.DemiBold }
                                Txt { color: Theme.faint; font.pixelSize: Theme.fMeta
                                      text: !root.sel ? "" : (root.sel.kind.charAt(0).toUpperCase() + root.sel.kind.slice(1)) + " · "
                                            + (!root.sel.id ? "not set up yet" : root.usedIn(root.sel.id) === 0 ? "in no automation yet"
                                               : "used in " + root.usedIn(root.sel.id) + (root.usedIn(root.sel.id) === 1 ? " automation" : " automations")) }
                            }
                            GBtn { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; visible: root.sel && root.sel.id; text: "Archive"; small: true
                                   onClicked: falcon.call("control.action_delete", { action_id: root.sel.id }, function (ok, r) {
                                       shell.notify(ok ? "Archived" : r.message, !ok); if (ok) { root.sel = null; root.refresh() } }) }
                        }
                        Needs { width: parent.width }
                        Row {
                            visible: root.sel && !root.sel.id
                            spacing: 10
                            TBtn { objectName: "setUpAction"; text: "Set it up"; iconName: "check"; enabled: root.missing.length === 0; onClicked: root.saveNow() }
                            Txt { anchors.verticalCenter: parent.verticalCenter; color: Theme.faint; font.pixelSize: Theme.fMeta
                                  text: root.missing.length ? "Fill in what it needs first." : "It joins the library, ready for any automation." }
                        }
                        Txt { visible: root.sel && root.sel.id && root.missing.length > 0; color: Theme.warn; font.pixelSize: Theme.fMeta
                              text: "Not saved: it still needs something above." }
                    }
                    Column {
                        visible: root.mode === "custom"
                        width: parent.width
                        spacing: 8
                        Txt { text: "Name"; color: Theme.faint; font.pixelSize: Theme.fMeta }
                        Field { width: parent.width; text: root.customName; placeholderText: "what it is called in the library"
                                    onTextEdited: root.customName = text }
                        Txt { text: "What it does, in a line"; color: Theme.faint; font.pixelSize: Theme.fMeta }
                        Field { width: parent.width; text: root.customDoes; placeholderText: "e.g. Empties the temp folders to free disk space."
                                    onTextEdited: root.customDoes = text }
                        Row { spacing: 8
                              Txt { text: "It goes in"; color: Theme.faint; font.pixelSize: Theme.fMeta; anchors.verticalCenter: parent.verticalCenter }
                              Rectangle { width: cg.implicitWidth + 14; height: 22; radius: 6; color: Theme.warnSoft
                                          Txt { id: cg; anchors.centerIn: parent; text: "Custom"; color: Theme.warn; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold } } }
                        Item { width: 1; height: 8 }
                        Row { spacing: 8
                              GBtn { text: "Cancel"; onClicked: root.mode = "library" }
                              TBtn { objectName: "saveCustom"; text: "Add to the library"; iconName: "check"
                                     enabled: root.check !== null && root.check.ok && root.customName.trim() !== ""; onClicked: root.saveCustom() } }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 310
                    Layout.maximumHeight: 310
                    Layout.fillHeight: false
                    spacing: 20
                    // when it runs
                    GridCell {
                        objectName: "actionWhen"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.fillHeight: true
                        topAlign: true
                        title: "When it runs"
                        narration: ({ brief: root.draft.timing && root.draft.timing.mode === "delayed" ? "after " + Automate.minutes(root.draft.timing.delay_s) : "right away",
                                      state: root.mode === "custom" || root.sel ? "ok" : "empty" })
                        Column {
                            width: parent.width
                            spacing: 8
                            Radio { title: "Right away"; sub: "as soon as it is started"; on: !root.draft.timing || root.draft.timing.mode !== "delayed"
                                    onPicked: root.setDraft("timing", { mode: "immediate" }) }
                            Radio { title: "After a wait"; sub: "then it runs once"; on: !!root.draft.timing && root.draft.timing.mode === "delayed"
                                    onPicked: root.setDraft("timing", { mode: "delayed", delay_s: 60 }) }
                            Row {
                                visible: !!root.draft.timing && root.draft.timing.mode === "delayed"
                                x: 30; spacing: 4
                                Repeater { model: [30, 60, 300, 900]
                                           delegate: Chip { required property var modelData; text: Automate.minutes(modelData)
                                                            on: !!root.draft.timing && root.draft.timing.delay_s === modelData
                                                            onPicked: root.setDraft("timing", { mode: "delayed", delay_s: modelData }) } }
                            }
                            Radio { title: "On a schedule"; sub: "that is an automation with a time"; on: false
                                    onPicked: shell.show("automation") }
                            Rectangle { width: parent.width; height: 1; color: Theme.line }
                            Row {
                                spacing: 4
                                Txt { text: "Give up after"; color: Theme.faint; font.pixelSize: Theme.fMeta; anchors.verticalCenter: parent.verticalCenter; rightPadding: 6 }
                                Repeater { model: [30, 60, 300, 900]
                                           delegate: Chip { required property var modelData; text: Automate.minutes(modelData)
                                                            on: root.draft.timeout_seconds === modelData; onPicked: root.setDraft("timeout_seconds", modelData) } }
                            }
                            Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta
                                  text: "Giving up is reported as timed out, not as failed." }
                        }
                    }
                    // try it on one machine
                    GridCell {
                        objectName: "actionTry"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.fillHeight: true
                        topAlign: true
                        title: "Try it on one machine"
                        narration: ({ brief: root.trial ? "last tried " + root.trial.at : "not tried yet", tone: root.trial ? "ok" : "warn",
                                      state: root.mode === "custom" || root.sel ? "ok" : "empty" })
                        Column {
                            width: parent.width
                            spacing: 10
                            Txt { text: "See it work before an automation relies on it."; color: Theme.dim; font.pixelSize: Theme.fBody }
                            Row {
                                spacing: 8
                                Txt { text: "On"; color: Theme.faint; font.pixelSize: Theme.fBody; anchors.verticalCenter: parent.verticalCenter }
                                SentenceSlot {
                                    text: root.machineOf(root.tryPc) ? root.machineOf(root.tryPc).hostname + "  " + root.machineOf(root.tryPc).name : "a machine"
                                    onClicked: tryMenu.open()
                                    Menu { id: tryMenu; y: parent.height + 4
                                           Repeater { model: root.machines
                                                      delegate: MenuItem { required property var modelData; text: modelData.hostname + "  ·  " + modelData.name
                                                                           onTriggered: root.tryPc = modelData.pc_id } } }
                                }
                            }
                            TBtn { objectName: "tryAction"; text: root.sel && root.sel.id ? "Run " + Automate.actionName(root.sel).toLowerCase() + " now" : "Run it now"
                                   iconName: "play"; enabled: root.mode === "library" && root.sel && root.sel.id && root.tryPc > 0 && !root.dirty
                                   onClicked: root.tryIt() }
                            Txt { visible: !(root.sel && root.sel.id) || root.mode === "custom"; color: Theme.faint; font.pixelSize: Theme.fMeta
                                  text: "Save it to the library first." }
                            Rectangle { visible: root.trial !== null; width: parent.width; height: 1; color: Theme.line }
                            Row {
                                visible: root.trial !== null
                                spacing: 8
                                Icon { name: !root.trial ? "check" : root.trial.status === "success" ? "check" : root.trial.status === "pending" ? "clock" : "warn"; size: 14
                                       color: !root.trial ? Theme.ok : root.trial.status === "success" ? Theme.ok : root.trial.status === "pending" ? Theme.accent : Theme.warn
                                       anchors.verticalCenter: parent.verticalCenter }
                                Txt { font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                                      color: !root.trial ? Theme.ok : root.trial.status === "success" ? Theme.ok : root.trial.status === "pending" ? Theme.accent : Theme.warn
                                      text: !root.trial ? "" : root.trial.status === "delayed" ? "Waiting its turn on " + root.trial.hostname
                                            : (Automate.outcome({ status: root.trial.status, terminated_reason: root.trial.terminated_reason,
                                                                  builtin_type: root.sel ? root.sel.builtin_type : "", action_name: root.sel ? root.sel.name : "" })
                                               + " on " + root.trial.hostname).replace(/^./, function (c) { return c.toUpperCase() }) }
                            }
                            Txt { visible: root.trial !== null && root.trial.output.length > 0; width: parent.width; wrapMode: Text.WordWrap
                                  color: Theme.faint; font.pixelSize: Theme.fMeta; text: root.trial ? root.trial.output.slice(-3).join("\n") : "" }
                        }
                    }
                }
            }
        }
    }

    // --- parts -------------------------------------------------------------------------------------------

    component LibRow: Item {
        id: lr
        property var action: null
        readonly property bool picked: root.sel !== null && action !== null && root.mode === "library"
                                       && (action.id ? root.sel.id === action.id : (!root.sel.id && root.sel.builtin_type === action.builtin_type))
        height: 35
        Rectangle { anchors.fill: parent; anchors.leftMargin: -8; anchors.rightMargin: -8; radius: 8
                    color: lr.picked ? Theme.accentSoft : lrArea.containsMouse ? Qt.rgba(1, 1, 1, 0.04) : "transparent" }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line; visible: !lr.picked }
        Icon { id: lrIcon; anchors.verticalCenter: parent.verticalCenter; name: Automate.actionIcon(lr.action); size: 15
               color: lr.action && !lr.action.id ? Theme.faint : Theme.dim }
        Txt { x: 28; anchors.verticalCenter: parent.verticalCenter; text: Automate.actionName(lr.action); font.pixelSize: Theme.fBody
              font.weight: Font.DemiBold; color: lr.action && !lr.action.id ? Theme.faint : Theme.ink }
        Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fMeta
              text: lr.action && !lr.action.id ? "not set up · " + Automate.actionDoes(lr.action) : Automate.actionDoes(lr.action)
              color: lr.picked ? Theme.ink : Theme.faint }
        MouseArea { id: lrArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.choose(lr.action) }
    }

    component Chip: Rectangle {
        id: ch
        property string text: ""
        property bool on: false
        signal picked()
        width: chT.implicitWidth + 16; height: 26; radius: 7
        color: on ? Theme.accentSoft : "transparent"
        Txt { id: chT; anchors.centerIn: parent; text: ch.text; font.pixelSize: Theme.fMeta; font.weight: ch.on ? Font.DemiBold : Font.Normal
              color: ch.on ? Theme.accent : Theme.dim }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: ch.picked() }
    }

    component Radio: Item {
        id: rd
        property string title: ""
        property string sub: ""
        property bool on: false
        signal picked()
        width: parent ? parent.width : 200; height: 42
        Rectangle { id: dot; width: 18; height: 18; radius: 9; anchors.verticalCenter: parent.verticalCenter
                    color: rd.on ? Theme.accentSoft : "transparent"; border.width: 1.2; border.color: rd.on ? Theme.accent : Theme.line2
                    Rectangle { anchors.centerIn: parent; width: 7; height: 7; radius: 4; color: Theme.accent; visible: rd.on } }
        Column { anchors.left: dot.right; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 1
                 Txt { text: rd.title; color: rd.on ? Theme.ink : Theme.dim; font.pixelSize: Theme.fBody; font.weight: rd.on ? Font.DemiBold : Font.Normal }
                 Txt { text: rd.sub; color: Theme.faint; font.pixelSize: Theme.fMeta } }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: rd.picked() }
    }

    // what the chosen action needs (AU06): each need with the control it calls for, nothing more
    component Needs: Column {
        id: nd
        readonly property string t: root.sel ? root.sel.builtin_type || "" : ""
        readonly property var p: root.draft.params || {}
        spacing: 10

        // Notify: a message
        Txt { visible: nd.t === "notify"; text: "What it says"; color: Theme.faint; font.pixelSize: Theme.fMeta }
        Field { visible: nd.t === "notify"; width: nd.width; text: nd.p.message || ""; placeholderText: "Please save your work; the network restarts at 18:00."
                    onTextEdited: root.setParam("message", text) }

        // Lock the screen: how long -- hidden until the Worker holds a lock for a time (ENGINE-WORK.md); the
        // Engine still requires duration_s, so the default rides along unseen
        Item {
            visible: false
            width: nd.width; height: 50
            Txt { text: "Lock it for"; color: Theme.faint; font.pixelSize: Theme.fMeta }
            Txt { anchors.right: parent.right; text: Automate.minutes(nd.p.duration_s || 900); color: Theme.accent; font.pixelSize: Theme.fMeta; font.weight: Font.Bold }
            Slider { y: 18; width: parent.width; from: 60; to: 3600; stepSize: 60; value: nd.p.duration_s || 900
                     onMoved: root.setParam("duration_s", Math.round(value)) }
        }

        // Rename, restore, snapshot a file: a file from the index
        Txt { visible: ["rename_file", "restore_file", "snapshot_file"].indexOf(nd.t) >= 0; text: "Which file"; color: Theme.faint; font.pixelSize: Theme.fMeta }
        FilePick { visible: ["rename_file", "restore_file", "snapshot_file"].indexOf(nd.t) >= 0; width: nd.width; path: nd.p.path || ""
                   onChosen: function (path) { root.setParam("path", path) } }
        Txt { visible: nd.t === "rename_file"; text: "New name"; color: Theme.faint; font.pixelSize: Theme.fMeta }
        Field { visible: nd.t === "rename_file"; width: nd.width; text: nd.p.new_name || ""; placeholderText: "budget-2026 (locked).xlsx"
                    onTextEdited: root.setParam("new_name", text) }
        Txt { visible: nd.t === "snapshot_file"; text: "A copy as it is right now, kept for the record."; color: Theme.faint; font.pixelSize: Theme.fMeta }

        // File activity: a folder from the index
        Txt { visible: nd.t === "file_activity"; text: "Which folder"; color: Theme.faint; font.pixelSize: Theme.fMeta }
        FolderPick { visible: nd.t === "file_activity"; path: nd.p.path || ""; onChosen: function (path) { root.setParam("path", path) } }

        // Close / start a program: its name
        Txt { visible: nd.t === "kill_process" || nd.t === "start_process"; text: "Which program"; color: Theme.faint; font.pixelSize: Theme.fMeta }
        Field { visible: nd.t === "kill_process"; width: nd.width; text: nd.p.name || ""; placeholderText: "its name, like excel.exe"
                    onTextEdited: root.setParam("name", text) }
        Field { visible: nd.t === "start_process"; width: nd.width; text: nd.p.command || ""; placeholderText: "its name, like calc.exe"
                    onTextEdited: root.setParam("command", text) }
        Row { visible: nd.t === "kill_process" || nd.t === "reboot" || nd.t === "shutdown"; spacing: 8
              Icon { name: "warn"; size: 14; color: Theme.danger; anchors.verticalCenter: parent.verticalCenter }
              Txt { color: Theme.danger; font.pixelSize: Theme.fBody
                    text: nd.t === "kill_process" ? "Unsaved work in it is lost." : "They get 30 seconds' warning; unsaved work on the machine is lost." } }

        // the ones that need nothing
        Column {
            visible: ["screenshot", "process_list", "system_metrics", "idle_time", "usb_contents", "reboot", "shutdown", "lock_session"].indexOf(nd.t) >= 0
            width: nd.width
            spacing: 4
            Txt { text: "Nothing to set."; color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                  visible: nd.t !== "reboot" && nd.t !== "shutdown" }
            Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fBody
                  text: "It " + Automate.actionDoes(root.sel).replace(/^what /, "reads what ") + ". The only question is when it runs." }
        }
        Txt { visible: root.sel && root.sel.kind === "custom"; width: nd.width; wrapMode: Text.WordWrap; color: Theme.dim; font.pixelSize: Theme.fBody
              text: root.sel && root.sel.description ? root.sel.description : "Your own script. It needs nothing more; change when it runs, or try it." }
    }

    // a file from the index, found by a few letters of its name -- the path is never typed
    component FilePick: Column {
        id: fp
        property string path: ""
        property var results: []
        signal chosen(string path)
        spacing: 6
        SentenceSlot { text: fp.path ? fp.path.replace(/\\/g, "/").split("/").pop() : "find a file"; dashed: !fp.path; tone: fp.path ? "accent" : "warn"
                       onClicked: findBox.visible = !findBox.visible }
        Field {
            id: findBox
            visible: !fp.path
            width: fp.width
            placeholderText: "a few letters of its name"
            onTextEdited: if (text.length >= 2) falcon.call("assistance.search", { query: text }, function (ok, r) { fp.results = ok ? r.results.slice(0, 5) : [] })
        }
        Repeater {
            model: findBox.visible ? fp.results : []
            delegate: Txt {
                required property var modelData
                width: fp.width; elide: Text.ElideMiddle; color: Theme.dim; font.pixelSize: Theme.fBody
                text: modelData.filename + "   ·   " + (root.machineOf(modelData.pc_id) ? root.machineOf(modelData.pc_id).hostname : "") + "   " + modelData.path
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { fp.chosen(modelData.path); findBox.visible = false } }
            }
        }
    }

    // a folder from the index, on a machine
    component FolderPick: Row {
        id: fo
        property string path: ""
        property var folders: []
        signal chosen(string path)
        spacing: 8
        SentenceSlot { text: fo.path ? Automate.folderName(fo.path) : "a folder"; dashed: !fo.path; tone: fo.path ? "accent" : "warn"
                       onClicked: { falcon.call("index.folders", { pc_id: root.tryPc }, function (ok, r) { fo.folders = ok ? r.folders : [] }); foMenu.open() }
                       Menu { id: foMenu; y: parent.height + 4
                              Repeater { model: fo.folders
                                         delegate: MenuItem { required property var modelData; text: modelData.name + "   (" + modelData.files + " files)"
                                                              onTriggered: fo.chosen(modelData.path) } } } }
        Txt { text: "as found on " + (root.machineOf(root.tryPc) ? root.machineOf(root.tryPc).hostname : "a machine"); color: Theme.faint
              font.pixelSize: Theme.fMeta; anchors.verticalCenter: parent.verticalCenter }
    }
}
