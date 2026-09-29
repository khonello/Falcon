import QtQuick
import "."

// WHAT COPIES WHERE. A flow runs one direction only, so the page reads that way too: a source on the
// left, what it lands in on the right, and -- when it has stopped -- the Engine's own sentence about
// why, never one this console made up.
Item {
    id: root

    property var flows: []
    property bool loaded: false
    property var chosen: null

    readonly property var rows: flows.map(function (f) {
        var s = Sync.state(f)
        var dests = f.destinations || []
        return { flow_id: f.id, status: f.status,
                 from: (f.source_hostname || "a machine") + "  " + Sync.folder(f.source_path),
                 fromPath: f.source_path,
                 to: dests.length === 0 ? "nowhere"
                     : dests.length === 1 ? Sync.where(dests[0])
                     : dests.length + " places",
                 count: dests.length,
                 stages: (f.stages || []).length,
                 stateWord: s.word, stateTone: s.tone, line: s.line,
                 flow: f }
    })
    readonly property int stopped: rows.filter(function (r) { return r.stateTone === "danger" }).length

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("flow.list", {}, function (ok, r) {
            root.loaded = true
            if (ok) root.flows = r.flows || []
        })
    }
    function act(type, payload, said) {
        falcon.call(type, payload, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "It did not go through"); return }
            Msg.ok(said)
            detail.close()
            root.refresh()
        })
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.flows = []; root.loaded = false }
        function onPushReceived(type) { if (String(type).indexOf("flow.") === 0) root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s5
        spacing: Theme.s3

        PageHeader {
            width: parent.width
            title: "Flows"
            subtitle: root.rows.length + " flows"
                      + (root.stopped > 0 ? " · " + root.stopped + " stopped" : "")
            Btn {
                objectName: "newFlow"
                kind: "primary"
                iconName: "plus"
                text: "New flow"
                onClicked: maker.open()
            }
        }

        Rectangle {
            width: parent.width
            height: parent.height - y
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Table {
                objectName: "flowsTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                loading: !root.loaded
                pageSize: 12
                rows: root.rows
                emptyText: "No flows yet"
                emptyHint: "A flow copies a folder one way: what changes on the source lands where you send it."
                onRowActivated: function (row) { root.chosen = row; detail.open() }
                columns: [
                    { title: "From", key: "from", width: 240, mono: true, strong: true },
                    { title: "To", key: "to", width: 260, mono: true,
                      tone: function () { return "mid" } },
                    { title: "State", key: "stateWord", width: 120, tag: true,
                      filters: ["running", "waiting", "stopped", "retired"],
                      tone: function (r) { return r.stateTone } },
                    { title: "Why", key: "line",
                      tone: function (r) { return r.stateTone === "" ? "mid" : r.stateTone } }
                ]
            }
        }
    }

    NewFlow {
        id: maker
        objectName: "newFlowModal"
        onMade: root.refresh()
    }

    Confirm {
        id: retire
        objectName: "retireConfirm"
        title: "Retire this flow"
        cost: "It stops copying. The flow and everything it has already synced stay on record -- nothing "
              + "is deleted from either machine -- but it does not come back on its own."
        verb: "Retire"
        destructive: true
        onAccepted: root.act("flow.delete", { flow_id: root.chosen.flow_id }, "Flow retired")
    }

    Drawer {
        id: detail
        objectName: "flowDrawer"
        title: root.chosen ? root.chosen.from : ""
        subtitle: root.chosen ? root.chosen.line : ""

        Descriptions {
            width: parent.width
            items: root.chosen ? [
                { label: "From", value: root.chosen.fromPath, mono: true },
                { label: "State", value: root.chosen.stateWord, tag: true, tone: root.chosen.stateTone },
                { label: "Steps on the way", value: root.chosen.stages === 0 ? "none, a straight copy"
                                                                             : root.chosen.stages }
            ] : []
        }

        Txt {
            width: parent.width
            text: "Where it lands"
            tone: "mid"
            font.pixelSize: Theme.fSmall
        }
        Column {
            width: parent.width
            spacing: 0

            Repeater {
                model: root.chosen && root.chosen.flow ? (root.chosen.flow.destinations || []) : []
                delegate: Item {
                    required property var modelData
                    width: parent.width
                    height: stack.implicitHeight + Theme.s2 * 2

                    Column {
                        id: stack
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1

                        Txt {
                            width: parent.width
                            text: Sync.where(modelData)
                            mono: true
                            font.pixelSize: Theme.fSmall
                        }
                        Txt {
                            width: parent.width
                            visible: text !== ""
                            text: modelData.suggestion || ""
                            tone: "danger"
                            font.pixelSize: Theme.fSmall
                            wrapMode: Text.WordWrap
                            elide: Text.ElideNone
                        }
                        Txt {
                            width: parent.width
                            visible: !modelData.suggestion && modelData.last_sync
                            text: modelData.last_sync ? "last copied " + Task.when(modelData.last_sync.synced_at)
                                                      : ""
                            tone: "quiet"
                            font.pixelSize: Theme.fSmall
                        }
                    }
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: Theme.split
                    }
                }
            }
        }

        Alert {
            width: parent.width
            visible: root.chosen !== null && root.chosen.stateWord === "waiting"
            kind: "warn"
            text: "Nothing copies until whoever owns the destination says yes."
        }

        // the Drawer's footer is a Row: order places these, not anchors
        footer: [
            Btn {
                objectName: "retireFlow"
                danger: true
                text: "Retire"
                visible: root.chosen && root.chosen.status !== "inactive"
                onClicked: retire.open()
            },
            Btn {
                objectName: "pauseFlow"
                kind: "primary"
                text: root.chosen && root.chosen.status === "paused" ? "Resume" : "Pause"
                visible: root.chosen && root.chosen.status !== "inactive"
                onClicked: root.chosen.status === "paused"
                           ? root.act("flow.resume", { flow_id: root.chosen.flow_id }, "Flow resumed")
                           : root.act("flow.pause", { flow_id: root.chosen.flow_id }, "Flow paused")
            }
        ]
    }
}
