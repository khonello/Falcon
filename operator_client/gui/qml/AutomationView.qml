import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// AUTOMATION (board AU04), an Admin's -- a Super User inside one sees the same.
//
//   left   every automation as  when → first action (+ N more), paging down; + New automation
//   right  the chosen one as a recipe card: WHEN, then DO, IN ORDER, with Pause / Switch on and Change
//          beneath it, what it did: what is running now (Stop), then each firing with its outcome
//
// No tabs: the old Dashboard / Events / Executions are this one page. Making or changing one is
// NewAutomation (AU08-AU10), in place.
Item {
    id: root

    property string mode: "list"            // list | new
    property var events: []
    property var actions: []                // the library, flattened with .kind
    property var tree: []
    property int chosenId: 0
    property var history: null              // control.event_history of the chosen one
    property string clock: ""

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("control.event_list", {}, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            root.events = r.events
            if (!root.chosen && r.events.length) root.choose(r.events[0].id)
            else if (root.chosenId) root.loadHistory()
        })
        falcon.call("control.action_list", {}, function (ok, r) {
            if (!ok) return
            var flat = []
            ;["control", "monitoring", "custom"].forEach(function (k) { r.actions[k].forEach(function (a) { a.kind = k; flat.push(a) }) })
            root.actions = flat
        })
        falcon.call("hierarchy.tree", {}, function (ok, r) { if (ok) root.tree = r.departments })
    }
    function choose(id) { chosenId = id; history = null; loadHistory() }
    function loadHistory() {
        if (!chosenId) return
        var id = chosenId
        falcon.call("control.event_history", { event_id: id }, function (ok, r) { if (ok && id === root.chosenId) root.history = r })
    }
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onScopeChanged() { if (falcon.isConnected) root.refresh() }
        function onPushReceived(type, p) {
            if (type === "event.fired" || type === "action.status" || type.indexOf("control.") === 0) root.refresh()
        }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Keys.onEscapePressed: root.mode = "list"
    focus: true

    readonly property var chosen: {
        for (var i = 0; i < events.length; i++) if (events[i].id === chosenId) return events[i]
        return null
    }
    readonly property int onCount: events.filter(function (e) { return e.enabled }).length
    readonly property int runningCount: history ? history.running.length : 0

    // how an automation's machines read: "any Operations machine" / "OPS-03, OPS-07" / "3 machines"
    function hostOf(pcId) {
        for (var i = 0; i < tree.length; i++) {
            var all = tree[i].workers.concat(tree[i].admins)
            for (var j = 0; j < all.length; j++) if (all[j].pc_id === pcId) return all[j].hostname
        }
        return "machine " + pcId
    }
    function where(spec) {
        var t = spec.type
        if (t.indexOf("task.") === 0 || t === "flow.failed" || t === "resource.violation") return ""
        var ids = spec.pc_ids
        if (!ids || ids.length === 0) return tree.length === 1 ? "any " + tree[0].name + " machine" : "every machine"
        if (ids.length <= 2) return ids.map(hostOf).join(", ")
        return ids.length + " machines"
    }
    function line(e) { return Automate.when(e.condition_spec, where(e.condition_spec)) }
    function timeOf(iso) { return iso ? Qt.formatDateTime(new Date(iso), "HH:mm") : "" }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 22
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 16

        Item {
            visible: root.mode === "list"
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Column {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4
                Txt { text: "Automation"; color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                Row {
                    spacing: 12
                    Txt { text: "Automation"; color: "#ffffff"; font.pixelSize: Theme.fTitle; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                    Txt { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody; color: Qt.rgba(1, 1, 1, 0.55)
                          text: root.events.length === 0 ? "none set up yet"
                                : root.onCount + " switched on" + (root.onCount < root.events.length ? " · " + (root.events.length - root.onCount) + " off" : "") }
                }
            }
            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                  text: root.clock; color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody }
        }

        RowLayout {
            visible: root.mode === "list"
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            // --- when -> then ---------------------------------------------------------------------
            GridCell {
                objectName: "automationList"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "When · then"
                narration: ({ brief: root.events.length + (root.events.length === 1 ? " automation" : " automations"),
                              state: root.events.length === 0 ? "empty" : "ok",
                              note: "No automations yet", sentence: "Start one with New automation, or from an example." })
                Column {
                    width: parent.width
                    spacing: 14
                    PagedColumn {
                        width: parent.width
                        height: Math.min(root.events.length * 62, Math.max(120, root.height - 250))
                        itemHeight: 53
                        model: root.events
                        delegate: Rectangle {
                            id: rowCard
                            property var modelData: null
                            property int index: -1
                            readonly property var words: modelData ? root.line(modelData) : ({})
                            readonly property var acts: modelData ? modelData.actions : []
                            readonly property bool picked: modelData && modelData.id === root.chosenId
                            radius: 10
                            color: picked ? Theme.accentSoft : rowArea.containsMouse ? Qt.rgba(1, 1, 1, 0.04) : "transparent"
                            opacity: modelData && !modelData.enabled ? 0.55 : 1
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 12
                                Icon { name: rowCard.modelData ? Automate.iconFor(rowCard.modelData.condition_spec.type) : "bell"; size: 17; color: Theme.dim }
                                Column {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 3
                                    spacing: 2
                                    Txt { width: parent.width; elide: Text.ElideRight; text: rowCard.words.title || ""; color: Theme.ink
                                          font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                                    Txt { width: parent.width; elide: Text.ElideRight; font.pixelSize: Theme.fMeta
                                          text: rowCard.modelData && !rowCard.modelData.enabled ? "switched off" : (rowCard.words.sub || "")
                                          color: rowCard.modelData && !rowCard.modelData.enabled ? Theme.warn : Theme.faint }
                                }
                                Icon { name: "fwd"; size: 13; color: Theme.faint }
                                Row {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 2
                                    spacing: 8
                                    clip: true
                                    Icon { visible: rowCard.acts.length > 0; name: Automate.actionIcon(rowCard.acts[0]); size: 15; color: Theme.dim
                                           anchors.verticalCenter: parent.verticalCenter }
                                    Txt { text: rowCard.acts.length ? Automate.actionName(rowCard.acts[0]) : "does nothing yet"
                                          color: rowCard.acts.length ? Theme.dim : Theme.warn; font.pixelSize: Theme.fBody; anchors.verticalCenter: parent.verticalCenter }
                                    Txt { visible: rowCard.acts.length > 1; text: "+ " + (rowCard.acts.length - 1) + " more"
                                          color: Theme.faint; font.pixelSize: Theme.fMeta; anchors.verticalCenter: parent.verticalCenter }
                                }
                            }
                            MouseArea { id: rowArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                        onClicked: root.choose(rowCard.modelData.id) }
                        }
                    }
                    TBtn { objectName: "newAutomationButton"; text: "New automation"; iconName: "plus"
                           onClicked: { maker.start(null); root.mode = "new" } }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                spacing: 20

                // --- the chosen one, as a recipe ------------------------------------------------------
                GridCell {
                    objectName: "automationChosen"
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(420, 200 + (root.chosen ? root.chosen.actions.length : 0) * 50)
                    topAlign: true
                    title: "Chosen"
                    narration: ({ brief: root.history ? (root.history.fired_today === 0 ? "not fired today"
                                         : "fired " + root.history.fired_today + (root.history.fired_today === 1 ? " time" : " times") + " today") : "",
                                  tone: root.history && root.history.fired_today > 0 ? "ok" : "",
                                  state: root.chosen ? "ok" : "empty", note: "Nothing chosen", sentence: "Pick an automation on the left." })
                    Column {
                        visible: root.chosen !== null
                        width: parent.width
                        spacing: 10
                        Txt { text: "WHEN"; color: Theme.faint; font.pixelSize: Theme.fMeta; font.weight: Font.Bold }
                        Row {
                            spacing: 12
                            Icon { name: root.chosen ? Automate.iconFor(root.chosen.condition_spec.type) : "bell"; size: 18; color: Theme.accent
                                   anchors.verticalCenter: parent.verticalCenter }
                            Column {
                                spacing: 2
                                Txt { text: root.chosen ? root.line(root.chosen).title : ""; color: Theme.ink; font.pixelSize: Theme.fSection; font.weight: Font.DemiBold }
                                Txt { text: root.chosen ? root.line(root.chosen).sub : ""; color: Theme.faint; font.pixelSize: Theme.fMeta }
                            }
                        }
                        Item { width: 1; height: 2 }
                        Txt { text: "DO, IN ORDER"; color: Theme.faint; font.pixelSize: Theme.fMeta; font.weight: Font.Bold }
                        Repeater {
                            model: root.chosen ? root.chosen.actions : []
                            delegate: Row {
                                required property var modelData
                                required property int index
                                spacing: 12
                                Txt { text: String(index + 1); width: 14; color: Theme.faint; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                                      anchors.verticalCenter: parent.verticalCenter }
                                Icon { name: Automate.actionIcon(modelData); size: 17; color: Theme.ok; anchors.verticalCenter: parent.verticalCenter }
                                Column {
                                    spacing: 1
                                    Txt { text: Automate.actionName(modelData); color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                                    Txt { text: Automate.actionTiming(modelData); color: Theme.faint; font.pixelSize: Theme.fMeta }
                                }
                            }
                        }
                        Txt { visible: root.chosen && root.chosen.actions.length === 0; text: "Nothing yet. Change it to pick what it does."
                              color: Theme.warn; font.pixelSize: Theme.fBody }
                        Item {
                            width: parent.width; height: 40
                            Row {
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                spacing: 8
                                GBtn { objectName: "automationPause"; text: root.chosen && root.chosen.enabled ? "Pause it" : "Switch on"
                                       iconName: root.chosen && root.chosen.enabled ? "pause" : "play"
                                       onClicked: root.chosen.enabled
                                                  ? falcon.call("control.event_delete", { event_id: root.chosen.id }, root.after)
                                                  : falcon.call("control.event_update", { event_id: root.chosen.id, enabled: true }, root.after) }
                                TBtn { text: "Change"; onClicked: { maker.start(root.chosen); root.mode = "new" } }
                            }
                        }
                    }
                }

                // --- what it did ----------------------------------------------------------------------
                GridCell {
                    id: didCell
                    objectName: "automationDid"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    topAlign: true
                    title: "What it did"
                    readonly property var firings: root.history ? root.history.firings : []
                    narration: ({ brief: root.runningCount > 0 ? root.runningCount + " running now" : "",
                                  tone: root.runningCount > 0 ? "accent" : "",
                                  state: root.chosen && firings.length === 0 ? "empty" : "ok",
                                  note: "It has not fired yet", sentence: "Each time it does, it is written here with what each action did." })
                    Column {
                        width: parent.width
                        spacing: 0
                        Repeater {
                            model: root.history ? root.history.running : []
                            delegate: Item {
                                required property var modelData
                                width: parent.width; height: 38
                                Rectangle { width: 7; height: 7; radius: 4; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter }
                                Txt { x: 16; anchors.verticalCenter: parent.verticalCenter; color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                                      text: "Running now: " + Automate.actionName({ name: modelData.action_name, builtin_type: modelData.builtin_type })
                                            + " on " + (modelData.hostname || "a machine") }
                                GBtn { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "Stop"; iconName: "stop"; small: true
                                       onClicked: falcon.call("control.terminate", { execution_id: modelData.id }, root.after) }
                            }
                        }
                        PagedColumn {
                            width: parent.width
                            height: Math.max(80, didCell.height - 90 - (root.history ? root.history.running.length * 38 : 0))
                            itemHeight: 36
                            spacing: 2
                            model: didCell.firings
                            delegate: Item {
                                property var modelData: null
                                property int index: -1
                                readonly property var runs: modelData ? modelData.runs : []
                                readonly property var bad: runs.filter(function (r) { return r.status === "failed" || r.status === "terminated" })
                                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                                Txt { id: at; anchors.verticalCenter: parent.verticalCenter; width: 56; monospace: true; color: Theme.faint; font.pixelSize: Theme.fMeta
                                      text: parent.modelData ? root.timeOf(parent.modelData.at) : "" }
                                Txt { anchors.left: at.right; anchors.right: verdict.left; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                                      elide: Text.ElideRight; color: Theme.ink; font.pixelSize: Theme.fBody
                                      text: !parent.modelData ? "" : [parent.modelData.hostname || "every machine", parent.modelData.subject,
                                                                     parent.runs.map(Automate.outcome).join(", ") || "nothing ran"]
                                                                    .filter(function (x) { return !!x }).join(" · ") }
                                Txt { id: verdict; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold
                                      text: parent.bad.length ? Automate.outcome(parent.bad[0]) : parent.runs.some(function (r) { return r.status === "pending" }) ? "running" : "clean"
                                      color: parent.bad.length ? Theme.warn : Theme.ok }
                            }
                        }
                    }
                }
            }
        }

        NewAutomation {
            id: maker
            objectName: "newAutomation"
            visible: root.mode === "new"
            Layout.fillWidth: true
            Layout.fillHeight: true
            tree: root.tree
            actions: root.actions
            onDone: function (id) { root.mode = "list"; root.refresh(); if (id) root.choose(id) }
            onCancelled: root.mode = "list"
        }
    }

    function after(ok, r) {
        shell.notify(ok ? "Done" : r.message, !ok)
        root.refresh()
    }
}
