import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// MAKING A FLOW (board FL08): a sentence over a preview.
//
//   Copy [folder] from [machine] to [folder] on [machine]   then [a step] … + another destination
//
// Every blank is a choice: machines from the department, folders from the file index (index.folders) -- a path is never
// typed. The tree the sentence makes grows underneath. The Engine's checks run on Save and are said in words: a loop is
// refused, a folder that already holds files asks whether that is meant, and a destination outside your authority waits
// for its owner's yes.
ColumnLayout {
    id: root

    property var tree: []
    property var layoutFn: null
    property var source: null               // { pc_id, hostname }
    property string sourcePath: ""
    property var destinations: []           // [{ pc_id, hostname, path }]
    property var stages: []                 // [{ stage_type }]
    property var folders: ({})              // pc_id -> [{ path, name, files }]
    property string problem: ""
    property bool askCollision: false
    signal created(int id)
    signal cancelled()

    spacing: 20

    function reset() { source = null; sourcePath = ""; destinations = []; stages = []; problem = ""; askCollision = false }
    readonly property var machines: {
        var out = []
        for (var i = 0; i < tree.length; i++) {
            var all = tree[i].workers.concat(tree[i].admins.filter(function (a) { return !!a.pc_id }))
            for (var j = 0; j < all.length; j++) if (all[j].pc_id) out.push({ pc_id: all[j].pc_id, hostname: all[j].hostname, name: all[j].name })
        }
        return out.sort(function (a, b) { return String(a.hostname).localeCompare(String(b.hostname)) })
    }
    function loadFolders(pcId) {
        if (folders[pcId]) return
        falcon.call("index.folders", { pc_id: pcId }, function (ok, r) {
            var copy = {}; for (var k in root.folders) copy[k] = root.folders[k]
            copy[pcId] = ok ? r.folders : []
            root.folders = copy
        })
    }
    function folderName(p) { var s = String(p || "").replace(/\\/g, "/").replace(/\/$/, ""); return s.split("/").pop() || s }
    function setDest(i, patch) {
        var c = destinations.slice(); var o = {}; for (var k in c[i]) o[k] = c[i][k]; for (var p in patch) o[p] = patch[p]; c[i] = o; destinations = c
    }
    readonly property bool complete: source !== null && sourcePath !== "" && destinations.length > 0
                                     && destinations.every(function (d) { return d.pc_id && d.path })

    // the preview, in the same shape a saved flow is drawn
    readonly property var preview: {
        if (!layoutFn) return { nodes: [], links: [], width: 0, height: 0 }
        var f = { source_hostname: source ? source.hostname : "choose a machine", source_path: sourcePath || "a folder", stages: [], destinations: [] }
        var parent = null
        for (var i = 0; i < stages.length; i++) { f.stages.push({ id: i + 1, parent_stage_id: parent, stage_type: stages[i].stage_type }); parent = i + 1 }
        for (var d = 0; d < destinations.length; d++)
            f.destinations.push({ id: 100 + d, parent_stage_id: parent, destination_hostname: destinations[d].hostname || "choose",
                                  destination_path: destinations[d].path || "a folder" })
        if (destinations.length === 0) f.destinations.push({ id: 100, parent_stage_id: parent, destination_hostname: "where to?", destination_path: "" })
        return layoutFn(f, 210, 64)
    }

    function save(confirmCollisions) {
        var st = stages.map(function (s, i) { return { stage_type: s.stage_type, parent_index: i === 0 ? null : i - 1, config: null } })
        var ds = destinations.map(function (d) { return { destination_pc_id: d.pc_id, destination_path: d.path, parent_index: st.length ? st.length - 1 : null } })
        falcon.call("flow.create", { source_pc_id: source.pc_id, source_path: sourcePath, destinations: ds, stages: st,
                                     confirm_collisions: !!confirmCollisions }, function (ok, r) {
            if (ok) {
                root.problem = ""; root.askCollision = false
                shell.notify(r.flow && r.flow.consent_status === "pending" ? "Saved — waiting for the owner's yes" : "Flow saved", false)
                root.created(r.flow.id)
                root.reset()
                return
            }
            root.problem = r.message
            root.askCollision = r.code === "conflict" && /collid|already/i.test(r.message)
        })
    }

    // --- the sentence -----------------------------------------------------------------------------------
    GridCell {
        objectName: "newFlowSentence"
        Layout.fillWidth: true
        Layout.preferredHeight: 160
        topAlign: true
        title: "Fill the sentence"
        narration: ({ brief: "then… adds a step", tone: "accent", state: "ok" })
        Column {
            width: parent.width
            spacing: 14
            Flow {
                width: parent.width
                spacing: 8
                Txt { text: "Copy"; color: Theme.dim; font.pixelSize: 17; height: 32; verticalAlignment: Text.AlignVCenter }
                SentenceSlot {
                    text: root.sourcePath ? root.folderName(root.sourcePath) : "a folder"; fontSize: 16; tone: root.sourcePath ? "accent" : "warn"
                    enabled: root.source !== null
                    onClicked: srcFolders.open()
                    Menu { id: srcFolders; y: parent.height + 4
                           Repeater { model: root.source ? (root.folders[root.source.pc_id] || []) : []
                                      delegate: MenuItem { required property var modelData; text: modelData.name + "   (" + modelData.files + " files)"
                                                           onTriggered: root.sourcePath = modelData.path } } }
                }
                Txt { text: "from"; color: Theme.dim; font.pixelSize: 17; height: 32; verticalAlignment: Text.AlignVCenter }
                SentenceSlot {
                    objectName: "newFlowSource"
                    text: root.source ? root.source.hostname : "a machine"; fontSize: 16; tone: root.source ? "accent" : "warn"
                    onClicked: srcMachines.open()
                    Menu { id: srcMachines; y: parent.height + 4
                           Repeater { model: root.machines
                                      delegate: MenuItem { required property var modelData; text: modelData.hostname + "  ·  " + (modelData.name || "")
                                                           onTriggered: { root.source = modelData; root.sourcePath = ""; root.loadFolders(modelData.pc_id) } } } }
                }
                Repeater {
                    model: root.destinations
                    delegate: Row {
                        required property var modelData
                        required property int index
                        spacing: 8
                        Txt { text: index === 0 ? "to" : "and to"; color: Theme.dim; font.pixelSize: 17; height: 32; verticalAlignment: Text.AlignVCenter }
                        SentenceSlot {
                            text: modelData.path ? root.folderName(modelData.path) : "a folder"; fontSize: 16; tone: modelData.path ? "ok" : "warn"
                            enabled: !!modelData.pc_id
                            onClicked: dFolders.open()
                            Menu { id: dFolders; y: parent.height + 4
                                   Repeater { model: modelData.pc_id ? (root.folders[modelData.pc_id] || []) : []
                                              delegate: MenuItem { required property var modelData; text: modelData.name + "   (" + modelData.files + " files)"
                                                                   onTriggered: root.setDest(index, { path: modelData.path }) } } }
                        }
                        Txt { text: "on"; color: Theme.dim; font.pixelSize: 17; height: 32; verticalAlignment: Text.AlignVCenter }
                        SentenceSlot {
                            text: modelData.hostname || "a machine"; fontSize: 16; tone: modelData.hostname ? "ok" : "warn"
                            onClicked: dMachines.open()
                            Menu { id: dMachines; y: parent.height + 4
                                   Repeater { model: root.machines
                                              delegate: MenuItem { required property var modelData; text: modelData.hostname + "  ·  " + (modelData.name || "")
                                                                   onTriggered: { root.setDest(index, { pc_id: modelData.pc_id, hostname: modelData.hostname, path: "" })
                                                                                  root.loadFolders(modelData.pc_id) } } } }
                        }
                    }
                }
                SentenceSlot { visible: root.destinations.length === 0; text: "+ to…"; dashed: true; fontSize: 16
                               onClicked: root.destinations = [{ pc_id: 0, hostname: "", path: "" }] }
            }
            Row {
                spacing: 9
                Repeater {
                    model: root.stages
                    delegate: Row { required property var modelData; required property int index; spacing: 9
                        Txt { text: "then"; color: Theme.faint; font.pixelSize: Theme.fRow; anchors.verticalCenter: parent.verticalCenter }
                        SentenceSlot { text: modelData.stage_type === "transformation" ? "transform" : modelData.stage_type === "categorization" ? "sort into folders" : "branch"
                                       tone: "warn"; onClicked: { var c = root.stages.slice(); c.splice(index, 1); root.stages = c } } }
                }
                SentenceSlot {
                    text: "+ then…"; dashed: true
                    onClicked: stageMenu.open()
                    Menu { id: stageMenu; y: parent.height + 4
                           MenuItem { text: "transform the files"; onTriggered: root.stages = root.stages.concat([{ stage_type: "transformation" }]) }
                           MenuItem { text: "sort them into folders"; onTriggered: root.stages = root.stages.concat([{ stage_type: "categorization" }]) } }
                }
                Txt { text: "·"; color: Theme.faint; font.pixelSize: Theme.fRow; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: "+ another destination"; color: Theme.accent; font.pixelSize: Theme.fBody; anchors.verticalCenter: parent.verticalCenter
                      visible: root.destinations.length > 0
                      MouseArea { anchors.fill: parent; anchors.margins: -4; cursorShape: Qt.PointingHandCursor
                                  onClicked: root.destinations = root.destinations.concat([{ pc_id: 0, hostname: "", path: "" }]) } }
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 20
        GridCell {
            objectName: "newFlowPreview"
            Layout.fillWidth: true
            Layout.preferredWidth: 2
            Layout.fillHeight: true
            topAlign: true
            title: "What it makes"
            narration: ({ brief: "a preview", state: "ok" })
            Column {
                width: parent.width
                spacing: 10
                Item {
                    width: parent.width; height: Math.max(160, root.height - 300)
                    FlowTree { x: Math.max(0, (parent.width - root.preview.width) / 2)
                               y: Math.max(0, (parent.height - root.preview.height - nodeHeight) / 2 - 20)
                               width: root.preview.width; height: root.preview.height + nodeHeight
                               nodes: root.preview.nodes; links: root.preview.links }
                }
                Txt { text: "The tree grows as you write the sentence."; color: Theme.faint; font.pixelSize: Theme.fMeta }
            }
        }
        GridCell {
            objectName: "newFlowChecks"
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            Layout.fillHeight: true
            topAlign: true
            title: "Checked before saving"
            narration: ({ brief: root.problem ? "one question" : "", tone: root.problem ? "warn" : "", state: "ok" })
            Column {
                width: parent.width
                spacing: 10
                Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.dim; font.pixelSize: Theme.fBody
                      text: "When you save, Falcon checks three things: that nothing flows back into its own source, that the destination folder is not already holding unrelated files, and whether the destination's owner must agree." }
                Row { visible: root.problem !== ""; spacing: 8; width: parent.width
                      Icon { name: "warn"; size: 15; color: Theme.warn }
                      Txt { width: parent.width - 23; wrapMode: Text.WordWrap; text: root.problem; color: Theme.warn; font.pixelSize: Theme.fBody } }
                Row { visible: root.askCollision; spacing: 6
                      GBtn { text: "Use another folder"; small: true; onClicked: { root.problem = ""; root.askCollision = false } }
                      GBtn { text: "Replace them, it is meant"; small: true; onClicked: root.save(true) } }
                Item { width: 1; height: 10 }
                Row { spacing: 8
                      GBtn { text: "Cancel"; onClicked: { root.reset(); root.cancelled() } }
                      TBtn { objectName: "newFlowSave"; text: "Save the flow"; iconName: "check"; enabled: root.complete; onClicked: root.save(false) } }
                Txt { visible: !root.complete; color: Theme.faint; font.pixelSize: Theme.fMeta; width: parent.width; wrapMode: Text.WordWrap
                      text: "Fill every blank first: a machine and folder to copy from, and somewhere to copy to." }
            }
        }
    }
}
