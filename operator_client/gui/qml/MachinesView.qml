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
        return out
    }
    readonly property int needing: machines.filter(function (m) { return m.state === "warn" || m.state === "danger" }).length

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function (ok, r) { root.loaded = true; if (ok) root.tree = r.departments })
        falcon.call("updates.rollout_health", {}, function (ok, r) { if (ok) root.rollout = r })
        falcon.call("resource.violations", {}, function (ok, r) { if (ok) root.violations = r.violations || [] })
    }
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.tree = []; root.loaded = false }
    }
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
            Btn { objectName: "registerMachine"; kind: "primary"; iconName: "plus"; text: "Register" }
        }

        Rectangle {
            width: parent.width
            height: parent.height - y
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Table {
                objectName: "machinesTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                loading: !root.loaded
                pageSize: 12
                rows: root.machines
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
                      tone: function () { return "mid" } }
                ]
            }
        }
    }

    Drawer {
        id: detail
        objectName: "machineDrawer"
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
