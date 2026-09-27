import QtQuick
import QtQuick.Layouts
import "."

// ROLLOUT, the Super User's area (boards RO05, and RO06 for one department maximised).
//
// A page about many departments shows DEPARTMENTS (PATTERNS.md 3a): one line each with one mark holding the count behind.
// Double click maximises a department: its whole fleet at full size in a grid that pages down, its words beside it.
// "Holding it up" groups by department with one act each -- the same failure on several machines is usually one cause.
//
// Real data only: updates.rollout_health (departments + pcs_behind) and hierarchy.tree (names, hostnames, Admins).
// The Engine does not report whether a machine is online, so the words say what IS known: retrying, or past the limit.
Item {
    id: root

    property var tree: []
    property var health: ({})
    property int openDept: 0                // 0 = every department; else the maximised one
    property string filter: "all"           // all | behind
    property string clock: ""

    readonly property var version: health.version || null
    readonly property var depts: health.departments || []
    readonly property var behindAll: health.pcs_behind || []
    readonly property int pcTotal: depts.reduce(function (n, d) { return n + (d.pcs || 0) }, 0)
    readonly property int behindTotal: behindAll.length
    readonly property var deptsBehind: depts.filter(function (d) { return root.behindIn(d.department_id).length > 0 })
    readonly property var listed: filter === "behind" ? deptsBehind : depts
    readonly property var opened: {
        for (var i = 0; i < depts.length; i++) if (depts[i].department_id === openDept) return depts[i]
        return null
    }

    function behindIn(id) { return behindAll.filter(function (b) { return b.department_id === id }) }
    function treeDept(id) {
        for (var i = 0; i < tree.length; i++) if (tree[i].department_id === id) return tree[i]
        return null
    }
    function stamp(id) {
        for (var i = 0; i < tree.length; i++) if (tree[i].department_id === id) return Theme.series(i)
        return Theme.accent
    }
    function adminsOf(id) { var d = treeDept(id); return d ? d.admins : [] }
    function prefixed(host) { return host || "" }

    function refresh() {
        if (!falcon.isConnected || falcon.role !== "super_user") return
        falcon.call("updates.rollout_health", {}, function (ok, r) { if (ok) root.health = r })
        falcon.call("hierarchy.tree", {}, function (ok, r) { if (ok) root.tree = r.departments })
    }
    function ask(id) {
        falcon.call("updates.prompt_admin", { department_id: id }, function (ok, r) {
            shell.notify(ok ? "Asked the department's Admins to look" : r.message, !ok)
        })
    }
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onPushReceived(type, p) { if (type.indexOf("update.") === 0) root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Keys.onEscapePressed: root.openDept = 0
    focus: true

    // the machines of the maximised department, in hostname order, each with its words
    readonly property var openMachines: {
        var d = treeDept(openDept)
        if (!d) return []
        var out = d.workers.map(function (w) {
            var b = root.behindAll.filter(function (x) { return x.pc_id === w.pc_id })[0]
            var host = w.hostname || ""
            return { label: host.split("-").pop(), name: host, sortKey: host,
                     status: !b ? "ok" : b.escalated ? "danger" : "warn",
                     line: !b ? "on " + (root.version ? root.version.version_string : "current")
                              : (b.escalated ? "past the limit" : "failed " + (b.failures || 0) + "×"),
                     lineTone: !b ? "" : b.escalated ? "danger" : "warn" }
        })
        out.sort(function (a, b) { return a.sortKey.localeCompare(b.sortKey) })
        return out
    }

    component StallCard: Rectangle {
        id: stall
        property var dept: ({})
        property var modelData: null
        property int index: -1
        readonly property var rows: root.behindIn(dept ? dept.department_id : 0)
        readonly property int past: rows.filter(function (b) { return b.escalated }).length
        readonly property int worst: rows.reduce(function (m, b) { return Math.max(m, b.failures || 0) }, 0)
        readonly property var admins: root.adminsOf(dept ? dept.department_id : 0)
        height: 64
        radius: 14
        color: Theme.pane
        Row {
            anchors.left: parent.left
            anchors.leftMargin: 14
            anchors.right: parent.right
            anchors.rightMargin: 150          // the act's room: words never run under the button
            anchors.verticalCenter: parent.verticalCenter
            spacing: 14
            clip: true
            MachineMark { size: 36; label: String(stall.rows.length); status: stall.past > 0 ? "danger" : "warn"
                          anchors.verticalCenter: parent.verticalCenter }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Txt { text: (stall.dept ? stall.dept.department_name : "") + ": "
                            + (stall.rows.length === 1 ? stall.rows[0].hostname : stall.rows.length + " machines")
                      color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                Txt { text: (stall.past > 0 ? stall.past + " past the limit" : "retrying")
                            + (stall.worst > 0 ? " · worst " + stall.worst + "×" : "")
                            + (stall.admins.length === 0 ? " · nobody governs it" : "")
                      color: Theme.faint; font.pixelSize: Theme.fMeta }
            }
        }
        TBtn {
            visible: stall.admins.length > 0
            anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
            text: "Ask " + (stall.admins.length > 0 ? (stall.admins[0].name || "the Admin") : "")
            tone: "warn"; small: true
            onClicked: root.ask(stall.dept.department_id)
        }
        GBtn {
            visible: stall.admins.length === 0
            anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
            text: "Assign an Admin"; small: true
            onClicked: shell.enterDepartment(stall.dept.department_id)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 22
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 16

        // --- the crumb and the title ----------------------------------------------------------
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Column {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4
                Row {
                    spacing: 6
                    Txt { text: "Rollout"; color: root.openDept === 0 ? "#ffffff" : Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody
                          font.weight: root.openDept === 0 ? Font.DemiBold : Font.Normal
                          MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: root.openDept = 0 } }
                    Icon { visible: root.opened !== null; name: "chev"; color: Qt.rgba(1, 1, 1, 0.45); size: 12; anchors.verticalCenter: parent.verticalCenter }
                    Txt { objectName: "rolloutCrumbDept"; visible: root.opened !== null; text: root.opened ? root.opened.department_name : ""
                          color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                }
                Row {
                    spacing: 12
                    Txt { text: root.opened ? root.opened.department_name : "Rollout"; color: "#ffffff"; font.pixelSize: Theme.fTitle
                          font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                    Rectangle { visible: root.opened !== null; width: 9; height: 9; radius: 3; color: root.stamp(root.openDept)
                                anchors.verticalCenter: parent.verticalCenter }
                    Txt {
                        objectName: "rolloutPhrase"
                        anchors.verticalCenter: parent.verticalCenter
                        font.pixelSize: Theme.fBody
                        color: root.behindTotal > 0 ? Theme.warn : Qt.rgba(1, 1, 1, 0.55)
                        text: !root.version ? "no version approved yet"
                              : root.opened ? (root.opened.pcs + " machines · " + root.behindIn(root.openDept).length + " behind")
                              : root.version.version_string + " on " + (root.pcTotal - root.behindTotal) + " of " + root.pcTotal
                                + " machines · " + root.depts.length + (root.depts.length === 1 ? " department" : " departments")
                    }
                }
            }
            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                  text: root.opened ? "Esc to go back" : root.clock; color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody }
        }

        // --- every department -----------------------------------------------------------------
        RowLayout {
            visible: root.openDept === 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            GridCell {
                objectName: "rolloutDepartments"
                Layout.fillWidth: true
                Layout.preferredWidth: 2
                Layout.fillHeight: true
                topAlign: true
                title: "By department"
                narration: ({ brief: root.deptsBehind.length === 0 ? "all current"
                                     : root.deptsBehind.length + (root.deptsBehind.length === 1 ? " with machines behind" : " with machines behind"),
                              tone: root.deptsBehind.length > 0 ? "warn" : "", state: root.depts.length === 0 ? "empty" : "ok",
                              note: "No machines yet", sentence: "Machines appear here once they are registered." })
                Column {
                    width: parent.width
                    spacing: 10
                    SegmentedControl {
                        id: filterTabs
                        segments: [{ text: "Every department" }, { text: "Behind only" }]
                        onCurrentIndexChanged: root.filter = currentIndex === 0 ? "all" : "behind"
                    }
                    PagedColumn {
                        objectName: "rolloutList"
                        width: parent.width
                        height: Math.max(120, root.height - 210)
                        itemHeight: 50
                        spacing: 8
                        model: root.listed
                        attention: function (d) {
                            var n = root.behindIn(d.department_id).length
                            return n > 0 ? d.department_name + ": " + n + " behind" : ""
                        }
                        delegate: DeptRolloutCard {
                            dept: modelData || ({})
                            behind: modelData ? root.behindIn(modelData.department_id) : []
                            stamp: modelData ? root.stamp(modelData.department_id) : Theme.accent
                            onOpened: root.openDept = modelData.department_id
                        }
                    }
                    Txt { text: "Double-click a department to open its machines."; color: Theme.faint; font.pixelSize: Theme.fMeta }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                spacing: 20

                GridCell {
                    objectName: "rolloutGate"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 230
                    topAlign: true
                    title: "The gate"
                    narration: ({ brief: root.behindTotal > 0 ? "the next version waits" : "open", tone: root.behindTotal > 0 ? "warn" : "ok", state: "ok" })
                    Column {
                        width: parent.width
                        spacing: 10
                        Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: Theme.fSection; font.weight: Font.DemiBold
                              text: root.behindTotal > 0 ? "A new version can't be approved yet." : "A new version can be approved." }
                        Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.dim; font.pixelSize: Theme.fBody
                              text: root.behindTotal > 0
                                    ? root.behindTotal + (root.behindTotal === 1 ? " machine is" : " machines are") + " not on "
                                      + (root.version ? root.version.version_string : "the current version") + " yet. Every machine must be first."
                                    : "Every machine is on " + (root.version ? root.version.version_string : "the current version") + "." }
                        TBtn { visible: !approveRow.visible; text: "Approve a new version"; iconName: "check"
                               enabled: root.behindTotal === 0; onClicked: approveRow.visible = true }
                        Row {
                            id: approveRow
                            visible: false
                            spacing: 8
                            Field { id: nextVersion; width: 150; placeholderText: "next version" }
                            TBtn { text: "Approve"; enabled: nextVersion.text.length > 0
                                   onClicked: falcon.call("updates.approve", { version: nextVersion.text }, function (ok, r) {
                                       shell.notify(ok ? "Approved " + r.version + "; Admins roll it out" : r.message, !ok)
                                       if (ok) { approveRow.visible = false; root.refresh() } }) }
                        }
                        Txt { visible: root.behindTotal > 0; text: "This unlocks by itself when they catch up."; color: Theme.faint; font.pixelSize: Theme.fMeta }
                    }
                }
                GridCell {
                    objectName: "rolloutHolding"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    topAlign: true
                    title: "Holding it up"
                    narration: ({ brief: root.deptsBehind.length === 0 ? "nothing" : root.deptsBehind.length + (root.deptsBehind.length === 1 ? " department" : " departments"),
                                  tone: root.deptsBehind.length > 0 ? "warn" : "ok", state: "ok" })
                    Column {
                        width: parent.width
                        spacing: 8
                        PagedColumn {
                            width: parent.width
                            height: Math.max(80, root.height - 460)
                            itemHeight: 64
                            spacing: 8
                            model: root.deptsBehind
                            delegate: StallCard { width: parent ? parent.width : 300; dept: modelData || ({}) }
                        }
                        Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta
                              text: root.deptsBehind.length === 0 ? "Nothing is holding the rollout up."
                                    : "Failed updates retry on their own when a machine is idle." }
                    }
                }
            }
        }

        // --- one department, maximised --------------------------------------------------------
        RowLayout {
            visible: root.openDept !== 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            GridCell {
                objectName: "rolloutMachines"
                Layout.fillWidth: true
                Layout.preferredWidth: 2
                Layout.fillHeight: true
                topAlign: true
                title: "Its machines"
                narration: ({ brief: root.behindIn(root.openDept).length + " behind", tone: root.behindIn(root.openDept).length > 0 ? "warn" : "ok", state: "ok" })
                MachineGrid {
                    objectName: "rolloutGrid"
                    width: parent.width
                    height: Math.max(200, root.height - 150)
                    machines: root.openMachines
                }
            }
            GridCell {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "What it says"
                narration: ({ brief: root.behindIn(root.openDept).length > 0 ? "one ask" : "nothing to chase", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 12
                    Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: Theme.fSection; font.weight: Font.DemiBold
                          text: root.opened ? (root.opened.pcs - root.behindIn(root.openDept).length) + " of " + root.opened.department_name + "'s "
                                              + root.opened.pcs + " machines are on " + (root.version ? root.version.version_string : "the current version") + "." : "" }
                    StallCard { visible: root.behindIn(root.openDept).length > 0; width: parent.width; dept: root.opened || ({}) }
                    KeyRow { label: "Governed by"; value: root.adminsOf(root.openDept).map(function (a) { return a.name }).join(", ") || "nobody" }
                    KeyRow { label: "Retries"; value: "run by themselves when idle" }
                }
            }
        }
    }
}
