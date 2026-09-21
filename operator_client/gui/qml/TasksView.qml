import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Tasks: list / detail with the verification stack, and the propose -> review -> create editor.
// The proposal is never committed on its own: the operator reviews items, flags and the deadline.
Item {
    id: view
    property var tasks: []
    property var task: null
    property var proposal: null      // {items, flags, collisions, final_deadline, llm_available}
    property var items: []           // the working stack being edited

    function refresh() {
        falcon.call("task.list", {include_completed: showAll.checked}, function(ok, r) { if (ok) view.tasks = r.tasks; else root.notify(r.message, true) })
    }
    function open(id) {
        falcon.call("task.get", {task_id: id}, function(ok, r) { if (ok) view.task = r.task; else root.notify(r.message, true) })
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Connections {
        target: falcon
        function onConnected() { view.refresh() }
        function onPushReceived(type, p) {
            if (type.indexOf("task.") === 0) { view.refresh(); if (view.task && p.task_id === view.task.id) view.open(view.task.id) }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 10

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            RowLayout {
                Label { text: "Tasks"; font.pixelSize: Theme.fontLarge; color: Theme.text }
                CheckBox { id: showAll; text: "include completed"; onToggled: view.refresh() }
                Item { Layout.fillWidth: true }
                Btn { text: "New task"; onClicked: editor.visible = !editor.visible }
                Btn { text: "Refresh"; onClicked: view.refresh() }
            }
            DataTable {
                Layout.fillWidth: true
                Layout.preferredHeight: 240
                rows: view.tasks
                columns: ["id", "status", "assigner_name", "assignee_name", "description_raw", "verification_mode", "final_deadline_at"]
                widths: ({id: 50, status: 90, assigner_name: 110, assignee_name: 110, description_raw: 260, verification_mode: 90, final_deadline_at: 130})
                onRowClicked: function(row) { view.open(row.id) }
            }

            // detail
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Theme.surface; radius: Theme.radius; border.width: 1; border.color: Theme.border
                visible: !!view.task
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 10; spacing: 6
                    RowLayout {
                        Label { text: view.task ? "Task " + view.task.id + " — " + view.task.status + " (" + view.task.verification_mode + ")" : ""; color: Theme.text; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Btn { text: "Start (assignee)"; onClicked: falcon.call("task.start", {task_id: view.task.id}, view.after) }
                        Btn { text: "Verify complete"; onClicked: falcon.call("task.verify", {task_id: view.task.id, outcome: "complete"}, view.after) }
                        Btn { text: "Incomplete"; onClicked: falcon.call("task.verify", {task_id: view.task.id, outcome: "incomplete"}, view.after) }
                        Btn { text: "Re-evaluate stack"; onClicked: falcon.call("task.stack", {task_id: view.task.id}, function(ok, r) { view.after(ok, r); if (ok) view.open(view.task.id) }) }
                    }
                    Label { text: view.task ? view.task.description_raw : ""; color: Theme.textDim; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Label { color: Theme.textFaint; text: view.task ? ("assigned by " + view.task.assigner_name + " to " + view.task.assignee_name
                                                              + "  ·  soft " + (view.task.soft_deadline_at || "-") + "  ·  final " + (view.task.final_deadline_at || "-")) : "" }
                    Eyebrow { label: "verification stack" }
                    DataTable {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        rows: view.task ? view.task.items : []
                        columns: ["sequence", "target_type", "intent", "proposed_filename", "program_name", "file_path", "status"]
                        widths: ({sequence: 40, target_type: 80, intent: 120, proposed_filename: 160, program_name: 120, file_path: 220, status: 90})
                        emptyText: "(no verification items)"
                    }
                }
            }
            Item { Layout.fillHeight: true; visible: !view.task }
        }

        // editor: propose -> review -> create
        Rectangle {
            id: editor
            Layout.preferredWidth: 420
            Layout.fillHeight: true
            color: Theme.surface; radius: Theme.radius; border.width: 1; border.color: Theme.border
            visible: false
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 6
                Label { text: "New task"; font.pixelSize: Theme.fontMedium; color: Theme.text }
                RowLayout {
                    Eyebrow { label: "assignee account" }
                    Field { id: assignee; Layout.preferredWidth: 80; validator: IntValidator { bottom: 1 } }
                }
                TextArea { id: desc; Layout.fillWidth: true; Layout.preferredHeight: 90; placeholderText: "describe the task in plain language"; wrapMode: TextEdit.Wrap }
                RowLayout {
                    Btn { text: "Propose (local LLM)"; enabled: assignee.text.length > 0 && desc.text.length > 0
                             onClicked: falcon.call("task.propose", {description: desc.text, assignee_account_id: parseInt(assignee.text)}, view.onProposal) }
                    Label { text: view.proposal && !view.proposal.llm_available ? "LLM unavailable — manual" : ""; color: Theme.warn }
                }
                Label { text: view.proposal && view.proposal.flags.length ? "needs your decision: " + view.proposal.flags.map(view.flagText).join("; ") : ""
                        color: Theme.warn; wrapMode: Text.Wrap; Layout.fillWidth: true; visible: text.length > 0 }
                Label { text: view.proposal && view.proposal.collisions.length ? "name collisions: " + view.proposal.collisions.map(function(c) { return c.name + " exists at " + c.existing.map(function(e) { return e.path }).join(", ") }).join("; ") : ""
                        color: Theme.danger; wrapMode: Text.Wrap; Layout.fillWidth: true; visible: text.length > 0 }

                Label { text: "verification items (" + view.items.length + ")"; color: Theme.textDim }
                DataTable {
                    id: itemTable
                    Layout.fillWidth: true; Layout.preferredHeight: 150
                    rows: view.items
                    columns: ["target_type", "intent", "name", "path", "populated_by"]
                    widths: ({target_type: 70, intent: 110, name: 120, path: 90, populated_by: 60})
                    emptyText: "(empty — create with 'no verification' or add items)"
                }
                RowLayout {
                    Picker { id: newType; model: ["file", "program"]; Layout.preferredWidth: 90 }
                    Picker { id: newIntent; Layout.preferredWidth: 150
                               model: newType.currentText === "file" ? ["create", "update", "exists"] : ["used", "used_with_file", "installed_available", "closed_not_running"] }
                    Field { id: newName; Layout.fillWidth: true; placeholderText: "name" }
                    Btn { text: "+"; enabled: newName.text.length > 0
                             onClicked: { var a = view.items.slice(); a.push({target_type: newType.currentText, intent: newIntent.currentText, name: newName.text, path: null,
                                                                             linked_item_index: null, file_index_id: null, populated_by: "manual"}); view.items = a; newName.text = "" } }
                    Btn { text: "−"; enabled: itemTable.selectedIndex >= 0
                             onClicked: { var a = view.items.slice(); a.splice(itemTable.selectedIndex, 1); view.items = a; itemTable.selectedIndex = -1 } }
                }
                GridLayout {
                    columns: 3; Layout.fillWidth: true
                    Eyebrow { label: "soft deadline" }
                    Field { id: soft; Layout.fillWidth: true; placeholderText: "friday 5pm / ISO"; onEditingFinished: softResolved.text = text ? (falcon.resolveDeadline(text) || "?") : "" }
                    Label { id: softResolved; color: Theme.textDim; Layout.preferredWidth: 130 }
                    Eyebrow { label: "final deadline" }
                    Field { id: final; Layout.fillWidth: true; placeholderText: "tomorrow 3pm / ISO"; onEditingFinished: finalResolved.text = text ? (falcon.resolveDeadline(text) || "?") : "" }
                    Label { id: finalResolved; color: Theme.textDim; Layout.preferredWidth: 130 }
                }
                RowLayout {
                    Btn { text: "Create"; enabled: view.items.length > 0 && assignee.text.length > 0 && desc.text.length > 0; onClicked: view.create(false) }
                    Btn { text: "Create with no verification"; enabled: assignee.text.length > 0 && desc.text.length > 0; onClicked: view.create(true) }
                    Item { Layout.fillWidth: true }
                    Btn { text: "Close"; flat: true; onClicked: editor.visible = false }
                }
                Item { Layout.fillHeight: true }
            }
        }
    }

    function flagText(f) {
        switch (f.kind) {
        case "unclear": return "unclear: " + f.question
        case "ambiguous_deadline": return "ambiguous deadline: " + JSON.stringify(f.candidates)
        case "contradiction": return "contradiction: " + f.detail
        case "no_target": return f.ask + " (create with no verification to confirm)"
        case "file_not_indexed": return "item " + (f.item_index + 1) + ": " + f.ask
        default: return JSON.stringify(f)
        }
    }
    function onProposal(ok, r) {
        if (!ok) { root.notify(r.message, true); return }
        view.proposal = r
        view.items = r.items.map(function(i) { return {target_type: i.target_type, intent: i.intent, name: i.name, path: i.path || null,
                                                       linked_item_index: i.linked_item_index === undefined ? null : i.linked_item_index,
                                                       file_index_id: i.file_index_id === undefined ? null : i.file_index_id, populated_by: "llm"} })
        if (r.final_deadline) { final.text = r.final_deadline; finalResolved.text = falcon.resolveDeadline(r.final_deadline) || "?" }
        root.notify("proposal: " + r.items.length + " item(s)" + (r.flags.length ? ", " + r.flags.length + " flag(s)" : "")
                    + (r.proposed_split && r.proposed_split.length ? " — looks like " + r.proposed_split.length + " tasks: " + r.proposed_split.map(function(p) { return p.description }).join(" | ") : ""), false)
    }
    function deadline(field, label) {
        if (!field.text) return null
        var iso = falcon.resolveDeadline(field.text)
        if (!iso) { root.notify(label + " deadline must be ISO 8601 or a phrase like 'friday 5pm'", true); return undefined }
        return iso
    }
    function create(none) {
        var s = deadline(soft, "soft"), f = deadline(final, "final")
        if (s === undefined || f === undefined) return
        falcon.call("task.create", {assignee_account_id: parseInt(assignee.text), description: desc.text,
                                    verification_mode: none ? "none" : "stack", confirm_none: none, items: none ? [] : view.items,
                                    soft_deadline_at: s, final_deadline_at: f},
                    function(ok, r) {
                        if (!ok) { root.notify(r.message, true); return }
                        root.notify("task " + r.task.id + " created for " + r.task.assignee_name, false)
                        view.items = []; view.proposal = null; desc.text = ""; soft.text = ""; final.text = ""; softResolved.text = ""; finalResolved.text = ""
                        editor.visible = false; view.refresh()
                    })
    }
    function after(ok, r) { root.notify(ok ? falcon.pretty(r) : r.message, !ok); view.refresh(); if (ok && view.task) view.open(view.task.id) }
}
