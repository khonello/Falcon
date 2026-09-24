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

    // --- the bones a panel keeps when it has nothing to draw -------------------------------------
    // A panel is never blank. With no data the chart still draws its own structure, quietened, and
    // the notice is laid over it. A zero is NOT this: a zero is a result and is drawn normally.
    readonly property var skeletonRows: {
        var names = tree.length > 0 ? tree.map(function (d) { return d.name })
                                    : ["Department", "Department", "Department"]
        return names.map(function (n) { return { label: n, parts: [{ tone: "quiet", value: 1 }] } })
    }
    readonly property var skeletonCells: {
        var out = []
        for (var i = 0; i < 8; i++) out.push({ tone: "quiet", label: "" })
        return out
    }
    readonly property var skeletonLanes: {
        var out = []
        for (var i = 0; i < 4; i++) out.push({ name: "PC", blocks: [] })
        return out
    }
    readonly property var skeletonTiers: [{ label: "/restricted/", count: 0 }, { label: "/admin/", count: 0 },
                                          { label: "/workers/", count: 0 }, { label: "/common/", count: 0 }]

    // the pairs the assistance sentence is generated from, with names rather than indexes
    readonly property var assistPairs: assistLinks.map(function (l) {
        return { from_name: tree[l.from] ? tree[l.from].name : "", 
                 to_name: tree[l.to] ? tree[l.to].name : "", count: l.count }
    })
    readonly property int quietPcs: {
        var n = 0
        for (var i = 0; i < timelineLanes.length; i++)
            if (timelineLanes[i].blocks.length === 0) n++
        return n
    }
    // the same three counts, scoped to whatever department is descended into
    function tasksIn(departmentId) {
        return tasks.filter(function (t) { return deptOfAccount(t.assignee_account_id) === departmentId })
    }
    function flowsIn(departmentId) {
        return flows.filter(function (f) { return deptOfPc(f.source_pc_id) === departmentId })
    }
    function overdueIn(departmentId) {
        var now = Date.now(), n = 0, list = tasksIn(departmentId)
        for (var i = 0; i < list.length; i++) {
            var hard = list[i].final_deadline_at ? Date.parse(list[i].final_deadline_at) : NaN
            if (!isNaN(hard) && hard < now) n++
        }
        return n
    }
    readonly property int overdueTasks: {
        var now = Date.now(), n = 0
        for (var i = 0; i < tasks.length; i++) {
            var hard = tasks[i].final_deadline_at ? Date.parse(tasks[i].final_deadline_at) : NaN
            if (!isNaN(hard) && hard < now) n++
        }
        return n
    }

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
    readonly property string clock: {
        var d = new Date()
        var days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        var hh = d.getHours() < 10 ? "0" + d.getHours() : String(d.getHours())
        var mm = d.getMinutes() < 10 ? "0" + d.getMinutes() : String(d.getMinutes())
        return days[d.getDay()] + ", " + hh + ":" + mm
    }
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
    // the window is the day that actually happened, not a window around "now": at 00:30 the
    // morning's sessions are still the record, and starting the axis at midnight would bury them
    readonly property real windowStart: {
        var lo = NaN
        for (var i = 0; i < timelineLanes.length; i++)
            for (var j = 0; j < timelineLanes[i].blocks.length; j++) {
                var f = timelineLanes[i].blocks[j].from
                lo = isNaN(lo) ? f : Math.min(lo, f)
            }
        if (isNaN(lo)) return Math.max(0, Math.floor(nowHours - 4))
        return Math.max(0, Math.floor(lo))
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

    // every ordered pair of departments, so a pair that never happened says "never" out loud
    readonly property var assistRows: {
        var counts = ({})
        for (var i = 0; i < assistLinks.length; i++)
            counts[assistLinks[i].from + ">" + assistLinks[i].to] = assistLinks[i].count
        var out = []
        for (var a = 0; a < tree.length; a++)
            for (var b = 0; b < tree.length; b++) {
                if (a === b) continue
                var n = counts[a + ">" + b] || 0
                if (n === 0 && out.length >= 3) continue
                out.push({ from_name: tree[a].name, to_name: tree[b].name, count: n,
                           fromTint: Theme.series(a), toTint: Theme.series(b) })
            }
        return out.slice(0, 5)
    }

    // a line per category with the departments it also reaches; "You" is always the first chip
    readonly property var routingLines: {
        var cats = routing.categories || []
        var conf = routing.routing || []
        return cats.map(function (c) {
            var depts = []
            for (var i = 0; i < conf.length; i++)
                if (conf[i].category === c)
                    depts.push({ name: conf[i].department_name,
                                 tint: Theme.series(root.deptIndex(conf[i].routed_department_id)) })
            var words = String(c).replace(/_/g, " ")
            return { label: words.charAt(0).toUpperCase() + words.slice(1), departments: depts }
        })
    }

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
    // ==============================================================================================
    // The page is a perfect grid: four equal cells, so nothing claims to matter more than anything
    // else. Each cell's title sits ABOVE it on the frame, with its state beside it; the cell is a
    // clean surface holding nothing but the drawing. Board K01.
    //
    // There are no tabs and no description of the organisation. A Super User knows how many
    // departments they have; the page says what they must see.
    readonly property var authoritySays: falcon.narrate("hierarchy", { tree: root.tree })
    readonly property var rolloutSays: falcon.narrate("rollout", {
        version: root.version, pcs_behind: root.behind, pc_count: root.pcCount })
    readonly property var daySays: falcon.narrate("the_day", {
        sessions: root.sessions, pc_count: root.pcCount, quiet_pcs: root.quietPcs })
    readonly property var placeSays: falcon.narrate("out_of_place", {
        violations: root.violations, deviations: root.deviations })

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.s6
        anchors.rightMargin: Theme.s6
        anchors.topMargin: Theme.s5
        anchors.bottomMargin: Theme.s5
        spacing: 20

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 34

            Txt {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "Must see"
                color: "#ffffff"
                font.pixelSize: Theme.fTitle
                font.weight: Font.Bold
            }
            Txt {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: root.clock
                color: Qt.rgba(1, 1, 1, 0.45)
                font.pixelSize: Theme.fBody
            }
        }

        GridLayout {
            id: grid
            objectName: "mustSeeGrid"
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 2
            rowSpacing: 20
            columnSpacing: 20

            // --- who governs what, and where nobody does
            GridCell {
                objectName: "cellAuthority"
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Authority"
                narration: root.authoritySays

                OrgMap {
                    width: parent.width
                    height: Math.max(150, grid.height / 2 - 120)
                    departments: root.tree
                    focusId: 0
                    onPicked: function (id) { shell.show("hierarchy") }
                }
            }

            // --- the lever only a Super User holds
            GridCell {
                objectName: "cellRollout"
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: root.version ? ("Rollout " + root.version.version_string) : "Rollout"
                narration: root.rolloutSays

                StackedBars {
                    width: parent.width
                    barHeight: 20
                    rowGap: 34
                    rows: root.rolloutRows.length > 0 ? root.rolloutRows : root.skeletonRows
                }
                Txt {
                    text: "the fleet, one square each"
                    color: Theme.faint
                    font.pixelSize: Theme.fMeta
                }
                Waffle {
                    width: parent.width
                    cellSize: 24
                    gap: 7
                    cells: root.fleetCells.length > 0 ? root.fleetCells : root.skeletonCells
                }
                Legend {
                    items: [{ label: "Confirmed", color: Theme.ok, round: true },
                            { label: "Behind", color: Theme.warn, round: true },
                            { label: "Failing", color: Theme.danger, round: true }]
                }
            }

            // --- who held each machine, and who never signed in
            GridCell {
                objectName: "cellToday"
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Today"
                narration: root.daySays

                DayTimeline {
                    width: parent.width
                    laneGap: 6
                    // the lanes share out what the cell has, and always leave the legend its room
                    laneHeight: Math.max(11, Math.min(26, (grid.height / 2 - 132)
                                                          / Math.max(1, lanes.length) - laneGap))
                    lanes: root.timelineLanes.length > 0 ? root.timelineLanes : root.skeletonLanes
                    fromHour: root.windowStart
                    toHour: root.windowEnd
                }
                Legend {
                    items: [{ label: "At the PC", color: Theme.line2, round: false },
                            { label: "An Admin entered", color: Theme.warn, round: false },
                            { label: "You entered", color: Theme.danger, round: false }]
                    note: root.quietPcs === 0 ? ""
                          : root.quietPcs + (root.quietPcs === 1 ? " PC was never signed in"
                                                                 : " PCs were never signed in")
                }
            }

            // --- files against their tier, and what deviated from what the system expects
            GridCell {
                objectName: "cellOutOfPlace"
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Out of place"
                narration: root.placeSays

                TierBars {
                    width: parent.width
                    rows: root.tierRows
                }
                Rectangle { width: parent.width; height: 1; color: Theme.line }
                Column {
                    width: parent.width
                    spacing: 0

                    Repeater {
                        model: root.deviations.slice(0, 2)
                        delegate: Item {
                            required property var modelData
                            width: parent.width
                            height: 30

                            Txt {
                                id: at
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                width: 44
                                text: String(modelData.detected_at).substring(11, 16)
                                color: Theme.faint
                                monospace: true
                                font.pixelSize: Theme.fMeta
                            }
                            Txt {
                                anchors.left: at.right
                                anchors.leftMargin: 8
                                anchors.right: mark.left
                                anchors.rightMargin: 8
                                anchors.verticalCenter: parent.verticalCenter
                                text: {
                                    var w = String(modelData.expectation).replace(/_/g, " ")
                                    return w.charAt(0).toUpperCase() + w.slice(1)
                                }
                                font.pixelSize: Theme.fBody
                            }
                            Chip {
                                id: mark
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.resolved_at ? "Addressed" : "Logged"
                                tone: modelData.resolved_at ? "ok" : "neutral"
                            }
                        }
                    }
                }
                Txt {
                    width: parent.width
                    text: root.violations.length === 0 ? "" :
                          (root.violations[0].filename + ", " + root.violations[0].resource_tag
                           + ", found on " + root.violations[0].hostname + ".")
                    visible: text !== ""
                    color: Theme.faint
                    font.pixelSize: Theme.fMeta
                    wrapMode: Text.WordWrap
                    elide: Text.ElideRight
                    maximumLineCount: 2
                }
            }
        }
    }
}
