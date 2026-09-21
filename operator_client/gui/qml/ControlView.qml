import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Automation: the action library (built-in + custom), event definitions, the dashboard of
// enabled automations with their recent executions, and live runs with output + terminate.
Item {
    id: view
    property var builtin: ({})
    property var actions: []        // flattened: [{id, kind, name, builtin_type, ...}]
    property var events: []
    property var eventTypes: []
    property var automations: []
    property var live: []
    property var execution: null
    property var output: []

    function refresh() {
        falcon.call("control.action_list", {}, function(ok, r) {
            if (!ok) { root.notify(r.message, true); return }
            view.builtin = r.builtin
            var flat = []
            ;["control", "monitoring", "custom"].forEach(function(k) { r.actions[k].forEach(function(a) { a.kind = k; flat.push(a) }) })
            view.actions = flat
        })
        falcon.call("control.event_list", {}, function(ok, r) {
            if (!ok) return
            view.eventTypes = r.types.slice().sort()
            view.events = r.events.map(function(e) { return {id: e.id, type: e.condition_spec.type, mechanism: e.condition_type, enabled: e.enabled,
                                                            pcs: e.condition_spec.pc_ids || "dept", match: e.condition_spec.match,
                                                            actions: e.actions.map(function(a) { return a.name || a.id }), last_fired: e.last_fired_at} })
        })
        falcon.call("control.dashboard", {}, function(ok, r) { if (ok) { view.automations = r.automations; view.live = r.live } })
    }
    function openExec(id) {
        falcon.call("control.execution", {execution_id: id}, function(ok, r) { if (ok) { view.execution = r.execution; view.output = r.output } else root.notify(r.message, true) })
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Connections {
        target: falcon
        function onConnected() { view.refresh() }
        function onPushReceived(type, p) {
            if (type.indexOf("control.") === 0) { view.refresh(); if (view.execution && p.execution_id === view.execution.id) view.openExec(view.execution.id) }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8
        RowLayout {
            Label { text: "Automation"; font.pixelSize: 18; color: "white" }
            TabBar { id: tabs; Layout.fillWidth: true
                     TabButton { text: "Dashboard" } TabButton { text: "Actions" } TabButton { text: "Events" } TabButton { text: "Executions" } }
            Button { text: "Refresh"; onClicked: view.refresh() }
        }

        StackLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            // --- dashboard
            ColumnLayout {
                Label { text: "enabled automations"; color: "#9aa" }
                ListView {
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6
                    model: view.automations
                    delegate: Rectangle {
                        required property var modelData
                        width: ListView.view.width
                        height: col.implicitHeight + 12
                        color: "#26282c"; radius: 4
                        ColumnLayout {
                            id: col; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 6; spacing: 2
                            Label { text: "Event " + modelData.event.id + ": " + modelData.event.condition_spec.type + "   (last: " + (modelData.last_fired_at || "never") + ")"; color: "#ffd166"; font.bold: true }
                            Repeater {
                                model: modelData.actions
                                delegate: Label {
                                    required property var modelData
                                    color: "#ddd"
                                    text: {
                                        var act = modelData.action, last = modelData.recent.length ? modelData.recent[0] : null
                                        var status = last ? last.status.toUpperCase() + (last.terminated_reason ? " (" + last.terminated_reason + ")" : "") : "never run"
                                        return "  ├─ " + (act.name || act.builtin_type) + " [" + act.action_kind + "] -> " + status
                                             + (last && last.output.length ? "\n  │     " + last.output.slice(-3).join("\n  │     ") : "")
                                    }
                                }
                            }
                        }
                    }
                    Label { anchors.centerIn: parent; visible: view.automations.length === 0; text: "(no enabled automations)"; color: "#777" }
                }
                Label { text: "live executions"; color: "#9aa" }
                DataTable { Layout.fillWidth: true; Layout.preferredHeight: 120; rows: view.live
                            columns: ["id", "action_id", "builtin_type", "target_pc_id", "started_at"]; widths: ({id: 60, action_id: 70, builtin_type: 160, target_pc_id: 80, started_at: 140})
                            onRowClicked: function(row) { view.openExec(row.id); tabs.currentIndex = 3 } }
            }

            // --- actions
            RowLayout {
                spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    DataTable { id: actionTable; Layout.fillWidth: true; Layout.fillHeight: true; rows: view.actions
                                columns: ["id", "kind", "name", "builtin_type", "params", "timeout_seconds", "timing", "custom_script_language"]
                                widths: ({id: 50, kind: 90, name: 160, builtin_type: 150, params: 220, timeout_seconds: 60, timing: 130, custom_script_language: 80}) }
                    RowLayout {
                        Label { text: actionTable.selectedIndex >= 0 ? "run action " + view.actions[actionTable.selectedIndex].id + " on" : "select an action to run"; color: "#ccc" }
                        TextField { id: runPc; Layout.preferredWidth: 70; placeholderText: "pc id" }
                        Label { text: "or department"; color: "#ccc" }
                        TextField { id: runDept; Layout.preferredWidth: 70; placeholderText: "dept id" }
                        Button { text: "Run now"; enabled: actionTable.selectedIndex >= 0 && (runPc.text.length > 0 || runDept.text.length > 0)
                                 onClicked: { var p = {action_id: view.actions[actionTable.selectedIndex].id}
                                              if (runDept.text) p.department_id = parseInt(runDept.text); else p.pc_id = parseInt(runPc.text)
                                              falcon.call("control.action_run", p, function(ok, r) {
                                                  if (!ok) { root.notify(r.message, true); return }
                                                  root.notify("started: " + r.executions.map(function(e) { return e.hostname + " (exec " + (e.execution_id || "delayed") + ")" }).join(", "), false); view.refresh() }) } }
                        Button { text: "Archive"; enabled: actionTable.selectedIndex >= 0
                                 onClicked: falcon.call("control.action_delete", {action_id: view.actions[actionTable.selectedIndex].id}, function(ok, r) { root.notify(ok ? "action " + r.action_id + " archived" : r.message, !ok); actionTable.selectedIndex = -1; view.refresh() }) }
                    }
                }
                // create
                Rectangle {
                    Layout.preferredWidth: 400; Layout.fillHeight: true; color: "#26282c"; radius: 6
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 10; spacing: 6
                        Label { text: "New action"; color: "white"; font.bold: true }
                        RowLayout {
                            ComboBox { id: newKind; model: ["control", "monitoring", "custom"]; Layout.preferredWidth: 120 }
                            TextField { id: newName; Layout.fillWidth: true; placeholderText: "name" + (newKind.currentText === "custom" ? " (required)" : "") }
                        }
                        ComboBox { id: newBuiltin; Layout.fillWidth: true; visible: newKind.currentText !== "custom"
                                   model: Object.keys(view.builtin).filter(function(k) { return view.builtin[k].category === newKind.currentText }) }
                        Label { visible: newBuiltin.visible && newBuiltin.currentText; color: "#9aa"; wrapMode: Text.Wrap; Layout.fillWidth: true
                                text: newBuiltin.currentText && view.builtin[newBuiltin.currentText] ? "params: " + (view.builtin[newBuiltin.currentText].params.join(", ") || "-") : "" }
                        TextField { id: newParams; Layout.fillWidth: true; visible: newKind.currentText !== "custom"; placeholderText: "params k=v,k2=v2" }
                        RowLayout { visible: newKind.currentText === "custom"
                            ComboBox { id: newLang; model: ["python", "powershell"]; Layout.preferredWidth: 120 }
                            TextField { id: scriptPath; Layout.fillWidth: true; placeholderText: "script file path" }
                            Button { text: "Load"; onClicked: { var s = falcon.readFile(scriptPath.text); if (s.indexOf("__error__:") === 0) root.notify(s.substring(10), true); else script.text = s } }
                        }
                        TextArea { id: script; Layout.fillWidth: true; Layout.preferredHeight: 160; visible: newKind.currentText === "custom"; font.family: "Consolas"; placeholderText: "script source (stdlib + Windows-native only)"; wrapMode: TextEdit.NoWrap }
                        RowLayout {
                            Label { text: "timeout s"; color: "#ccc" } TextField { id: newTimeout; Layout.preferredWidth: 50; text: "60" }
                            Label { text: "delay s"; color: "#ccc" } TextField { id: newDelay; Layout.preferredWidth: 50; placeholderText: "-" }
                            Item { Layout.fillWidth: true }
                            Button { text: "Create"
                                     enabled: newKind.currentText === "custom" ? (newName.text.length > 0 && script.text.length > 0) : newBuiltin.currentText.length > 0
                                     onClicked: view.createAction() }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            // --- events
            RowLayout {
                spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    DataTable { id: eventTable; Layout.fillWidth: true; Layout.fillHeight: true; rows: view.events
                                columns: ["id", "type", "mechanism", "enabled", "pcs", "match", "actions", "last_fired"]
                                widths: ({id: 50, type: 150, mechanism: 90, enabled: 60, pcs: 100, match: 220, actions: 200, last_fired: 130}) }
                    RowLayout {
                        Button { text: "Enable"; enabled: eventTable.selectedIndex >= 0; onClicked: falcon.call("control.event_update", {event_id: view.events[eventTable.selectedIndex].id, enabled: true}, view.after) }
                        Button { text: "Disable"; enabled: eventTable.selectedIndex >= 0; onClicked: falcon.call("control.event_delete", {event_id: view.events[eventTable.selectedIndex].id}, view.after) }
                        TextField { id: evActions; Layout.preferredWidth: 120; placeholderText: "action ids 1,2" }
                        Button { text: "Set actions"; enabled: eventTable.selectedIndex >= 0 && evActions.text.length > 0
                                 onClicked: falcon.call("control.event_update", {event_id: view.events[eventTable.selectedIndex].id, action_ids: view.ints(evActions.text)}, view.after) }
                    }
                }
                Rectangle {
                    Layout.preferredWidth: 400; Layout.fillHeight: true; color: "#26282c"; radius: 6
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 10; spacing: 6
                        Label { text: "New event"; color: "white"; font.bold: true }
                        ComboBox { id: evType; Layout.fillWidth: true; model: view.eventTypes }
                        TextField { id: evNewActions; Layout.fillWidth: true; placeholderText: "action ids 1,2" }
                        TextField { id: evPcs; Layout.fillWidth: true; placeholderText: "pc ids (blank = whole department)" }
                        TextField { id: evMatch; Layout.fillWidth: true; placeholderText: "match k=v,k2=v2  e.g. path_prefix=C:/resources/restricted" }
                        RowLayout {
                            CheckBox { id: evEnabled; text: "enabled"; checked: true }
                            Item { Layout.fillWidth: true }
                            Button { text: "Create"; enabled: evType.currentText.length > 0
                                     onClicked: falcon.call("control.event_create", {type: evType.currentText, action_ids: view.ints(evNewActions.text), pc_ids: evPcs.text ? view.ints(evPcs.text) : null,
                                                                                     match: view.kv(evMatch.text, true), enabled: evEnabled.checked},
                                                            function(ok, r) { root.notify(ok ? "event " + r.event.id + " (" + r.event.condition_type + ") created" : r.message, !ok); view.refresh() }) }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            // --- executions
            ColumnLayout {
                RowLayout {
                    Label { text: "execution id"; color: "#ccc" }
                    TextField { id: execId; Layout.preferredWidth: 80; validator: IntValidator { bottom: 1 } }
                    Button { text: "Open"; enabled: execId.text.length > 0; onClicked: view.openExec(parseInt(execId.text)) }
                    Button { text: "Terminate"; enabled: !!view.execution && view.execution.status === "running"
                             onClicked: falcon.call("control.terminate", {execution_id: view.execution.id}, function(ok, r) { root.notify(ok ? "termination requested for " + r.execution_id : r.message, !ok) }) }
                    Item { Layout.fillWidth: true }
                }
                Label { visible: !!view.execution; color: "#ddd"; wrapMode: Text.Wrap; Layout.fillWidth: true; text: view.execution ? falcon.pretty(view.execution) : "" ; font.family: "Consolas" }
                Label { text: "output"; color: "#9aa" }
                ScrollView {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    TextArea { readOnly: true; font.family: "Consolas"; color: "#ddd"; text: view.output.join("\n") || "(none)"; wrapMode: TextEdit.NoWrap }
                }
            }
        }
    }

    function ints(text) { return text.split(",").map(function(s) { return parseInt(s.trim()) }).filter(function(n) { return !isNaN(n) }) }
    function kv(text, coerce) {
        var out = {}
        text.split(",").forEach(function(item) { var i = item.indexOf("="); if (i > 0) { var v = item.substring(i + 1).trim(); out[item.substring(0, i).trim()] = coerce && /^\d+$/.test(v) ? parseInt(v) : v } })
        return out
    }
    function createAction() {
        var timing = newDelay.text ? {mode: "delayed", delay_s: parseInt(newDelay.text)} : null
        var p
        if (newKind.currentText === "custom") {
            var v = falcon.validateScript(newLang.currentText, script.text)
            if (!v.ok) { root.notify("script rejected before sending: " + v.problems.join("; "), true); return }
            p = {kind: "custom", name: newName.text, language: newLang.currentText, script: script.text, timeout_s: parseInt(newTimeout.text) || 60, description: null, timing: timing}
        } else {
            p = {kind: newKind.currentText, builtin_type: newBuiltin.currentText, params: view.kv(newParams.text, false), timeout_s: parseInt(newTimeout.text) || 60,
                 name: newName.text || null, description: null, timing: timing}
        }
        falcon.call("control.action_create", p, function(ok, r) { root.notify(ok ? "action " + r.action.id + " '" + r.action.name + "' created" : r.message, !ok); if (ok) { newName.text = ""; script.text = "" } view.refresh() })
    }
    function after(ok, r) { root.notify(ok ? falcon.pretty(r) : r.message, !ok); view.refresh() }
}
