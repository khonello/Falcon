import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// LEVEL 4 -- A CLIENT PC, HELD (board CP03). Under level 3's lid, one level down. A machine has no interface of
// its own to show, so the page is about it:
//
//   the machine, live   its screen mark at 84 with its live facts (idle, processor, memory) and what is out of
//                       place on it; their screen is not carried -- a live state, not a viewport
//   run here            the Actions library, aimed at this one machine
//   its files           what is out of place here, and the folders Falcon watches on it
//   its work            tasks its person holds and flows that touch it; what they see on their screen now
Item {
    id: root

    property var pc: null                   // shell.heldPc: the worker entry, with department_name
    property var levels: null
    property var actions: []
    property var violations: []
    property var folders: []
    property var tasks: []
    property var flows: []
    property var ran: ({})                  // action id -> what running it here came back as
    property string clock: ""
    property string holder: ""              // who is holding it, as the person at the machine would name them

    function refresh() {
        if (!falcon.isConnected || !pc) return
        var id = pc.pc_id
        falcon.call("control.levels", { pc_ids: [id] }, function (ok, r) { if (ok) root.levels = r })
        falcon.call("control.action_list", {}, function (ok, r) {
            if (!ok) return
            var flat = []
            ;["control", "monitoring", "custom"].forEach(function (k) { r.actions[k].forEach(function (a) { a.kind = k; flat.push(a) }) })
            root.actions = flat
        })
        falcon.call("resource.violations", {}, function (ok, r) {
            if (ok) root.violations = r.violations.filter(function (v) { return v.found_on_pc_id === id || v.hostname === root.pc.hostname })
        })
        falcon.call("index.folders", { pc_id: id }, function (ok, r) { root.folders = ok ? r.folders : [] })
        falcon.call("task.list", {}, function (ok, r) { if (ok) root.tasks = r.tasks.filter(function (t) { return t.assignee_account_id === root.pc.account_id }) })
        falcon.call("flow.list", {}, function (ok, r) {
            if (ok) root.flows = r.flows.filter(function (f) {
                return f.source_pc_id === id || (f.destinations || []).some(function (d) { return d.destination_pc_id === id })
            })
        })
    }
    onPcChanged: { ran = {}; refresh() }
    onVisibleChanged: if (visible) refresh()
    Timer { interval: 15000; repeat: true; running: root.visible; onTriggered: if (falcon.isConnected && root.pc)
            falcon.call("control.levels", { pc_ids: [root.pc.pc_id] }, function (ok, r) { if (ok) root.levels = r }) }
    Connections {
        target: falcon
        function onPushReceived(type, p) {
            if (type === "action.status" && root.ran[p.action_id] !== undefined) {
                var c = {}; for (var k in root.ran) c[k] = root.ran[k]; c[p.action_id] = p.status; root.ran = c
            }
        }
    }

    readonly property string first: pc ? String(pc.name || "").split(" ")[0] : ""
    readonly property bool reporting: levels !== null && levels.machines > 0
    function pct(pair) { return pair ? Math.round(pair[1]) + " %" : "—" }
    function late(t) { return t.final_deadline_at && Date.parse(t.final_deadline_at) < Date.now() }
    function runHere(a) {
        falcon.call("control.action_run", { action_id: a.id, pc_id: pc.pc_id }, function (ok, r) {
            var c = {}; for (var k in root.ran) c[k] = root.ran[k]; c[a.id] = ok ? "pending" : "refused"; root.ran = c
            if (!ok) shell.notify(r.message, true)
        })
    }
    function ranWord(id) {
        var s = ran[id]
        return s === undefined ? "Run" : s === "pending" ? "running" : s === "success" ? "done" : s === "terminated" ? "stopped" : s
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
                    Txt { text: root.pc ? root.pc.department_name : ""; color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody
                          MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: shell.stepOut() } }
                    Icon { name: "chev"; color: Qt.rgba(1, 1, 1, 0.45); size: 12; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: root.pc ? root.pc.hostname : ""; color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                }
                Row {
                    spacing: 12
                    Txt { text: root.pc ? root.pc.hostname : ""; color: "#ffffff"; font.pixelSize: Theme.fTitle; font.weight: Font.Bold
                          anchors.verticalCenter: parent.verticalCenter }
                    Txt { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody; color: Theme.danger
                          text: root.first + "'s machine · you are holding it" }
                }
            }
            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: root.clock
                  color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            // --- the machine, live ------------------------------------------------------------------------
            GridCell {
                objectName: "pcLive"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "The machine, live"
                narration: ({ brief: root.violations.length ? (root.violations.length === 1 ? "a file out of place" : root.violations.length + " files out of place") : "",
                              tone: "danger", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 12
                    Row {
                        spacing: 18
                        MachineMark { size: 84; label: root.pc ? String(root.pc.hostname).split("-").pop() : ""
                                      status: root.violations.length ? "danger" : "ok" }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 3
                            Txt { text: root.pc ? root.pc.hostname : ""; color: Theme.ink; monospace: true; font.pixelSize: Theme.fSection + 2; font.weight: Font.Bold }
                            Txt { text: root.pc ? root.pc.name + " · " + root.pc.department_name : ""; color: Theme.dim; font.pixelSize: Theme.fBody }
                            Txt { visible: root.violations.length > 0; text: root.violations.length === 1 ? "a file out of place" : root.violations.length + " files out of place"
                                  color: Theme.danger; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                        }
                    }
                    Repeater {
                        model: [["Idle for", root.reporting && root.levels.idle_s ? Automate.minutes(root.levels.idle_s[1]) : "—"],
                                ["Processor", root.reporting ? root.pct(root.levels.cpu) : "—"],
                                ["Memory", root.reporting ? root.pct(root.levels.memory) : "—"]]
                        delegate: Item {
                            required property var modelData
                            width: parent.width; height: 36
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                            Txt { anchors.verticalCenter: parent.verticalCenter; text: modelData[0]; color: Theme.dim; font.pixelSize: Theme.fBody }
                            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: modelData[1]
                                  color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                        }
                    }
                    Txt { visible: !root.reporting; width: parent.width; wrapMode: Text.WordWrap; color: Theme.warn; font.pixelSize: Theme.fMeta
                          text: "The machine has not reported its levels yet." }
                    Rectangle {
                        width: parent.width; height: 130; radius: 12; color: "transparent"; border.width: 1; border.color: Theme.line2
                        Column {
                            anchors.centerIn: parent; spacing: 8
                            Icon { anchors.horizontalCenter: parent.horizontalCenter; name: "camera"; size: 16; color: Theme.faint }
                            Txt { text: "Their screen is not carried"; color: Theme.faint; font.pixelSize: Theme.fBody }
                        }
                    }
                    Txt { text: "A live state, not a viewport: nothing streams their screen. A Screenshot is one still, on request."
                          width: parent.width; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                spacing: 20
                // --- run here -------------------------------------------------------------------------------
                GridCell {
                    id: runCell
                    objectName: "pcRun"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 3
                    topAlign: true
                    title: "Run here"
                    narration: ({ brief: "the library, aimed", tone: "accent", state: root.actions.length ? "ok" : "empty",
                                  note: "No actions yet", sentence: "Set some up on the Actions page." })
                    Column {
                        width: parent.width
                        spacing: 6
                        PagedColumn {
                            width: parent.width
                            height: Math.min(root.actions.length * 51, Math.max(51, runCell.room - 30))
                            itemHeight: 46
                            spacing: 5
                            model: root.actions
                            delegate: Item {
                                property var modelData: null
                                property int index: -1
                                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                                Icon { id: rIcon; anchors.verticalCenter: parent.verticalCenter; size: 15; color: Theme.dim
                                       name: parent.modelData ? Automate.actionIcon(parent.modelData) : "play" }
                                Column {
                                    anchors.left: rIcon.right; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter
                                    Txt { color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                                          text: parent.parent.modelData ? Automate.actionName(parent.parent.modelData).replace(/ me$/, " " + root.first) : "" }
                                    Txt { color: Theme.faint; font.pixelSize: Theme.fMeta; text: parent.parent.modelData ? Automate.actionDoes(parent.parent.modelData) : "" }
                                }
                                Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                                      text: parent.modelData ? root.ranWord(parent.modelData.id) : ""
                                      color: parent.modelData && root.ran[parent.modelData.id] === undefined ? Theme.accent
                                             : parent.modelData && root.ran[parent.modelData.id] === "success" ? Theme.ok : Theme.warn
                                      MouseArea { anchors.fill: parent; anchors.margins: -8; cursorShape: Qt.PointingHandCursor
                                                  onClicked: root.runHere(parent.parent.modelData) } }
                            }
                        }
                        Txt { text: "The Actions library, aimed at this one machine."; color: Theme.faint; font.pixelSize: Theme.fMeta }
                    }
                }
                // --- its files ------------------------------------------------------------------------------
                GridCell {
                    objectName: "pcFiles"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: 2
                    topAlign: true
                    title: "Its files"
                    narration: ({ brief: root.violations.length ? (root.violations.length === 1 ? "one out of place" : root.violations.length + " out of place") : "",
                                  tone: "danger", state: "ok" })
                    Column {
                        width: parent.width
                        spacing: 9
                        Repeater {
                            model: root.violations.slice(0, 2)
                            delegate: InfoCard {
                                required property var modelData
                                width: parent.width
                                iconName: "file"; iconTone: "danger"
                                title: modelData.filename
                                line: String(modelData.expected_tag || "").replace("worker_dept", "workers").replace(/^./, function (c) { return c.toUpperCase() }) + " · out of place here"
                                stateWord: "out of place"; stateTone: "danger"
                                onClicked: { shell.stepOut(); shell.show("resources") }
                            }
                        }
                        InfoCard {
                            width: parent.width
                            iconName: "folder"; iconTone: "ok"
                            title: root.folders.length + (root.folders.length === 1 ? " folder" : " folders") + " watched here"
                            line: root.folders.slice(0, 3).map(function (f) { return f.name }).join(", ") || "nothing indexed yet"
                        }
                    }
                }
            }

            // --- its work, and what they see -------------------------------------------------------------------
            GridCell {
                objectName: "pcWork"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "Its work"
                readonly property int overdue: root.tasks.filter(root.late).length
                narration: ({ brief: overdue ? (overdue === 1 ? "one overdue" : overdue + " overdue") : "", tone: "danger", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 9
                    Repeater {
                        model: root.tasks.slice(0, 3)
                        delegate: InfoCard {
                            required property var modelData
                            width: parent.width
                            iconName: "tasks"; iconTone: root.late(modelData) ? "danger" : "accent"
                            title: String(modelData.description_raw || "").split(/[.\n]/)[0].substring(0, 42)
                            line: root.late(modelData) ? "final deadline has passed" : modelData.started_at ? "under way" : "not started"
                            stateWord: root.late(modelData) ? "overdue" : ""; stateTone: "danger"
                        }
                    }
                    Repeater {
                        model: root.flows.slice(0, 2)
                        delegate: InfoCard {
                            required property var modelData
                            width: parent.width
                            iconName: "flows"; iconTone: modelData.status === "active" ? "ok" : "warn"
                            readonly property bool out: modelData.source_pc_id === root.pc.pc_id
                            title: Automate.folderName(modelData.source_path) + " → "
                                   + (out ? (modelData.destinations || []).map(function (d) { return d.destination_hostname || "remote storage" }).join(", ") : "this machine")
                            line: out ? "from this machine" : "from " + (modelData.source_hostname || "")
                            stateWord: modelData.status === "active" ? "syncing" : "paused"; stateTone: modelData.status === "active" ? "" : "warn"
                        }
                    }
                    Txt { visible: root.tasks.length === 0 && root.flows.length === 0; text: "No task or flow touches this machine."
                          color: Theme.faint; font.pixelSize: Theme.fBody }
                    Txt { topPadding: 8; text: "What " + root.first + " sees now"; color: Theme.dim; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
                    Rectangle {
                        width: parent.width; height: seen.implicitHeight + 26; radius: 12; color: "transparent"
                        border.width: 1; border.color: Theme.line2
                        Txt { id: seen; x: 13; y: 13; width: parent.width - 26; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: Theme.fBody
                              text: (falcon && falcon.role === "super_user" ? "The Super User" : "Your Admin, " + (root.holder || "your Admin") + ",")
                                    + " is in charge of this machine for now. You can use it again when they leave." }
                    }
                }
            }
        }
    }
}
