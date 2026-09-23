import QtQuick
import QtQuick.Layouts
import "."

// Super User: the system, seen.
//
// The Super User can see every department, Admin, PC, session, rollout, report and violation. That
// is too much to list, so it is drawn -- three pages of one dashboard: the system at a glance, the
// hierarchy itself, and the record of the day. Picking a department on the hierarchy page descends
// into it: the same drawing, everything else quietened.
//
// Nothing here is invented. Every figure comes from a handler that already exists, and a panel with
// no data behind it says so rather than drawing an empty chart.
Item {
    id: root

    property int page: 0                   // 0 at a glance, 1 the hierarchy, 2 the record
    property int focusDept: 0              // 0 = everything

    property var tree: []
    property var rollout: ({})             // updates.rollout_health
    property var sessions: []              // hierarchy.sessions_today
    property var violations: []
    property var deviations: []
    property var routing: ({})             // reports.routing_get
    property var confirmations: []         // successful update attempts, by day, accumulated
    property var tasks: []
    property var flows: []

    // --- what the tree tells us ----------------------------------------------------------------
    readonly property int pcCount: tree.reduce(function (n, d) { return n + d.workers.length }, 0)
    readonly property int adminCount: tree.reduce(function (n, d) { return n + d.admins.length }, 0)
    readonly property var focused: findDept(focusDept)

    function findDept(id) {
        for (var i = 0; i < tree.length; i++) if (tree[i].department_id === id) return tree[i]
        return null
    }
    function deptIndex(id) {
        for (var i = 0; i < tree.length; i++) if (tree[i].department_id === id) return i
        return 0
    }
    function deptOfAccount(accountId) {
        for (var i = 0; i < tree.length; i++) {
            var all = tree[i].admins.concat(tree[i].workers)
            for (var j = 0; j < all.length; j++)
                if (all[j].account_id === accountId) return tree[i].department_id
        }
        return 0
    }
    function deptOfPc(pcId) {
        for (var i = 0; i < tree.length; i++) {
            var all = tree[i].admins.concat(tree[i].workers)
            for (var j = 0; j < all.length; j++) if (all[j].pc_id === pcId) return tree[i].department_id
        }
        return 0
    }
    function initials(name) {
        if (!name) return "?"
        var parts = String(name).replace(".", " ").split(" ").filter(function (p) { return p.length > 0 })
        return (parts.length > 1 ? parts[0][0] + parts[1][0] : String(name).substring(0, 2)).toUpperCase()
    }

    // --- rollout --------------------------------------------------------------------------------
    readonly property var version: rollout.version || null
    readonly property var behind: rollout.pcs_behind || []
    readonly property int behindCount: behind.length
    readonly property int confirmedCount: Math.max(0, pcCount - behindCount)

    function rolloutRow(departmentId) {
        var list = rollout.departments || []
        for (var i = 0; i < list.length; i++) if (list[i].department_id === departmentId) return list[i]
        return null
    }
    function rolloutParts(departmentId) {
        var h = rolloutRow(departmentId)
        var failing = 0, pending = 0
        for (var i = 0; i < behind.length; i++)
            if (behind[i].department_id === departmentId) {
                if (behind[i].escalated) failing++
                else pending++
            }
        var total = h ? h.pcs : 0
        return [{ tone: "ok", value: Math.max(0, total - pending - failing) },
                { tone: "warn", value: pending }, { tone: "danger", value: failing }]
    }
    function behindFor(pcId) {
        for (var i = 0; i < behind.length; i++) if (behind[i].pc_id === pcId) return behind[i]
        return null
    }
    readonly property var fleetCells: {
        var out = []
        for (var i = 0; i < tree.length; i++)
            for (var j = 0; j < tree[i].workers.length; j++) {
                var w = tree[i].workers[j]
                var b = behindFor(w.pc_id)
                out.push({ tone: !b ? "ok" : b.escalated ? "danger" : "warn",
                           label: (w.hostname || w.name)
                                  + (!b ? " — confirmed" : b.escalated ? " — failing" : " — behind") })
            }
        return out
    }
    readonly property var rolloutRows: tree.map(function (d) {
        return { label: d.name, parts: root.rolloutParts(d.department_id) }
    })

    // --- work, by department ----------------------------------------------------------------------
    function taskParts(departmentId) {
        var now = Date.now(), on = 0, soon = 0, over = 0
        for (var i = 0; i < tasks.length; i++) {
            var t = tasks[i]
            if (deptOfAccount(t.assignee_account_id) !== departmentId) continue
            var hard = t.final_deadline_at ? Date.parse(t.final_deadline_at) : NaN
            var soft = t.soft_deadline_at ? Date.parse(t.soft_deadline_at) : NaN
            if (!isNaN(hard) && hard < now) over++
            else if (!isNaN(soft) && soft < now) soon++
            else on++
        }
        return [{ tone: "ok", value: on }, { tone: "warn", value: soon }, { tone: "danger", value: over }]
    }
    function flowParts(departmentId) {
        var syncing = 0, paused = 0
        for (var i = 0; i < flows.length; i++) {
            var f = flows[i]
            if (deptOfPc(f.source_pc_id) !== departmentId) continue
            if (f.status === "active") syncing++
            else paused++
        }
        return [{ tone: "ok", value: syncing }, { tone: "warn", value: paused }, { tone: "danger", value: 0 }]
    }

    // --- the record --------------------------------------------------------------------------------
    readonly property real nowHours: {
        var d = new Date()
        return d.getHours() + d.getMinutes() / 60
    }
    function hoursOf(iso) {
        if (!iso) return NaN
        var d = new Date(iso)
        var today = new Date()
        var midnight = new Date(today.getFullYear(), today.getMonth(), today.getDate())
        return (d.getTime() - midnight.getTime()) / 3600000
    }
    function sessionState(s) {
        if (s.occupied_via === "native") return "native"
        if (s.occupied_via === "assisted_access") return "assisted_access"
        return s.occupant_role === "super_user" ? "super_user" : "traversal"
    }
    function blocksFor(pcId) {
        var out = []
        for (var i = 0; i < sessions.length; i++) {
            var s = sessions[i]
            if (s.pc_id !== pcId) continue
            var from = hoursOf(s.entered_at)
            var to = s.ended_at ? hoursOf(s.ended_at) : nowHours
            if (isNaN(from) || to <= from) continue
            out.push({ state: sessionState(s), from: from, to: to,
                       label: (s.occupant_name || "someone") + " · "
                              + (s.occupied_via === "native" ? "at the PC" : s.occupied_via.replace("_", " ")) })
        }
        return out
    }
    readonly property var timelineLanes: {
        var out = []
        for (var i = 0; i < tree.length; i++) {
            if (focusDept !== 0 && tree[i].department_id !== focusDept) continue
            for (var j = 0; j < tree[i].workers.length; j++) {
                var w = tree[i].workers[j]
                out.push({ name: w.name || w.hostname, blocks: blocksFor(w.pc_id) })
            }
        }
        return out
    }
    readonly property real windowStart: {
        var lo = nowHours
        for (var i = 0; i < timelineLanes.length; i++)
            for (var j = 0; j < timelineLanes[i].blocks.length; j++)
                lo = Math.min(lo, timelineLanes[i].blocks[j].from)
        return Math.max(0, Math.floor(Math.min(lo, nowHours - 2)))
    }
    readonly property real windowEnd: {
        var hi = nowHours + 0.5
        for (var i = 0; i < timelineLanes.length; i++)
            for (var j = 0; j < timelineLanes[i].blocks.length; j++)
                hi = Math.max(hi, timelineLanes[i].blocks[j].to)
        return Math.min(24, Math.ceil(hi))
    }

    readonly property int traversalsToday: {
        var n = 0
        for (var i = 0; i < sessions.length; i++) if (sessions[i].occupied_via !== "native") n++
        return n
    }
    readonly property int openTraversals: {
        var n = 0
        for (var i = 0; i < sessions.length; i++)
            if (sessions[i].occupied_via !== "native" && !sessions[i].ended_at) n++
        return n
    }

    // assistance between departments, from the day's assisted sessions: the helper's department
    // reached the department the PC belongs to. Oversight only -- none of it is gated.
    readonly property var assistLinks: {
        var seen = ({}), out = []
        for (var i = 0; i < sessions.length; i++) {
            var s = sessions[i]
            if (s.occupied_via !== "assisted_access") continue
            var from = deptIndex(deptOfAccount(s.occupant_account_id))
            var to = deptIndex(s.department_id)
            if (from === to) continue
            var key = from + ">" + to
            if (seen[key] === undefined) {
                seen[key] = out.length
                out.push({ from: from, to: to, count: 0 })
            }
            out[seen[key]].count++
        }
        return out
    }
    readonly property var assistNodes: tree.map(function (d) { return { id: d.department_id, name: d.name } })

    // --- violations, deviations, routing ------------------------------------------------------------
    readonly property var tierRows: {
        var tiers = [{ label: "/restricted/", tag: "restricted" }, { label: "/admin/", tag: "admin" },
                     { label: "/workers/", tag: "worker_dept" }, { label: "/common/", tag: "common" }]
        return tiers.map(function (t) {
            var n = 0
            for (var i = 0; i < root.violations.length; i++)
                if (root.violations[i].resource_tag === t.tag) n++
            return { label: t.label, count: n }
        })
    }
    readonly property var routingRows: {
        var cats = routing.categories || []
        var conf = routing.routing || []
        return cats.map(function (c) {
            var to = []
            for (var i = 0; i < conf.length; i++)
                if (conf[i].category === c) to.push(root.deptIndex(conf[i].routed_department_id))
            var words = String(c).replace(/_/g, " ")
            return { label: words.charAt(0).toUpperCase() + words.slice(1), to: to }
        })
    }
    readonly property var routingDests: {
        var seen = ({}), out = []
        var conf = routing.routing || []
        for (var i = 0; i < conf.length; i++) {
            var d = conf[i].routed_department_id
            if (seen[d]) continue
            seen[d] = true
            out.push({ index: root.deptIndex(d), name: conf[i].department_name })
        }
        return out
    }

    readonly property int emptyDepartments: {
        var n = 0
        for (var i = 0; i < tree.length; i++) if (tree[i].admins.length === 0) n++
        return n
    }
    readonly property int waitingOnYou: emptyDepartments + violations.length + deviations.length

    // ==============================================================================================
    function refresh() {
        // these are the Super User's surfaces; reports.routing_get is refused to anyone else, so
        // the view stays quiet rather than firing requests it knows will come back forbidden
        if (!falcon.isConnected || falcon.role !== "super_user") return
        falcon.call("hierarchy.tree", {}, function (ok, r) { if (ok) root.tree = r.departments })
        falcon.call("updates.rollout_health", {}, function (ok, r) { if (ok) root.rollout = r })
        falcon.call("hierarchy.sessions_today", { hours: 24 }, function (ok, r) { if (ok) root.sessions = r.sessions })
        falcon.call("resource.violations", {}, function (ok, r) { if (ok) root.violations = r.violations })
        falcon.call("audit.deviations", {}, function (ok, r) { if (ok) root.deviations = r.deviations })
        falcon.call("reports.routing_get", {}, function (ok, r) { if (ok) root.routing = r })
        falcon.call("task.list", {}, function (ok, r) { if (ok) root.tasks = r.tasks })
        falcon.call("flow.list", {}, function (ok, r) { if (ok) root.flows = r.flows })
        falcon.call("audit.recent", { limit: 500, prefix: "update.attempt" }, function (ok, r) {
            if (ok) root.confirmations = root.cumulative(r.entries)
        })
    }
    // successful attempts, bucketed by day and accumulated: the shape of a rollout landing
    function cumulative(entries) {
        var days = [], seen = ({})
        for (var d = 6; d >= 0; d--) {
            var t = new Date()
            t.setDate(t.getDate() - d)
            days.push({ key: t.toDateString(), n: 0 })
        }
        for (var i = 0; i < entries.length; i++) {
            var e = entries[i]
            if (!e.detail || e.detail.succeeded !== true) continue
            if (seen[e.target_id]) continue
            seen[e.target_id] = true
            var key = new Date(e.occurred_at).toDateString()
            for (var j = 0; j < days.length; j++) if (days[j].key === key) days[j].n++
        }
        var out = [], run = 0
        for (var k = 0; k < days.length; k++) {
            run += days[k].n
            out.push(run)
        }
        return out
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() {
            root.tree = []
            root.sessions = []
            root.rollout = ({})
        }
        function onPushReceived(type, p) {
            if (type.indexOf("session.") === 0 || type.indexOf("assisted_access.") === 0
                || type.indexOf("update.") === 0 || type === "hierarchy.changed")
                root.refresh()
        }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    // ==============================================================================================
    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s6
        anchors.rightMargin: Theme.s6
        anchors.topMargin: Theme.s5
        anchors.bottomMargin: Theme.s5
        spacing: 0

        // the breadcrumb: descent is one level, and you back out by picking Everything
        Row {
            spacing: 7
            Layout.preferredHeight: 20

            Txt {
                text: "Everything"
                color: root.focusDept === 0 ? Theme.ink : Theme.faint
                font.pixelSize: Theme.fBody
                font.weight: root.focusDept === 0 ? Font.DemiBold : Font.Normal

                MouseArea {
                    anchors.fill: parent
                    enabled: root.focusDept !== 0
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.focusDept = 0
                }
            }
            Icon {
                name: "chev"
                color: Theme.faint
                size: 12
                visible: root.focusDept !== 0
                anchors.verticalCenter: parent.verticalCenter
            }
            Txt {
                visible: root.focusDept !== 0
                text: root.focused ? root.focused.name : ""
                font.pixelSize: Theme.fBody
                font.weight: Font.DemiBold
            }
        }

        Item { Layout.preferredHeight: 10 }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 46

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 13

                Rectangle {
                    width: 10
                    height: 28
                    radius: 3
                    color: root.focusDept === 0 ? Theme.ink : Theme.series(root.deptIndex(root.focusDept))
                    anchors.verticalCenter: parent.verticalCenter
                }
                Txt {
                    text: root.focusDept === 0 ? "Everything" : (root.focused ? root.focused.name : "")
                    font.pixelSize: Theme.fTitle - 2
                    font.weight: Font.Bold
                    anchors.verticalCenter: parent.verticalCenter
                }
                Txt {
                    text: root.focusDept === 0
                          ? (root.tree.length + " departments  ·  " + root.adminCount + " Admins  ·  "
                             + root.pcCount + " client PCs")
                          : (root.focused
                             ? (root.focused.admins.length
                                + (root.focused.admins.length === 1 ? " Admin  ·  " : " Admins  ·  ")
                                + root.focused.workers.length + " client PCs")
                             : "")
                    color: Theme.dim
                    font.pixelSize: Theme.fBody
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            GBtn {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                visible: root.focusDept !== 0
                small: true
                text: "Open in Hierarchy"
                iconName: "hierarchy"
                onClicked: shell.show("hierarchy")
            }
        }

        Item { Layout.preferredHeight: 14 }

        Pills {
            Layout.fillWidth: true
            model: [{ label: "At a glance", count: "" },
                    { label: "The hierarchy", count: "" },
                    { label: "The record", count: "" }]
            current: root.page
            onPicked: function (i) { root.page = i }
        }

        Item { Layout.preferredHeight: 14 }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.page

            GlancePage { view: root }
            HierarchyPage { view: root }
            RecordPage { view: root }
        }
    }
}
