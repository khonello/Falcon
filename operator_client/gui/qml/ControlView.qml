import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Automation: the dashboard of enabled automations with their recent executions, the event
// definitions, and live runs with output + terminate. The action LIBRARY is its own page
// (ActionsView); an event refers to actions by name, chosen from that library with ActionPicker.
Item {
    id: view
    property var actions: []        // the library, for the pickers: [{id, kind, name, builtin_type}]
    property var events: []
    property var eventTypes: []
    property var automations: []
    property var live: []
    property var execution: null
    property var output: []

    function refresh() {
        falcon.call("control.action_list", {}, function(ok, r) {
            if (!ok) { root.notify(r.message, true); return }
            var flat = []
            ;["control", "monitoring", "custom"].forEach(function(k) { r.actions[k].forEach(function(a) { a.kind = k; flat.push(a) }) })
            view.actions = flat
        })
        falcon.call("control.event_list", {}, function(ok, r) {
            if (!ok) return
            view.eventTypes = r.types.slice().sort()
            view.events = r.events.map(function(e) { return {id: e.id, type: e.condition_spec.type, mechanism: e.condition_type, enabled: e.enabled,
                                                            pcs: e.condition_spec.pc_ids || "dept", match: e.condition_spec.match,
                                                            actions: e.actions.map(function(a) { return a.name || a.id }).join(", "),
                                                            action_ids: e.actions.map(function(a) { return a.id }), last_fired: e.last_fired_at} })
        })
        falcon.call("control.dashboard", {}, function(ok, r) { if (ok) { view.automations = r.automations || []; view.live = r.live || [] } })
    }
    function openExec(id) {
        falcon.call("control.execution", {execution_id: id}, function(ok, r) { if (ok) { view.execution = r.execution; view.output = r.output } else root.notify(r.message, true) })
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Connections {
        target: falcon
        function onConnected() { view.refresh() }
        function onScopeChanged() { if (falcon.isConnected) view.refresh() }
        function onPushReceived(type, p) {
            if (type.indexOf("control.") === 0) { view.refresh(); if (view.execution && p.execution_id === view.execution.id) view.openExec(view.execution.id) }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8
        RowLayout {
            Label { text: "Automation"; font.pixelSize: Theme.fontLarge; color: Theme.text }
            SegmentedControl { id: tabs; objectName: "automationTabs"; Layout.leftMargin: 18; segments: [{text: "Dashboard"}, {text: "Events"}, {text: "Executions"}] }
            Btn { text: "Refresh"; onClicked: view.refresh() }
        }

        StackLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            // --- dashboard
            ColumnLayout {
                Eyebrow { label: "enabled automations" }
                ListView {
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6
                    model: view.automations
                    delegate: Rectangle {
                        required property var modelData
                        width: ListView.view.width
                        height: col.implicitHeight + 12
                        color: Theme.surface; radius: 4
                        ColumnLayout {
                            id: col; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 6; spacing: 2
                            Label { text: "Event " + modelData.event.id + ": " + modelData.event.condition_spec.type + "   (last: " + (modelData.last_fired_at || "never") + ")"; color: Theme.warn; font.bold: true }
                            Repeater {
                                model: modelData.actions
                                delegate: Label {
                                    required property var modelData
                                    color: Theme.textDim
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
                    Label { anchors.centerIn: parent; visible: view.automations.length === 0; text: "(no enabled automations)"; color: Theme.textFaint }
                }
                Eyebrow { label: "live executions" }
                DataTable { Layout.fillWidth: true; Layout.preferredHeight: 120; rows: view.live
                            columns: ["id", "action_id", "builtin_type", "target_pc_id", "started_at"]; widths: ({id: 60, action_id: 70, builtin_type: 160, target_pc_id: 80, started_at: 140})
                            onRowClicked: function(row) { view.openExec(row.id); tabs.currentIndex = 2 } }
            }

            // --- events
            RowLayout {
                spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    DataTable { id: eventTable; objectName: "eventTable"; Layout.fillWidth: true; Layout.fillHeight: true; rows: view.events
                                columns: ["id", "type", "mechanism", "enabled", "pcs", "match", "actions", "last_fired"]
                                widths: ({id: 50, type: 150, mechanism: 90, enabled: 60, pcs: 100, match: 220, actions: 200, last_fired: 130})
                                // the picker below shows what the chosen event fires, ready to change
                                onSelectedIndexChanged: editActions.selected = selectedIndex >= 0 ? view.events[selectedIndex].action_ids : [] }
                    RowLayout {
                        Btn { text: "Enable"; enabled: eventTable.selectedIndex >= 0; onClicked: falcon.call("control.event_update", {event_id: view.events[eventTable.selectedIndex].id, enabled: true}, view.after) }
                        Btn { text: "Disable"; enabled: eventTable.selectedIndex >= 0; onClicked: falcon.call("control.event_delete", {event_id: view.events[eventTable.selectedIndex].id}, view.after) }
                        Item { Layout.fillWidth: true }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: eventTable.selectedIndex >= 0
                        Eyebrow { label: "this event fires" }
                        ActionPicker { id: editActions; objectName: "eventActions"; Layout.fillWidth: true; actions: view.actions }
                        Btn { text: "Save actions"
                                 onClicked: falcon.call("control.event_update", {event_id: view.events[eventTable.selectedIndex].id, action_ids: editActions.selected}, view.after) }
                    }
                }
                Rectangle {
                    Layout.preferredWidth: 400; Layout.fillHeight: true; color: Theme.surface; radius: Theme.radius; border.width: 1; border.color: Theme.border
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 10; spacing: 6
                        Label { text: "New event"; color: Theme.text; font.bold: true }
                        Picker { id: evType; Layout.fillWidth: true; model: view.eventTypes }
                        Eyebrow { label: "fires" }
                        ActionPicker { id: evNewActions; objectName: "newEventActions"; Layout.fillWidth: true; actions: view.actions }
                        Field { id: evPcs; Layout.fillWidth: true; placeholderText: "pc ids (blank = whole department)" }
                        Field { id: evMatch; Layout.fillWidth: true; placeholderText: "match k=v,k2=v2  e.g. path_prefix=C:/resources/restricted" }
                        RowLayout {
                            CheckBox { id: evEnabled; text: "enabled"; checked: true }
                            Item { Layout.fillWidth: true }
                            Btn { text: "Create"; enabled: evType.currentText.length > 0
                                     onClicked: falcon.call("control.event_create", {type: evType.currentText, action_ids: evNewActions.selected, pc_ids: evPcs.text ? view.ints(evPcs.text) : null,
                                                                                     match: view.kv(evMatch.text, true), enabled: evEnabled.checked},
                                                            function(ok, r) { root.notify(ok ? "event " + r.event.id + " (" + r.event.condition_type + ") created" : r.message, !ok); if (ok) evNewActions.selected = []; view.refresh() }) }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            // --- executions
            ColumnLayout {
                RowLayout {
                    Eyebrow { label: "execution id" }
                    Field { id: execId; Layout.preferredWidth: 80; validator: IntValidator { bottom: 1 } }
                    Btn { text: "Open"; enabled: execId.text.length > 0; onClicked: view.openExec(parseInt(execId.text)) }
                    Btn { text: "Terminate"; enabled: !!view.execution && view.execution.status === "running"
                             onClicked: falcon.call("control.terminate", {execution_id: view.execution.id}, function(ok, r) { root.notify(ok ? "termination requested for " + r.execution_id : r.message, !ok) }) }
                    Item { Layout.fillWidth: true }
                }
                Label { visible: !!view.execution; color: Theme.textDim; wrapMode: Text.Wrap; Layout.fillWidth: true; text: view.execution ? falcon.pretty(view.execution) : "" ; font.family: Theme.mono }
                Eyebrow { label: "output" }
                ScrollView {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    TextArea { readOnly: true; font.family: Theme.mono; color: Theme.textDim; text: view.output.join("\n") || "(none)"; wrapMode: TextEdit.NoWrap }
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
    function after(ok, r) { root.notify(ok ? falcon.pretty(r) : r.message, !ok); view.refresh() }
}
