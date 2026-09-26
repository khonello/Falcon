import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Actions: the library (built-in + custom), running one now, and making a new one. Its own page on
// the Admin's rail -- Automation no longer carries an Actions tab (the user, 26 Sep 2026: "we have an
// action page"). Automation's events refer to these by name, from a picker.
Item {
    id: view
    property var builtin: ({})
    property var actions: []        // flattened: [{id, kind, name, builtin_type, ...}]

    function refresh() {
        falcon.call("control.action_list", {}, function(ok, r) {
            if (!ok) { root.notify(r.message, true); return }
            view.builtin = r.builtin
            var flat = []
            ;["control", "monitoring", "custom"].forEach(function(k) { r.actions[k].forEach(function(a) { a.kind = k; flat.push(a) }) })
            view.actions = flat
        })
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Connections {
        target: falcon
        function onConnected() { view.refresh() }
        function onScopeChanged() { if (falcon.isConnected) view.refresh() }
        function onPushReceived(type, p) { if (type.indexOf("control.action") === 0) view.refresh() }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8
        RowLayout {
            Label { text: "Actions"; font.pixelSize: Theme.fontLarge; color: Theme.text }
            Item { Layout.fillWidth: true }
            Btn { text: "Refresh"; onClicked: view.refresh() }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 10
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                DataTable { id: actionTable; Layout.fillWidth: true; Layout.fillHeight: true; rows: view.actions
                            columns: ["id", "kind", "name", "builtin_type", "params", "timeout_seconds", "timing", "custom_script_language"]
                            widths: ({id: 50, kind: 90, name: 160, builtin_type: 150, params: 220, timeout_seconds: 60, timing: 130, custom_script_language: 80}) }
                RowLayout {
                    Label { text: actionTable.selectedIndex >= 0 ? "run action " + view.actions[actionTable.selectedIndex].id + " on" : "select an action to run"; color: Theme.textDim }
                    Field { id: runPc; Layout.preferredWidth: 70; placeholderText: "pc id" }
                    Eyebrow { label: "or department" }
                    Field { id: runDept; Layout.preferredWidth: 70; placeholderText: "dept id" }
                    Btn { text: "Run now"; enabled: actionTable.selectedIndex >= 0 && (runPc.text.length > 0 || runDept.text.length > 0)
                             onClicked: { var p = {action_id: view.actions[actionTable.selectedIndex].id}
                                          if (runDept.text) p.department_id = parseInt(runDept.text); else p.pc_id = parseInt(runPc.text)
                                          falcon.call("control.action_run", p, function(ok, r) {
                                              if (!ok) { root.notify(r.message, true); return }
                                              root.notify("started: " + r.executions.map(function(e) { return e.hostname + " (exec " + (e.execution_id || "delayed") + ")" }).join(", "), false); view.refresh() }) } }
                    Btn { text: "Archive"; enabled: actionTable.selectedIndex >= 0
                             onClicked: falcon.call("control.action_delete", {action_id: view.actions[actionTable.selectedIndex].id}, function(ok, r) { root.notify(ok ? "action " + r.action_id + " archived" : r.message, !ok); actionTable.selectedIndex = -1; view.refresh() }) }
                }
            }
            // create
            Rectangle {
                Layout.preferredWidth: 400; Layout.fillHeight: true; color: Theme.surface; radius: Theme.radius; border.width: 1; border.color: Theme.border
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 10; spacing: 6
                    Label { text: "New action"; color: Theme.text; font.bold: true }
                    RowLayout {
                        Picker { id: newKind; model: ["control", "monitoring", "custom"]; Layout.preferredWidth: 120 }
                        Field { id: newName; Layout.fillWidth: true; placeholderText: "name" + (newKind.currentText === "custom" ? " (required)" : "") }
                    }
                    Picker { id: newBuiltin; Layout.fillWidth: true; visible: newKind.currentText !== "custom"
                               model: Object.keys(view.builtin).filter(function(k) { return view.builtin[k].category === newKind.currentText }) }
                    Label { visible: newBuiltin.visible && newBuiltin.currentText; color: Theme.textDim; wrapMode: Text.Wrap; Layout.fillWidth: true
                            text: newBuiltin.currentText && view.builtin[newBuiltin.currentText] ? "params: " + (view.builtin[newBuiltin.currentText].params.join(", ") || "-") : "" }
                    Field { id: newParams; Layout.fillWidth: true; visible: newKind.currentText !== "custom"; placeholderText: "params k=v,k2=v2" }
                    RowLayout { visible: newKind.currentText === "custom"
                        Picker { id: newLang; model: ["python", "powershell"]; Layout.preferredWidth: 120 }
                        Field { id: scriptPath; Layout.fillWidth: true; placeholderText: "script file path" }
                        Btn { text: "Load"; onClicked: { var s = falcon.readFile(scriptPath.text); if (s.indexOf("__error__:") === 0) root.notify(s.substring(10), true); else script.text = s } }
                    }
                    TextArea { id: script; Layout.fillWidth: true; Layout.preferredHeight: 160; visible: newKind.currentText === "custom"; font.family: Theme.mono; placeholderText: "script source (stdlib + Windows-native only)"; wrapMode: TextEdit.NoWrap }
                    RowLayout {
                        Eyebrow { label: "timeout s" } Field { id: newTimeout; Layout.preferredWidth: 50; text: "60" }
                        Eyebrow { label: "delay s" } Field { id: newDelay; Layout.preferredWidth: 50; placeholderText: "-" }
                        Item { Layout.fillWidth: true }
                        Btn { text: "Create"
                                 enabled: newKind.currentText === "custom" ? (newName.text.length > 0 && script.text.length > 0) : newBuiltin.currentText.length > 0
                                 onClicked: view.createAction() }
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }
    }

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
}
