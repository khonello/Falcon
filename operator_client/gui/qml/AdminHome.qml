import QtQuick
import QtQuick.Layouts
import "."

// THE ADMIN'S HOME (board HO03): their department, from inside. An Admin at home and a Super User inside that Admin see
// this same page -- the lid is the only difference (LEVELS.md, level 3).
//
// A band over three: the machines are the room -- every one a small screen at full size with its person and its line
// beneath, paged sideways, the hidden one that needs someone named at the edge -- and three cells beneath: what needs
// you, today, and who governs with you.
Item {
    id: root

    property int departmentId: 0            // 0 = the connected Admin's own department
    property var tree: []
    property var rollout: ({})
    property var violations: []
    property var sessions: []
    property var tasks: []
    property var flows: []
    property string clock: ""

    readonly property int deptId: departmentId !== 0 ? departmentId : falcon.departmentId
    readonly property var dept: {
        for (var i = 0; i < tree.length; i++) if (tree[i].department_id === deptId) return tree[i]
        return tree.length > 0 ? tree[0] : null
    }
    readonly property var workers: dept ? dept.workers : []
    readonly property var admins: dept ? dept.admins : []
    readonly property var machines: Fleet.machines(workers, rollout, violations)
    readonly property int needCount: machines.filter(function (m) { return Fleet.needsSomeone(m) }).length
    readonly property var me: {
        // the Admin whose home this is: the one inside, or the one connected
        var held = shell.heldAdmin
        if (held) return held
        for (var i = 0; i < admins.length; i++) if (admins[i].account_id === falcon.accountId) return admins[i]
        return null
    }
    readonly property var others: admins.filter(function (a) { return !root.me || a.account_id !== root.me.account_id })

    // what needs you, as cards: pings, files out of place, overdue tasks, flows that stopped
    readonly property var needs: {
        var out = []
        if (falcon.unaddressedPings > 0)
            out.push({ icon: "ping", tone: "warn", title: falcon.unaddressedPings + (falcon.unaddressedPings === 1 ? " ping waits" : " pings wait"),
                       line: "someone asked for help", word: "answer", key: "assistance" })
        for (var v = 0; v < violations.length; v++) {
            var vi = violations[v]
            var ours = workers.some(function (w) { return w.pc_id === vi.found_on_pc_id || w.hostname === vi.hostname })
            if (ours) out.push({ icon: "shield", tone: "danger", title: "A " + String(vi.expected_tag || "restricted").replace("worker_dept", "workers")
                                                                        + " file on " + vi.hostname,
                                 line: (vi.filename || "a file"), word: "new", key: "resources" })
        }
        var now = Date.now()
        for (var t = 0; t < tasks.length; t++) {
            var task = tasks[t]
            var hard = task.final_deadline_at ? Date.parse(task.final_deadline_at) : NaN
            if (!isNaN(hard) && hard < now && task.status !== "completed")
                out.push({ icon: "clock", tone: "danger", title: (task.assignee_name || "A task") + "'s task is overdue",
                           line: task.description_raw ? String(task.description_raw).substring(0, 48) : "final deadline passed", word: "", key: "tasks" })
        }
        for (var f = 0; f < flows.length; f++)
            if (flows[f].status === "paused")
                out.push({ icon: "flows", tone: "warn", title: "A flow is paused", line: "from " + (flows[f].source_hostname || "a machine"),
                           word: "", key: "flows" })
        return out
    }

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function (ok, r) { if (ok) root.tree = r.departments })
        falcon.call("updates.rollout_health", {}, function (ok, r) { if (ok) root.rollout = r })
        falcon.call("resource.violations", {}, function (ok, r) { if (ok) root.violations = r.violations })
        falcon.call("hierarchy.sessions_today", { hours: 24 }, function (ok, r) { if (ok) root.sessions = r.sessions })
        falcon.call("task.list", {}, function (ok, r) { if (ok) root.tasks = r.tasks })
        falcon.call("flow.list", {}, function (ok, r) { if (ok) root.flows = r.flows })
    }
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onScopeChanged() { if (falcon.isConnected) root.refresh() }
        function onPushReceived(type, p) {
            if (type.indexOf("session.") === 0 || type.indexOf("update.") === 0 || type.indexOf("resource.") === 0
                || type.indexOf("task.") === 0 || type.indexOf("flow.") === 0) root.refresh()
        }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    readonly property var lanes: Day.lanesFor(sessions, workers)
    readonly property int quietPcs: lanes.filter(function (l) { return l.blocks.length === 0 }).length

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
                Txt { text: root.dept ? root.dept.name : ""; color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                Row {
                    spacing: 12
                    Txt { objectName: "homeTitle"; text: root.dept ? root.dept.name : "Your department"; color: "#ffffff"
                          font.pixelSize: Theme.fTitle; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                    Txt { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody
                          color: root.needs.length > 0 ? Theme.warn : Qt.rgba(1, 1, 1, 0.55)
                          text: root.workers.length + (root.workers.length === 1 ? " machine" : " machines")
                                + (root.needs.length > 0 ? " · " + root.needs.length + " need you" : "") }
                }
            }
            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: root.clock
                  color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody }
        }

        // --- the machines: the room -------------------------------------------------------------
        GridCell {
            objectName: "homeMachines"
            Layout.fillWidth: true
            Layout.preferredHeight: 226
            title: "The machines"
            narration: ({ brief: root.needCount === 0 ? "all quiet" : root.needCount + (root.needCount === 1 ? " needs looking at" : " need looking at"),
                          tone: root.needCount > 0 ? "warn" : "", state: root.machines.length === 0 ? "empty" : "ok",
                          note: "No machines yet", sentence: "Machines appear here once they are registered." })
            Column {
                width: parent.width
                spacing: 12
                PagedRow {
                    objectName: "homeFleet"
                    width: parent.width
                    height: 150
                    itemWidth: 150
                    spacing: 16
                    model: root.machines
                    attention: function (m) { return Fleet.needsSomeone(m) ? m.host : "" }
                    delegate: MachineMark {
                        property var modelData: ({})
                        size: 84
                        label: modelData.label || ""
                        status: modelData.status || "ok"
                        name: modelData.name || ""
                        line: modelData.line || ""
                        lineTone: modelData.lineTone || ""
                    }
                }
                Txt { width: parent.width; horizontalAlignment: Text.AlignHCenter; color: Theme.faint; font.pixelSize: Theme.fMeta
                      text: "Quiet means fine. A machine in colour says why beneath it." }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            GridCell {
                objectName: "homeNeeds"
                Layout.fillWidth: true
                Layout.preferredWidth: 520
                Layout.fillHeight: true
                topAlign: true
                title: "Needs you"
                narration: ({ brief: root.needs.length === 0 ? "nothing" : root.needs.length + (root.needs.length === 1 ? " thing" : " things"),
                              tone: root.needs.length > 0 ? "warn" : "ok", state: "ok" })
                PagedColumn {
                    width: parent.width
                    height: Math.max(120, root.height - 400)
                    itemHeight: 58
                    model: root.needs
                    delegate: InfoCard {
                        iconName: modelData ? modelData.icon : ""
                        iconTone: modelData ? modelData.tone : "accent"
                        title: modelData ? modelData.title : ""
                        line: modelData ? modelData.line : ""
                        stateWord: modelData ? modelData.word : ""
                        stateTone: modelData ? modelData.tone : ""
                        onClicked: if (modelData && modelData.key) shell.show(modelData.key)
                    }
                }
                Txt { visible: root.needs.length === 0; text: "Nothing needs you right now."; color: Theme.faint; font.pixelSize: Theme.fBody }
            }

            GridCell {
                objectName: "homeToday"
                Layout.fillWidth: true
                Layout.preferredWidth: 420
                Layout.fillHeight: true
                topAlign: true
                title: "Today"
                narration: ({ brief: "", state: root.lanes.length === 0 ? "empty" : "ok", note: "Nothing recorded yet" })
                Column {
                    width: parent.width
                    spacing: 10
                    DayTimeline {
                        width: parent.width
                        height: Math.min(Math.max(100, root.height - 460), lanes.length * 24 + 34)
                        labelWidth: 64
                        laneGap: 6
                        laneHeight: Math.max(9, Math.min(18, (height - 30) / Math.max(1, lanes.length) - laneGap))
                        lanes: root.lanes
                    }
                    Legend {
                        items: [{ label: "At the PC", color: Theme.line2, round: false },
                                { label: "Entered", color: Theme.warn, round: false }]
                        note: root.quietPcs === 0 ? "" : root.quietPcs + " never signed in"
                    }
                }
            }

            GridCell {
                objectName: "homeGoverning"
                Layout.fillWidth: true
                Layout.preferredWidth: 380
                Layout.fillHeight: true
                topAlign: true
                title: "Governing with you"
                narration: ({ brief: root.others.length === 0 ? "just you" : root.others.length + (root.others.length === 1 ? " other Admin" : " other Admins"), state: "ok" })
                Column {
                    width: parent.width
                    spacing: 9
                    Repeater {
                        model: root.others
                        delegate: InfoCard {
                            required property var modelData
                            width: parent.width
                            initials: Theme.initials(modelData.name || "")
                            title: modelData.name || "Admin"
                            line: !modelData.session ? "not signed in"
                                  : modelData.session.occupied_via === "assisted_access" ? "helping another department" : "at their workstation"
                            lineTone: modelData.session && modelData.session.occupied_via === "assisted_access" ? "accent" : ""
                        }
                    }
                    Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta
                          text: root.others.length === 0 ? "You govern all " + root.workers.length + " machines."
                                : "You and " + (root.others.length === 1 ? root.others[0].name : root.others.length + " others")
                                  + " govern all " + root.workers.length + " machines together." }
                }
            }
        }
    }
}
