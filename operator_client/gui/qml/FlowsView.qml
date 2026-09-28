import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// FLOWS (boards FL06 the page, FL07 one flow, FL08 making one). An Admin's -- and a Super User inside one sees it.
//
//   list  what is broken, what waits for a yes, where files go (every flow drawn, paging down), your flows as cards
//   flow  the flow as a TREE by default (Sentence and Card are the other views), the fix offered beside a paused branch,
//         and every outside edit that was kept rather than overwritten
//   new   a sentence -- Copy [folder] from [machine] to [folder] on [machine], then [a step] -- with the tree growing
//         under it. Folders are picked from the index, never typed. The Engine's checks (loop, collision, consent) are
//         said in words before anything is saved.
//
// A stage's settings (what a transform converts to, how sorting groups) are a deferred design decision
// (CLAUDE.md, spec 10): stages are chosen by kind here and carry no settings until that is decided.
Item {
    id: root

    property string mode: "list"            // list | flow | new
    property var flows: []
    property var flow: null                 // flow.status
    property var history: []
    property var tree: []
    property string view: "tree"            // tree | sentence | card
    property string clock: ""

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("flow.list", {}, function (ok, r) { if (ok) root.flows = r.flows; else shell.notify(r.message, true) })
        falcon.call("hierarchy.tree", {}, function (ok, r) { if (ok) root.tree = r.departments })
    }
    function open(id) {
        falcon.call("flow.status", { flow_id: id }, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            root.flow = r.flow
            root.mode = "flow"
            falcon.call("flow.history", { flow_id: id }, function (ok2, h) { root.history = ok2 ? h.history : [] })
        })
    }
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onScopeChanged() { if (falcon.isConnected) root.refresh() }
        function onPushReceived(type, p) {
            if (type.indexOf("flow.") === 0) { root.refresh(); if (root.flow && p.flow_id === root.flow.id) root.open(root.flow.id) }
        }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Keys.onEscapePressed: root.mode = "list"
    focus: true

    // --- words and shapes -----------------------------------------------------------------------------
    function folderName(p) { var s = String(p || "").replace(/\\/g, "/").replace(/\/$/, ""); return s.split("/").pop() || s }
    function stageWord(st) { return st.stage_type === "transformation" ? "Transform" : st.stage_type === "categorization" ? "Sort into folders" : "Branch" }
    function destWord(d) { return (d.destination_hostname || "Remote storage") + " · " + folderName(d.destination_path) }
    function isBroken(f) { return f.status === "paused" || (f.destinations || []).some(function (d) { return !!d.paused_reason }) }
    function stateWord(f) {
        return f.consent_status === "pending" ? "waiting for a yes" : isBroken(f) ? "paused" : f.status === "active" ? "syncing" : f.status
    }
    function nameOf(accountId, fallback) {
        for (var i = 0; i < tree.length; i++) {
            var all = tree[i].admins.concat(tree[i].workers)
            for (var j = 0; j < all.length; j++) if (all[j].account_id === accountId) return all[j].name
        }
        return fallback || "the owner"
    }
    function ownerOf(f) {
        var d = (f.destinations || [])[0]
        return d ? nameOf(d.owner_account_id, (d.destination_hostname || "the destination") + "'s owner") : "the owner"
    }
    readonly property var broken: flows.filter(isBroken)
    readonly property var waiting: flows.filter(function (f) { return f.consent_status === "pending" })
    // a flow waiting on MY yes: it is into a folder I own, and nobody else can answer for me
    function mine(f) {
        if (!f || f.consent_status !== "pending") return false
        var me = falcon ? falcon.accountId : 0
        return (f.destinations || []).some(function (d) { return d.owner_account_id === me })
    }
    // retiring says its cost first: it stops syncing, and what it already copied stays where it is
    function retire() {
        if (!root.flow) return
        var f = root.flow
        shell.ask({ title: "Retire this flow?",
                    lead: "It stops copying from " + (f.source_hostname || "the source") + " straight away.",
                    body: "Everything it has already copied stays where it is, and its history is kept.",
                    act: "Retire it", actIcon: "stop", cancel: "Keep it" }, function () {
            falcon.call("flow.delete", { flow_id: f.id }, function (ok, r) {
                shell.notify(ok ? "The flow is retired" : r.message, !ok)
                if (ok) { root.mode = "list"; root.refresh() }
            })
        })
    }

    // A flow as a tree: source at the left, stages by depth, destinations at the right; leaves spaced evenly and each
    // parent centred on its children. Broken branches (a paused destination) are dashed.
    function layout(f, colW, rowH) {
        if (!f) return { nodes: [], links: [] }
        var kids = {}, info = {}
        function add(parent, id) { (kids[parent] = kids[parent] || []).push(id) }
        info["s"] = { icon: "folder", label: f.source_hostname || "source", sub: folderName(f.source_path), tone: "accent" }
        var stages = f.stages || []
        for (var i = 0; i < stages.length; i++) {
            var st = stages[i]
            info["st" + st.id] = { icon: st.stage_type === "categorization" ? "folder" : "file", label: stageWord(st), sub: "", tone: "warn" }
            add(st.parent_stage_id ? "st" + st.parent_stage_id : "s", "st" + st.id)
        }
        var dests = f.destinations || []
        for (var d = 0; d < dests.length; d++) {
            var de = dests[d]
            info["d" + de.id] = { icon: de.destination_hostname ? "monitor" : "globe", label: de.destination_hostname || "Remote storage",
                                  sub: de.paused_reason ? "paused — " + folderName(de.destination_path) : folderName(de.destination_path),
                                  tone: "ok", bad: !!de.paused_reason }
            add(de.parent_stage_id ? "st" + de.parent_stage_id : "s", "d" + de.id)
        }
        var nodes = [], links = [], next = 0
        function place(id, depth) {
            var ch = kids[id] || []
            var y
            if (ch.length === 0) { y = next * rowH; next++ }
            else {
                var ys = ch.map(function (c) { return place(c, depth + 1) })
                y = ys.reduce(function (a, b) { return a + b }, 0) / ys.length
            }
            var n = info[id]
            nodes.push({ id: id, x: depth * colW, y: y, w: colW - 50, icon: n.icon, label: n.label, sub: n.sub, tone: n.tone, bad: !!n.bad })
            for (var k = 0; k < ch.length; k++) links.push({ from: id, to: ch[k], bad: !!(info[ch[k]] && info[ch[k]].bad) })
            return y
        }
        place("s", 0)
        // only the link into a paused destination is dashed: the rest of the flow still runs
        var maxX = 0
        for (var q = 0; q < nodes.length; q++) maxX = Math.max(maxX, nodes[q].x + nodes[q].w)
        return { nodes: nodes, links: links, width: maxX, height: Math.max(0, next - 1) * rowH }
    }
    // the map draws at most two destinations per flow; the rest are "+N more"
    function firstTwo(f) {
        if (!f) return f
        var c = {}; for (var k in f) c[k] = f[k]
        c.destinations = (f.destinations || []).slice(0, 2)
        return c
    }
    function sentence(f) {
        if (!f) return ""
        var s = "Copy " + folderName(f.source_path) + " from " + (f.source_hostname || "a machine")
        var st = (f.stages || []).map(stageWord)
        if (st.length) s += ", then " + st.join(", then ").toLowerCase()
        s += ", to " + (f.destinations || []).map(destWord).join(" and ")
        return s + "."
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
                    Txt { text: "Flows"; color: root.mode === "list" ? "#ffffff" : Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody
                          font.weight: root.mode === "list" ? Font.DemiBold : Font.Normal
                          MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: root.mode = "list" } }
                    Icon { visible: root.mode !== "list"; name: "chev"; color: Qt.rgba(1, 1, 1, 0.45); size: 12; anchors.verticalCenter: parent.verticalCenter }
                    Txt { objectName: "flowsCrumb"; visible: root.mode !== "list"; color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                          text: root.mode === "new" ? "New flow" : root.flow ? root.folderName(root.flow.source_path) : "" }
                }
                Row {
                    spacing: 12
                    Txt { text: root.mode === "new" ? "New flow" : root.mode === "flow" && root.flow ? root.folderName(root.flow.source_path) : "Flows"
                          color: "#ffffff"; font.pixelSize: Theme.fTitle; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                    Txt { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody
                          color: root.broken.length > 0 ? Theme.warn : Qt.rgba(1, 1, 1, 0.55)
                          text: root.mode === "list" ? root.flows.length + (root.flows.length === 1 ? " flow" : " flows")
                                                         + (root.broken.length > 0 ? " · " + root.broken.length + " paused" : "")
                                : root.mode === "flow" && root.flow ? "from " + (root.flow.source_hostname || "") + " · " + root.stateWord(root.flow)
                                : "write it as a sentence" }
                }
            }
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 16
                TBtn { visible: root.mode === "list"; text: "New flow"; iconName: "plus"; onClicked: { newFlow.reset(); root.mode = "new" } }
                Txt { text: root.mode === "list" ? root.clock : "Esc to go back"; color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody
                      anchors.verticalCenter: parent.verticalCenter }
            }
        }

        // ====================================================================================================
        // FL06: the page
        RowLayout {
            visible: root.mode === "list"
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            ColumnLayout {
                Layout.preferredWidth: 460
                Layout.maximumWidth: 460
                Layout.fillHeight: true
                spacing: 20
                GridCell {
                    objectName: "flowsBroken"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    topAlign: true
                    title: "Broken"
                    narration: ({ brief: root.broken.length === 0 ? "nothing" : root.broken.length + " paused", tone: root.broken.length > 0 ? "danger" : "ok", state: "ok" })
                    Column {
                        width: parent.width
                        spacing: 10
                        Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: Theme.fSection; font.weight: Font.DemiBold
                              text: root.broken.length === 0 ? "Every flow is running." : "Only the broken branch waits; everything else still runs." }
                        PagedColumn {
                            width: parent.width; height: Math.max(70, root.height / 2 - 170); itemHeight: 58
                            model: root.broken
                            delegate: InfoCard {
                                iconName: "flows"; iconTone: "danger"
                                title: modelData ? (modelData.source_hostname || "") + " → " + (modelData.destinations || []).map(function (d) { return d.destination_hostname || "remote" }).join(", ") : ""
                                line: modelData ? (modelData.suggestion || ((modelData.destinations || []).filter(function (d) { return d.suggestion })[0] || {}).suggestion || "paused") : ""
                                stateWord: "see the fix"; stateTone: "accent"
                                onClicked: root.open(modelData.id)
                            }
                        }
                    }
                }
                GridCell {
                    objectName: "flowsWaiting"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 250
                    topAlign: true
                    title: "Waiting for a yes"
                    narration: ({ brief: root.waiting.length === 0 ? "none" : String(root.waiting.length), tone: root.waiting.length > 0 ? "accent" : "", state: "ok" })
                    Column {
                        width: parent.width
                        spacing: 9
                        Repeater {
                            model: root.waiting.slice(0, 2)
                            delegate: InfoCard {
                                required property var modelData
                                width: parent.width
                                iconName: "user"
                                title: root.ownerOf(modelData)
                                line: "must agree: " + (modelData.source_hostname || "") + " → " + ((modelData.destinations || [])[0] ? root.destWord(modelData.destinations[0]) : "")
                                lineTone: "accent"
                                onClicked: root.open(modelData.id)
                            }
                        }
                        Txt { visible: root.waiting.length === 0; text: "No flow waits on anyone."; color: Theme.faint; font.pixelSize: Theme.fBody }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 20
                GridCell {
                    objectName: "flowsMap"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    topAlign: true
                    title: "Where files go"
                    narration: ({ brief: "every flow, drawn", state: root.flows.length === 0 ? "empty" : "ok",
                                  note: "No flows yet", sentence: "Make one with New flow." })
                    // every flow as a small tree, one per row, paging down -- never one crowded drawing
                    PagedColumn {
                        width: parent.width
                        height: Math.max(120, root.height / 2 - 110)
                        itemHeight: 112
                        spacing: 10
                        model: root.flows
                        attention: function (f) { return root.isBroken(f) ? (f.source_hostname || "a flow") + " paused" : "" }
                        delegate: Item {
                            property var modelData: null
                            property int index: -1
                            readonly property int more: modelData ? Math.max(0, (modelData.destinations || []).length - 2) : 0
                            readonly property var shape: root.layout(root.firstTwo(modelData), Math.max(170, (width - 70) / 3.2), 56)
                            Rectangle { visible: parent.index > 0; width: parent.width; height: 1; y: -5; color: Theme.line }
                            FlowTree {
                                width: parent.width - 70; height: parent.shape.height + nodeHeight
                                y: (parent.height - height) / 2
                                nodeHeight: 44
                                nodes: parent.shape.nodes
                                links: parent.shape.links
                                onNodeClicked: root.open(parent.modelData.id)
                            }
                            Txt { visible: parent.more > 0; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.bottomMargin: 20
                                  text: "+" + parent.more + " more"; color: Theme.faint; font.pixelSize: Theme.fMeta }
                        }
                    }
                }
                GridCell {
                    objectName: "flowsCards"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 250
                    topAlign: true
                    title: "Your flows"
                    narration: ({ brief: "from → to", state: "ok" })
                    Flow {
                        width: parent.width
                        spacing: 14
                        Repeater {
                            model: root.flows.slice(0, 4)
                            delegate: Rectangle {
                                required property var modelData
                                width: (parent.width - 14) / 2; height: 70; radius: 14
                                color: fcArea.containsMouse ? Qt.lighter(Theme.pane, 1.12) : Theme.pane
                                Column {
                                    anchors.fill: parent; anchors.margins: 13; spacing: 8
                                    Row { spacing: 8
                                          Txt { text: modelData.source_hostname || ""; color: Theme.ink; monospace: true; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                                          Icon { name: "fwd"; size: 13; color: Theme.faint; anchors.verticalCenter: parent.verticalCenter }
                                          Txt { text: (modelData.destinations || []).map(function (d) { return d.destination_hostname || "remote" }).join(", ")
                                                color: Theme.dim; font.pixelSize: Theme.fBody } }
                                    Item { width: parent.width; height: 16
                                        Txt { text: (modelData.stages || []).length ? (modelData.stages || []).map(root.stageWord).join(", ").toLowerCase() : "copied as they are"
                                              color: (modelData.stages || []).length ? Theme.warn : Theme.faint; font.pixelSize: Theme.fMeta }
                                        Txt { anchors.right: parent.right; text: root.stateWord(modelData); font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold
                                              color: root.isBroken(modelData) ? Theme.danger : modelData.consent_status === "pending" ? Theme.accent : Theme.faint } }
                                }
                                MouseArea { id: fcArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.open(modelData.id) }
                            }
                        }
                    }
                }
            }
        }

        // ====================================================================================================
        // FL07: one flow
        RowLayout {
            visible: root.mode === "flow" && root.flow !== null
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            GridCell {
                objectName: "flowShape"
                Layout.fillWidth: true
                Layout.preferredWidth: 2
                Layout.fillHeight: true
                topAlign: true
                title: "The flow"
                narration: ({ brief: root.flow ? (root.flow.destinations || []).length + ((root.flow.destinations || []).length === 1 ? " destination" : " destinations") : "", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 16
                    SegmentedControl { id: viewTabs; segments: [{ text: "Tree" }, { text: "Sentence" }, { text: "Card" }] }
                    Item {
                        visible: viewTabs.currentIndex === 0
                        width: parent.width
                        height: Math.max(200, root.height - 250)
                        readonly property var shape: root.layout(root.flow, Math.min(250, Math.max(190, width / 4)), 72)
                        FlowTree {
                            objectName: "flowTree"
                            x: Math.max(0, (parent.width - parent.shape.width) / 2)
                            y: Math.max(0, (parent.height - parent.shape.height - nodeHeight) / 2 - 20)
                            width: parent.shape.width; height: parent.shape.height + nodeHeight
                            nodes: parent.shape.nodes
                            links: parent.shape.links
                        }
                    }
                    Txt { visible: viewTabs.currentIndex === 1; width: parent.width; wrapMode: Text.WordWrap; color: Theme.ink
                          font.pixelSize: Theme.fSection + 2; lineHeight: 1.5; text: root.sentence(root.flow) }
                    Column {
                        visible: viewTabs.currentIndex === 2
                        width: parent.width
                        spacing: 8
                        Txt { text: "FROM"; color: Theme.faint; font.pixelSize: Theme.fMeta; font.weight: Font.Bold }
                        InfoCard { width: parent.width; iconName: "folder"; title: root.flow ? (root.flow.source_hostname || "") + " · " + root.folderName(root.flow.source_path) : "" }
                        Txt { text: "THROUGH"; color: Theme.faint; font.pixelSize: Theme.fMeta; font.weight: Font.Bold; visible: root.flow && (root.flow.stages || []).length > 0 }
                        Repeater { model: root.flow ? (root.flow.stages || []) : []
                                   delegate: InfoCard { required property var modelData; width: parent.width; iconName: "file"; iconTone: "warn"; title: root.stageWord(modelData) } }
                        Txt { text: "TO"; color: Theme.faint; font.pixelSize: Theme.fMeta; font.weight: Font.Bold }
                        Repeater { model: root.flow ? (root.flow.destinations || []) : []
                                   delegate: InfoCard { required property var modelData; width: parent.width; iconName: "monitor"; iconTone: modelData.paused_reason ? "danger" : "ok"
                                                        title: root.destWord(modelData); stateWord: modelData.paused_reason ? "paused" : ""; stateTone: "danger" } }
                    }
                    Txt { visible: viewTabs.currentIndex === 0; color: Theme.faint; font.pixelSize: Theme.fMeta
                          text: "Tree is the default. Sentence and Card show the same flow another way." }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                spacing: 20
                GridCell {
                    objectName: "flowFix"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    topAlign: true
                    title: root.flow && root.isBroken(root.flow) ? "The fix, offered" : "Running"
                    narration: ({ brief: root.flow && root.isBroken(root.flow) ? "for the paused branch" : "", tone: "danger", state: "ok" })
                    Column {
                        width: parent.width
                        spacing: 11
                        Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: Theme.fSection; font.weight: Font.DemiBold
                              text: !root.flow ? "" : !root.isBroken(root.flow) ? (root.flow.consent_status === "pending" ? "Waiting for the destination's owner to agree." : "Every branch is syncing.")
                                    : (root.flow.suggestion || ((root.flow.destinations || []).filter(function (d) { return d.suggestion })[0] || {}).suggestion || "A branch is paused.") }
                        Txt { visible: root.flow && root.isBroken(root.flow); width: parent.width; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta
                              text: "Only the paused branch waits. Resume once the cause is fixed." }
                        // THE OWNER'S ANSWER (flow.consent). A flow into somebody else's folder does not
                        // run until they agree, and this is where they say so -- on the flow itself.
                        Row { spacing: 8
                              visible: root.mine(root.flow)
                              TBtn { objectName: "flowAllow"; text: "Yes, allow it"; tone: "ok"; iconName: "check"
                                     onClicked: falcon.call("flow.consent", { flow_id: root.flow.id, granted: true }, root.after) }
                              GBtn { objectName: "flowRefuse"; text: "No"
                                     onClicked: falcon.call("flow.consent", { flow_id: root.flow.id, granted: false }, root.after) } }
                        Row { spacing: 8
                              TBtn { visible: root.flow && root.isBroken(root.flow); text: "Resume"; iconName: "play"
                                     onClicked: falcon.call("flow.resume", { flow_id: root.flow.id }, root.after) }
                              GBtn { visible: root.flow && !root.isBroken(root.flow) && root.flow.status === "active"; text: "Pause"; iconName: "pause"
                                     onClicked: falcon.call("flow.pause", { flow_id: root.flow.id }, root.after) }
                              GBtn { visible: root.flow && root.flow.status === "active"; text: "Sync now"
                                     onClicked: falcon.call("flow.trigger", { flow_id: root.flow.id }, root.after) }
                              GBtn { objectName: "flowChange"; visible: root.flow !== null; text: "Change"; iconName: "branch"
                                     onClicked: { newFlow.start(root.flow); root.mode = "new" } }
                              GBtn { objectName: "flowRetire"; visible: root.flow !== null; text: "Retire"; iconName: "stop"
                                     onClicked: root.retire() } }
                    }
                }
                GridCell {
                    id: keptCell
                    objectName: "flowKept"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 300
                    topAlign: true
                    title: "Kept, not overwritten"
                    readonly property var kept: root.history.filter(function (h) { return h.written_by === "external" })
                    narration: ({ brief: kept.length === 0 ? "none" : kept.length + (kept.length === 1 ? " time" : " times"), tone: kept.length > 0 ? "warn" : "", state: "ok" })
                    Column {
                        width: parent.width
                        spacing: 9
                        Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                              text: keptCell.kept.length === 0 ? "Nobody has changed a copy at a destination."
                                    : "Someone changed a copy at a destination; their version was kept beside the fresh one." }
                        Repeater {
                            model: keptCell.kept.slice(0, 3)
                            delegate: InfoCard { required property var modelData; width: parent.width; iconName: "file"; iconTone: "warn"
                                                 title: root.folderName(modelData.written_path || modelData.destination_path)
                                                 line: "kept " + String(modelData.occurred_at || "").substring(11, 16) + (modelData.conflict_resolved ? " · resolved" : "")
                                                 stateWord: "kept"; stateTone: "warn" }
                        }
                    }
                }
            }
        }

        // ====================================================================================================
        // FL08: making one
        NewFlow {
            id: newFlow
            visible: root.mode === "new"
            Layout.fillWidth: true
            Layout.fillHeight: true
            tree: root.tree
            layoutFn: root.layout
            onCreated: function (id) { root.refresh(); root.open(id) }
            onCancelled: root.mode = "list"
        }
    }

    function after(ok, r) {
        shell.notify(ok ? "Done" : r.message, !ok)
        root.refresh()
        if (ok && root.flow) root.open(root.flow.id)
    }
}
