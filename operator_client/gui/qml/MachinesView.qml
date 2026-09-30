import QtQuick
import "."

// EVERY CLIENT PC, and what is true of it right now. A table, filtered by department and by state,
// with the detail in a drawer -- the shape every listing page in this console takes.
Item {
    id: root

    property var tree: []
    property var rollout: ({})
    property var violations: []
    property bool loaded: false
    property var chosen: null
    property string look: "list"          // list | grid | day
    property var day: []                  // hierarchy.sessions_today
    property int fromHour: 0
    property string find: ""
    property var picked: []

    // one place decides what a machine's state is, so every page agrees
    readonly property var machines: {
        var behind = {}
        var rows = (rollout && rollout.pcs_behind) ? rollout.pcs_behind : []
        for (var i = 0; i < rows.length; i++) behind[rows[i].pc_id] = rows[i]
        var bad = {}
        for (var v = 0; v < violations.length; v++)
            if (violations[v].found_on_pc_id) bad[violations[v].found_on_pc_id] = violations[v]

        var out = []
        for (var d = 0; d < tree.length; d++) {
            var dept = tree[d]
            for (var w = 0; w < (dept.workers || []).length; w++) {
                var pc = dept.workers[w]
                var b = behind[pc.pc_id], vi = bad[pc.pc_id], s = pc.session
                var state, line
                if (vi) { state = "danger"; line = "a file out of place" }
                else if (b && b.escalated) { state = "danger"; line = "update past the limit" }
                else if (b) { state = "warn"; line = "a version behind" }
                else if (!s) { state = "free"; line = "nobody on it" }
                else if (s.occupied_via === "native") { state = "ok"; line = "at the PC" }
                else { state = "entered"; line = (s.occupant_name || "someone") + " entered" }
                out.push({ pc_id: pc.pc_id, host: pc.hostname || pc.name, who: pc.name || "",
                           department: dept.name, version: (b ? (b.version || "behind") : (rollout.version
                                      ? rollout.version.version_string : "")),
                           state: state, line: line,
                           stateWord: state === "danger" ? "needs you" : state === "warn" ? "behind"
                                      : state === "entered" ? "entered" : state === "free" ? "free" : "fine" })
            }
        }
        out.sort(function (a, b2) { return String(a.host).localeCompare(String(b2.host)) })
        if (find !== "") {
            var q = find.toLowerCase()
            out = out.filter(function (m) {
                return (m.host + " " + m.who + " " + m.department + " " + m.line).toLowerCase()
                       .indexOf(q) >= 0
            })
        }
        return out
    }
    readonly property int needing: machines.filter(function (m) { return m.state === "warn" || m.state === "danger" }).length

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function (ok, r) { root.loaded = true; if (ok) root.tree = r.departments })
        falcon.call("updates.rollout_health", {}, function (ok, r) { if (ok) root.rollout = r })
        falcon.call("resource.violations", {}, function (ok, r) { if (ok) root.violations = r.violations || [] })
        if (look === "day") loadDay()
    }
    function loadDay() {
        falcon.call("hierarchy.sessions_today", { hours: 24 }, function (ok, r) {
            if (ok) root.day = r.sessions || []
        })
    }
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.tree = []; root.loaded = false }
    }
    // the day is fetched when it is first looked at, however the look was changed
    onLookChanged: if (look === "day" && day.length === 0) loadDay()
    Component.onCompleted: if (falcon.isConnected) refresh()

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s5
        spacing: Theme.s3

        PageHeader {
            width: parent.width
            title: "Machines"
            subtitle: root.machines.length + " client PCs"
                      + (root.needing > 0 ? " \u00b7 " + root.needing + " need someone" : "")
            Search {
                objectName: "machinesSearch"
                anchors.verticalCenter: parent.verticalCenter
                width: 200
                placeholder: "Hostname or person"
                onSearched: function (t) { root.find = t }
            }
            Segmented {
                objectName: "machinesLook"
                anchors.verticalCenter: parent.verticalCenter
                value: root.look
                options: [{ value: "list", label: "List" }, { value: "grid", label: "Grid" },
                          { value: "day", label: "Day" }]
                onPicked: function (v) { root.look = v; if (v === "day") root.loadDay() }
            }
            Segmented {
                objectName: "daySpan"
                anchors.verticalCenter: parent.verticalCenter
                visible: root.look === "day"
                value: root.fromHour
                options: [{ value: 0, label: "24 hours" }, { value: 6, label: "6 to 6" }]
                onPicked: function (v) { root.fromHour = v }
            }
            Btn { objectName: "registerMachine"; kind: "primary"; iconName: "plus"; text: "Register"
                  onClicked: reg.open() }
        }

        Rectangle {
            width: parent.width
            height: parent.height - y
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            FleetGrid {
                objectName: "machinesGrid"
                anchors.fill: parent
                anchors.margins: Theme.s4
                visible: root.look === "grid"
                machines: root.machines
                onChose: function (m) { root.chosen = m; detail.open() }
            }

            DayTimeline {
                objectName: "machinesDay"
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.s4
                visible: root.look === "day"
                sessions: root.day
                fromHour: root.fromHour
                toHour: root.fromHour === 6 ? 18 : 24
            }

            Table {
                objectName: "machinesTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                visible: root.look === "list"
                loading: !root.loaded
                pageSize: 12
                rows: root.machines
                selectable: true
                idKey: "host"
                onSelectionChanged: function (s) { root.picked = s }
                onRowAction: function (key, row) { root.act(key, row) }
                bulk: [
                    Btn {
                        objectName: "bulkRun"
                        small: true
                        kind: "primary"
                        text: "Run action"
                        onClicked: bulkRunner.open()
                    }
                ]
                emptyText: "No machines yet"
                emptyHint: "A machine appears here once it is registered."
                onRowActivated: function (row) { root.chosen = row; detail.open() }
                columns: [
                    { title: "Machine", key: "host", width: 150, mono: true, strong: true },
                    { title: "State", key: "stateWord", width: 130, tag: true,
                      filters: ["fine", "free", "entered", "behind", "needs you"],
                      tone: function (r) { return r.state === "danger" ? "danger" : r.state === "warn" ? "warn" : "" } },
                    { title: "Why", key: "line",
                      tone: function (r) { return r.state === "danger" ? "danger" : r.state === "warn" ? "warn" : "mid" } },
                    { title: "Department", key: "department", width: 150,
                      filters: root.tree.map(function (d) { return d.name }) },
                    { title: "Signed in", key: "who", width: 130 },
                    { title: "Version", key: "version", width: 100, mono: true,
                      tone: function () { return "mid" } },
                    { title: "", key: "host", width: 44, menu: function (r) {
                        return [{ key: "enter", label: "Enter this machine" },
                                { key: "run", label: "Run an action" },
                                { key: "rekey", label: "Rekey it", danger: true, divided: true }]
                      } }
                ]
            }
        }
    }

    function act(key, row) {
        chosen = row
        if (key === "enter") enter.open()
        else if (key === "rekey") rekeying.open()
        else if (key === "run") { root.picked = [row.host]; bulkRunner.open() }
    }

    readonly property var chosenTargets: root.machines.filter(function (m) {
        return root.picked.indexOf(m.host) >= 0
    }).map(function (m) { return { pc_id: m.pc_id, host: m.host } })

    BulkRun {
        id: bulkRunner
        objectName: "bulkRunModal"
        page: root
        targets: root.chosenTargets
    }

    Confirm {
        id: enter
        objectName: "enterConfirm"
        page: root
        title: "Enter this machine"
        cost: "Whoever is on it is locked out until you leave, they are told it is you, and the whole "
              + "session is on the record. There is a time limit, and it is counted from now."
        verb: "Enter"
        onAccepted: falcon.call("hierarchy.traverse", { pc_id: root.chosen.pc_id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not entered"); return }
            Msg.ok("Inside " + root.chosen.host)
        })
    }

    Confirm {
        id: rekeying
        objectName: "rekeyConfirm"
        page: root
        title: "Rekey this machine"
        cost: "Its current key stops working at once and the machine drops off until it is reinstalled "
              + "with the new one. Do this when a key has been lost, not to tidy up."
        verb: "Rekey"
        destructive: true
        onAccepted: falcon.call("hierarchy.pc_rekey", { pc_id: root.chosen.pc_id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not rekeyed"); return }
            Msg.urgent("New key for " + root.chosen.host, "shown once \u2014 " + r.client_key)
        })
    }

    RegisterMachine {
        id: reg
        objectName: "registerModal"
        page: root
        departments: root.tree
        onRegistered: root.refresh()
    }

    Drawer {
        id: detail
        objectName: "machineDrawer"
        page: root
        title: root.chosen ? root.chosen.host : ""
        subtitle: root.chosen ? root.chosen.department : ""

        Descriptions {
            width: parent.width
            items: root.chosen ? [
                { label: "Signed in", value: root.chosen.who || "nobody" },
                { label: "State", value: root.chosen.line, tag: true,
                  tone: root.chosen.state === "danger" ? "danger" : root.chosen.state === "warn" ? "warn" : "" },
                { label: "Version", value: root.chosen.version || "unknown", mono: true },
                { label: "Department", value: root.chosen.department }
            ] : []
        }
        Txt {
            width: parent.width
            wrapMode: Text.WordWrap
            tone: "mid"
            font.pixelSize: Theme.fSmall
            text: "Entering this machine blocks whoever is on it until you leave, and the trail records that it was you."
        }

        footer: [
            Component { Btn { text: "Run action" } },
            Component { Btn { kind: "primary"; text: "Enter" } }
        ]
    }
}
