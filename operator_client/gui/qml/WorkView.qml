import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// WORK (board WK03), the Super User's, three equal columns:
//
//   by department  each department as a card with its work as ticks (a tick per task and per flow, the late ones
//                  taller in their tone) and the one Open / Closed filter
//   yours          the tasks you gave (only you close them) and the flows you set, read as a sentence
//   help, watched  assistance a Super User watches -- channels it listens on and help across departments now --
//                  never taking part
Item {
    id: root

    property var tree: []
    property var tasks: []
    property var flows: []
    property var channels: []
    property var sessions: []
    property bool closed: false
    property int chosenTask: 0
    property string clock: ""

    // ST02: the cells keep their shape, quietened, until the first reply lands
    property bool loaded: false

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function (ok, r) { root.loaded = true; if (ok) root.tree = r.departments })
        falcon.call("task.list", { include_completed: true }, function (ok, r) { if (ok) root.tasks = r.tasks })
        falcon.call("flow.list", {}, function (ok, r) { if (ok) root.flows = r.flows })
        falcon.call("assistance.channels", {}, function (ok, r) { if (ok) root.channels = r.channels })
        falcon.call("hierarchy.sessions_today", { hours: 12 }, function (ok, r) { if (ok) root.sessions = r.sessions })
    }
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onPushReceived(type, p) { if (type.indexOf("task.") === 0 || type.indexOf("flow.") === 0 || type.indexOf("assistance.") === 0) root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    onVisibleChanged: if (visible) refresh()

    readonly property int me: falcon ? falcon.accountId : 0
    function person(id) {
        for (var i = 0; i < tree.length; i++) {
            var all = tree[i].admins.concat(tree[i].workers)
            for (var j = 0; j < all.length; j++) if (all[j].account_id === id) return { p: all[j], dept: tree[i] }
        }
        return null
    }
    // "Kojo" for Kojo, but "R. Mensah" for R. Mensah: an initial alone names no one
    function short(name) { var f = String(name).split(" ")[0]; return /\.$/.test(f) ? name : f }
    function nameOf(id) { var x = person(id); return x ? x.p.name : "someone" }
    function deptOfAccount(id) { var x = person(id); return x ? x.dept.department_id : 0 }
    function deptOfPc(pcId) {
        for (var i = 0; i < tree.length; i++) {
            var all = tree[i].admins.concat(tree[i].workers)
            for (var j = 0; j < all.length; j++) if (all[j].pc_id === pcId) return tree[i].department_id
        }
        return 0
    }
    function deptName(id) { for (var i = 0; i < tree.length; i++) if (tree[i].department_id === id) return tree[i].name; return "" }
    function late(t) {
        var now = Date.now()
        if (t.final_deadline_at && Date.parse(t.final_deadline_at) < now) return "danger"
        if (t.soft_deadline_at && Date.parse(t.soft_deadline_at) < now) return "warn"
        return ""
    }

    // --- by department -----------------------------------------------------------------------------------
    readonly property var shown: tasks.filter(function (t) { return root.closed ? t.status === "completed" : t.status !== "completed" })
    readonly property var depts: tree.map(function (d) {
        var ts = root.shown.filter(function (t) { return root.deptOfAccount(t.assignee_account_id) === d.department_id })
        var fs = root.closed ? [] : root.flows.filter(function (f) { return root.deptOfPc(f.source_pc_id) === d.department_id })
        var over = ts.filter(function (t) { return root.late(t) === "danger" }).length
        var paused = fs.filter(function (f) { return f.status !== "active" }).length
        return { id: d.department_id, name: d.name, tasks: ts, flows: fs, noAdmin: d.admins.length === 0,
                 word: root.closed ? ts.length + " closed" : d.admins.length === 0 ? "no Admin" : over ? (over === 1 ? "one overdue" : over + " overdue")
                       : paused ? (paused === 1 ? "a flow paused" : paused + " flows paused") : "on track",
                 tone: root.closed ? "" : d.admins.length === 0 || over ? "danger" : paused ? "warn" : "ok" }
    })
    readonly property int overdue: tasks.filter(function (t) { return t.status !== "completed" && root.late(t) === "danger" }).length

    // --- yours --------------------------------------------------------------------------------------------
    readonly property var mine: tasks.filter(function (t) { return t.assigner_account_id === root.me && t.status !== "completed" })
    readonly property var myFlows: flows.filter(function (f) { return f.created_by_account_id === root.me })
    readonly property var chosen: { for (var i = 0; i < mine.length; i++) if (mine[i].id === chosenTask) return mine[i]; return mine.length ? mine[0] : null }

    // --- help, watched ------------------------------------------------------------------------------------
    readonly property var watched: {
        var out = []
        for (var i = 0; i < channels.length; i++) {
            var c = channels[i]
            if (c.closed_at || c.initiator_account_id === me || c.superior_account_id === me) continue
            var sub = c.initiator_account_id === c.superior_account_id ? c.initiator_account_id : c.initiator_account_id
            var theirTurn = c.turn === "superior" ? c.superior_account_id : c.initiator_account_id
            out.push({ initials: Theme.initials(nameOf(c.initiator_account_id)),
                       title: nameOf(c.initiator_account_id) + " ↔ " + nameOf(c.superior_account_id),
                       line: deptName(deptOfAccount(c.initiator_account_id)) + " · " + short(nameOf(theirTurn)) + "'s turn", tone: "" })
        }
        for (var j = 0; j < sessions.length; j++) {
            var s = sessions[j]
            if (s.occupied_via !== "assisted_access" || s.ended_at) continue
            out.push({ initials: Theme.initials(s.occupant_name || ""), title: (s.occupant_name || "Someone") + " → " + (deptName(s.department_id) || s.hostname),
                       line: "helping by consent since " + Qt.formatDateTime(new Date(s.entered_at), "HH:mm"), tone: "accent" })
        }
        return out
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
                Txt { text: "Work"; color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                Row {
                    spacing: 12
                    Txt { text: "Work"; color: "#ffffff"; font.pixelSize: Theme.fTitle; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                    Txt { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody; color: root.overdue ? Theme.warn : Qt.rgba(1, 1, 1, 0.55)
                          text: root.tasks.filter(function (t) { return t.status !== "completed" }).length + " tasks · " + root.flows.length + " flows"
                                + (root.overdue ? " · " + (root.overdue === 1 ? "one overdue" : root.overdue + " overdue") : "") }
                }
            }
            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: root.clock
                  color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            GridCell {
                id: deptCell
                objectName: "workDepartments"
                loading: !root.loaded
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "By department"
                narration: ({ brief: root.overdue ? (root.overdue === 1 ? "one overdue" : root.overdue + " overdue") : "", tone: "danger", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 12
                    SegmentedControl { id: filter; segments: [{ text: "Open" }, { text: "Closed" }]; onCurrentIndexChanged: root.closed = currentIndex === 1 }
                    PagedColumn {
                        width: parent.width
                        height: Math.min(root.depts.length * 104, Math.max(110, deptCell.room - 80))
                        itemHeight: 94
                        spacing: 10
                        model: root.depts
                        attention: function (d) { return d.tone === "danger" ? d.name + ": " + d.word : "" }
                        delegate: Rectangle {
                            property var modelData: null
                            property int index: -1
                            radius: 14; color: Theme.pane
                            Txt { x: 14; y: 12; text: parent.modelData ? parent.modelData.name : ""; color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                            Txt { anchors.right: parent.right; anchors.rightMargin: 14; y: 12; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold
                                  text: parent.modelData ? parent.modelData.word : ""
                                  color: parent.modelData && parent.modelData.tone ? Theme.tone(parent.modelData.tone) : Theme.faint }
                            Ticks { x: 14; y: 40; width: parent.width - 28; label: "Tasks"
                                    items: parent.modelData ? parent.modelData.tasks.map(function (t) { return root.late(t) }) : [] }
                            Ticks { x: 14; y: 64; width: parent.width - 28; label: "Flows"; visible: !root.closed
                                    items: parent.modelData ? parent.modelData.flows.map(function (f) { return f.status === "active" ? "" : "warn" }) : [] }
                        }
                    }
                    Txt { text: root.closed ? "Closed work is kept in Record." : "Closed hands off to Record."; color: Theme.faint; font.pixelSize: Theme.fMeta }
                }
            }

            GridCell {
                objectName: "workYours"
                loading: !root.loaded
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "Yours"
                narration: ({ brief: [root.mine.length ? root.mine.length + (root.mine.length === 1 ? " task" : " tasks") : "",
                                      root.myFlows.length ? root.myFlows.length + (root.myFlows.length === 1 ? " flow" : " flows") : ""]
                                     .filter(function (x) { return !!x }).join(", "),
                              tone: "accent", state: root.mine.length || root.myFlows.length ? "ok" : "empty",
                              note: "Nothing of yours", sentence: "Tasks you give and flows you set show here." })
                Column {
                    width: parent.width
                    spacing: 10
                    Txt { visible: root.mine.length > 0; text: "Given by you"; color: Theme.dim; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
                    Repeater {
                        model: root.mine.slice(0, 3)
                        delegate: InfoCard {
                            required property var modelData
                            width: parent.width
                            iconName: "tasks"; iconTone: root.late(modelData) || "accent"
                            title: String(modelData.description_raw || "").split(/[.\n]/)[0].substring(0, 48)
                            line: [root.deptName(root.deptOfAccount(modelData.assignee_account_id)), modelData.assignee_name || root.nameOf(modelData.assignee_account_id),
                                   modelData.started_at ? "started " + Qt.formatDateTime(new Date(modelData.started_at), "ddd") : "not started"].join(" · ")
                            stateWord: modelData.final_deadline_at ? Qt.formatDateTime(new Date(modelData.final_deadline_at), "ddd") : ""
                            stateTone: root.late(modelData)
                            selected: root.chosen && root.chosen.id === modelData.id
                            onClicked: root.chosenTask = modelData.id
                        }
                    }
                    Item {
                        visible: root.chosen !== null
                        width: parent.width; height: 34
                        TBtn { objectName: "workVerify"; tone: "ok"; small: true; iconName: "check"; anchors.verticalCenter: parent.verticalCenter
                               text: "Verify it"
                               onClicked: falcon.call("task.verify", { task_id: root.chosen.id, outcome: "complete" }, function (ok, r) {
                                   shell.notify(ok ? "Verified and closed" : r.message, !ok); root.refresh() }) }
                        Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "you set it, so only you close it"
                              color: Theme.faint; font.pixelSize: Theme.fMeta }
                    }
                    Txt { visible: root.myFlows.length > 0; topPadding: 8; text: root.myFlows.length === 1 ? "A flow you set" : "Flows you set"
                          color: Theme.dim; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
                    Repeater {
                        model: root.myFlows.slice(0, 2)
                        delegate: Column {
                            required property var modelData
                            width: parent.width
                            spacing: 6
                            Flow {
                                width: parent.width
                                spacing: 7
                                Txt { text: "Copy"; color: Theme.dim; font.pixelSize: 16; height: 30; verticalAlignment: Text.AlignVCenter }
                                SentenceSlot { text: Automate.folderName(modelData.source_path); fontSize: 15; onClicked: {} }
                                Txt { text: "from"; color: Theme.dim; font.pixelSize: 16; height: 30; verticalAlignment: Text.AlignVCenter }
                                SentenceSlot { text: modelData.source_hostname || ""; fontSize: 15; onClicked: {} }
                                Txt { text: "to"; color: Theme.dim; font.pixelSize: 16; height: 30; verticalAlignment: Text.AlignVCenter }
                                SentenceSlot { tone: "ok"; fontSize: 15; onClicked: {}
                                               text: (modelData.destinations || []).map(function (d) { return d.destination_hostname || "remote" }).join(", ") }
                            }
                            Txt { color: Theme.faint; font.pixelSize: Theme.fMeta
                                  text: modelData.consent_status === "pending" ? "waiting for the destination's owner to agree"
                                        : modelData.status === "active" ? "syncing" : "paused" }
                        }
                    }
                }
            }

            GridCell {
                objectName: "workWatched"
                loading: !root.loaded
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "Help, watched"
                narration: ({ brief: root.watched.length ? root.watched.length + " live" : "", tone: "accent",
                              state: root.watched.length ? "ok" : "empty", note: "No help under way", sentence: "Assistance you watch shows here." })
                Column {
                    width: parent.width
                    spacing: 10
                    Row { spacing: 8
                          Icon { name: "eye"; size: 15; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter }
                          Txt { text: "Watching, never taking part"; color: Theme.accent; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold } }
                    Repeater {
                        model: root.watched.slice(0, 6)
                        delegate: InfoCard {
                            required property var modelData
                            width: parent.width
                            initials: modelData.initials; title: modelData.title; line: modelData.line; lineTone: modelData.tone
                        }
                    }
                    Txt { text: "A Super User watches assistance; it never starts it."; color: Theme.faint; font.pixelSize: Theme.fMeta }
                }
            }
        }
    }

    // a row of ticks: one per item, taller and in tone when it is late or paused
    component Ticks: Item {
        id: tk
        property string label: ""
        property var items: []
        height: 20
        Txt { text: tk.label; color: Theme.faint; font.pixelSize: Theme.fMeta; anchors.verticalCenter: parent.verticalCenter }
        Row {
            x: 56; anchors.bottom: parent.bottom; spacing: 6
            Repeater {
                model: tk.items.slice(0, 40)
                delegate: Rectangle { required property var modelData; width: 2.5; radius: 1.2
                                      height: modelData ? 16 : 9; color: modelData ? Theme.tone(modelData) : Theme.line2 }
            }
            Txt { visible: tk.items.length === 0; text: "none"; color: Theme.faint; font.pixelSize: Theme.fMeta }
        }
    }
}
