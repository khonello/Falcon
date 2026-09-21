import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Flows: list / status with stages + destinations / history, pause-resume-delete, consent, and
// a small builder (source, destinations, optional stages). Collision/cycle/consent issues come
// back from the Engine as errors or paused destinations — never silently resolved here.
Item {
    id: view
    property var flows: []
    property var flow: null
    property var history: []
    property var dests: []      // builder: [{destination_pc_id, destination_path, parent_index}]
    property var stages: []     // builder: [{stage_type, parent_index, config}]

    function refresh() {
        falcon.call("flow.list", {}, function(ok, r) { if (ok) view.flows = r.flows; else root.notify(r.message, true) })
    }
    function open(id) {
        falcon.call("flow.status", {flow_id: id}, function(ok, r) { if (ok) view.flow = r.flow; else root.notify(r.message, true) })
        falcon.call("flow.history", {flow_id: id}, function(ok, r) { if (ok) view.history = r.history })
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Connections {
        target: falcon
        function onConnected() { view.refresh() }
        function onPushReceived(type, p) {
            if (type.indexOf("flow.") === 0) { view.refresh(); if (view.flow && p.flow_id === view.flow.id) view.open(view.flow.id) }
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
                Label { text: "Flows"; font.pixelSize: 18; color: "white" }
                Item { Layout.fillWidth: true }
                Button { text: "New flow"; onClicked: builder.visible = !builder.visible }
                Button { text: "Refresh"; onClicked: view.refresh() }
            }
            DataTable {
                Layout.fillWidth: true
                Layout.preferredHeight: 200
                rows: view.flows
                columns: ["id", "status", "consent_status", "source_pc_id", "source_path", "pause_reason", "created_at"]
                widths: ({id: 50, status: 80, consent_status: 90, source_pc_id: 70, source_path: 300, pause_reason: 140, created_at: 130})
                onRowClicked: function(row) { view.open(row.id) }
            }

            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                color: "#26282c"; radius: 6
                visible: !!view.flow
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 10; spacing: 6
                    RowLayout {
                        Label { text: view.flow ? "Flow " + view.flow.id + " — " + view.flow.status + " · consent " + view.flow.consent_status : ""; color: "white"; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Button { text: "Grant consent"; onClicked: falcon.call("flow.consent", {flow_id: view.flow.id, granted: true}, view.after) }
                        Button { text: "Deny"; onClicked: falcon.call("flow.consent", {flow_id: view.flow.id, granted: false}, view.after) }
                        Button { text: "Pause"; onClicked: falcon.call("flow.pause", {flow_id: view.flow.id}, view.after) }
                        Button { text: "Resume"; onClicked: falcon.call("flow.resume", {flow_id: view.flow.id, destination_id: destTable.selectedIndex >= 0 ? view.flow.destinations[destTable.selectedIndex].id : null}, view.after) }
                        Button { text: "Delete"; onClicked: falcon.call("flow.delete", {flow_id: view.flow.id}, view.after) }
                    }
                    Label { color: "#ddd"; wrapMode: Text.Wrap; Layout.fillWidth: true
                            text: view.flow ? "source pc " + view.flow.source_pc_id + " : " + view.flow.source_path + (view.flow.pause_reason ? "\npaused: " + view.flow.pause_reason : "")
                                              + (view.flow.suggestion ? "\nsuggestion: " + view.flow.suggestion : "") : "" }
                    RowLayout {
                        TextField { id: trig; Layout.preferredWidth: 260; placeholderText: "relative path to push now" }
                        Button { text: "Trigger transfer"; enabled: trig.text.length > 0
                                 onClicked: falcon.call("flow.trigger", {flow_id: view.flow.id, relative_path: trig.text}, view.after) }
                    }
                    Label { text: "stages"; color: "#9aa"; visible: view.flow && view.flow.stages.length > 0 }
                    DataTable {
                        Layout.fillWidth: true; Layout.preferredHeight: 70; visible: view.flow && view.flow.stages.length > 0
                        rows: view.flow ? view.flow.stages : []
                        columns: ["id", "stage_type", "parent_stage_id", "config"]
                        widths: ({id: 50, stage_type: 100, parent_stage_id: 100, config: 400})
                    }
                    Label { text: "destinations (select one to resume it alone)"; color: "#9aa" }
                    DataTable {
                        id: destTable
                        Layout.fillWidth: true; Layout.preferredHeight: 100
                        rows: view.flow ? view.flow.destinations : []
                        columns: ["id", "destination_pc_id", "destination_path", "parent_stage_id", "pre_flight_check_status", "paused_reason", "suggestion"]
                        widths: ({id: 50, destination_pc_id: 60, destination_path: 260, parent_stage_id: 60, pre_flight_check_status: 90, paused_reason: 140, suggestion: 200})
                    }
                    Label { text: "history"; color: "#9aa" }
                    DataTable {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        rows: view.history
                        columns: ["occurred_at", "destination_path", "written_by", "content_hash", "conflict_resolved"]
                        widths: ({occurred_at: 130, destination_path: 280, written_by: 90, content_hash: 200, conflict_resolved: 60})
                        emptyText: "(no transfers yet)"
                    }
                }
            }
            Item { Layout.fillHeight: true; visible: !view.flow }
        }

        // builder
        Rectangle {
            id: builder
            Layout.preferredWidth: 420
            Layout.fillHeight: true
            color: "#26282c"; radius: 6
            visible: false
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 6
                Label { text: "New flow"; font.pixelSize: 16; color: "white" }
                RowLayout {
                    Label { text: "source pc"; color: "#ccc" }
                    TextField { id: srcPc; Layout.preferredWidth: 60; validator: IntValidator { bottom: 1 } }
                    TextField { id: srcPath; Layout.fillWidth: true; placeholderText: "C:\\path\\on\\source" }
                }
                Label { text: "destinations"; color: "#9aa" }
                DataTable { id: destList; Layout.fillWidth: true; Layout.preferredHeight: 90; rows: view.dests
                            columns: ["destination_pc_id", "destination_path", "parent_index"]; widths: ({destination_pc_id: 60, destination_path: 240, parent_index: 60}); emptyText: "(add at least one)" }
                RowLayout {
                    TextField { id: dPc; Layout.preferredWidth: 60; placeholderText: "pc / remote" }
                    TextField { id: dPath; Layout.fillWidth: true; placeholderText: "destination path" }
                    TextField { id: dStage; Layout.preferredWidth: 50; placeholderText: "stage#" }
                    Button { text: "+"; enabled: dPath.text.length > 0
                             onClicked: { var a = view.dests.slice(); a.push({destination_pc_id: dPc.text === "remote" || dPc.text === "" ? null : parseInt(dPc.text), destination_path: dPath.text,
                                                                             parent_index: dStage.text ? parseInt(dStage.text) : null}); view.dests = a; dPath.text = "" } }
                    Button { text: "−"; enabled: destList.selectedIndex >= 0; onClicked: { var a = view.dests.slice(); a.splice(destList.selectedIndex, 1); view.dests = a; destList.selectedIndex = -1 } }
                }
                Label { text: "stages (optional: branch / transform / categorize)"; color: "#9aa" }
                DataTable { id: stageList; Layout.fillWidth: true; Layout.preferredHeight: 70; rows: view.stages
                            columns: ["stage_type", "parent_index", "config"]; widths: ({stage_type: 100, parent_index: 60, config: 220}); emptyText: "(none)" }
                RowLayout {
                    ComboBox { id: sType; model: ["branch", "transform", "categorize"]; Layout.preferredWidth: 110 }
                    TextField { id: sParent; Layout.preferredWidth: 50; placeholderText: "parent#" }
                    TextField { id: sCfg; Layout.fillWidth: true; placeholderText: "k=v,k2=v2" }
                    Button { text: "+"; onClicked: { var cfg = null
                                                     if (sCfg.text) { cfg = {}; sCfg.text.split(",").forEach(function(kv) { var i = kv.indexOf("="); if (i > 0) cfg[kv.substring(0, i)] = kv.substring(i + 1) }) }
                                                     var a = view.stages.slice(); a.push({stage_type: sType.currentText, parent_index: sParent.text ? parseInt(sParent.text) : null, config: cfg}); view.stages = a; sCfg.text = "" } }
                    Button { text: "−"; enabled: stageList.selectedIndex >= 0; onClicked: { var a = view.stages.slice(); a.splice(stageList.selectedIndex, 1); view.stages = a; stageList.selectedIndex = -1 } }
                }
                RowLayout {
                    CheckBox { id: confirm; text: "confirm collisions" }
                    Item { Layout.fillWidth: true }
                    Button { text: "Create"; enabled: srcPc.text.length > 0 && srcPath.text.length > 0 && view.dests.length > 0
                             onClicked: falcon.call("flow.create", {source_pc_id: parseInt(srcPc.text), source_path: srcPath.text, destinations: view.dests, stages: view.stages, confirm_collisions: confirm.checked},
                                                    function(ok, r) { if (!ok) { root.notify(r.message, true); return }
                                                                      root.notify("flow " + r.flow.id + " created (" + r.flow.status + ", consent " + r.flow.consent_status + ")", false)
                                                                      view.dests = []; view.stages = []; builder.visible = false; view.refresh(); view.open(r.flow.id) }) }
                    Button { text: "Close"; flat: true; onClicked: builder.visible = false }
                }
                Item { Layout.fillHeight: true }
            }
        }
    }

    function after(ok, r) { root.notify(ok ? falcon.pretty(r) : r.message, !ok); view.refresh(); if (ok && view.flow) view.open(view.flow.id) }
}
