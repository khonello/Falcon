import QtQuick
import "."

// WHAT NEEDS SOMEBODY. Not a dashboard: no tiles counting things nobody has to act on, no chart of a
// number that is fine. Every line here is a thing a person has to do, in the words of what it is, and
// it opens the page where it gets done. When there is nothing, the page says so and stays quiet.
Item {
    id: root
    signal go(string view)
    property var reach: []                 // the areas this level actually has (main.qml decides)

    property var tree: []
    property var behind: []
    property var violations: []
    property var tasks: []
    property var flows: []
    property var pings: []
    property var reports: []
    property bool loaded: false

    readonly property bool boss: falcon.role === "super_user"

    readonly property int machines: {
        var n = 0
        for (var d = 0; d < tree.length; d++) n += (tree[d].workers || []).length
        return n
    }
    readonly property int people: {
        var n = 0
        for (var d = 0; d < tree.length; d++)
            n += (tree[d].admins || []).length + (tree[d].workers || []).length
        return n
    }
    readonly property int ungoverned: tree.filter(function (d) {
        return (d.admins || []).length === 0
    }).length
    readonly property int lateTasks: tasks.filter(function (t) {
        return Task.state(t).tone === "danger"
    }).length
    readonly property int stoppedFlows: flows.filter(function (f) {
        return Sync.state(f).tone === "danger"
    }).length
    readonly property int looseFiles: violations.filter(function (v) { return !v.resolved_at }).length
    readonly property int openReports: reports.filter(function (r) { return !r.addressed_at }).length
    readonly property int stuck: behind.filter(function (b) { return b.escalated }).length

    // one list, ordered by how much it matters, and every line is an act
    readonly property var needs: {
        var out = []
        if (pings.length > 0)
            out.push({ what: Theme.many(pings.length, "person", "people") + " asked for you",
                       why: "Nothing opens until you answer.", where: "assistance", tone: "danger" })
        if (looseFiles > 0)
            out.push({ what: Theme.many(looseFiles, "file") + " on the wrong shelf",
                       why: "Somebody has a file they should not have.", where: "resources",
                       tone: "danger" })
        if (stoppedFlows > 0)
            out.push({ what: Theme.many(stoppedFlows, "flow") + " stopped",
                       why: "Nothing is copying until it is fixed.", where: "flows", tone: "danger" })
        if (lateTasks > 0)
            out.push({ what: Theme.many(lateTasks, "task") + " past the deadline",
                       why: "Only you can close a task you assigned.", where: "tasks", tone: "danger" })
        if (stuck > 0)
            out.push({ what: Theme.many(stuck, "machine") + " cannot update",
                       why: "They have tried and failed too often.", where: "rollout", tone: "danger" })
        if (ungoverned > 0)
            out.push({ what: Theme.many(ungoverned, "department") + " with nobody governing",
                       why: "Their machines answer to no Admin.", where: "departments", tone: "warn" })
        if (behind.length - stuck > 0)
            out.push({ what: Theme.many(behind.length - stuck, "machine") + " not on the version yet",
                       why: "The next version waits on them.", where: "rollout", tone: "warn" })
        if (openReports > 0 && !boss)
            out.push({ what: Theme.many(openReports, "report") + " not addressed",
                       why: "The Super User is waiting to hear you have them.", where: "reports",
                       tone: "warn" })
        return out
    }

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function (ok, r) {
            root.loaded = true
            if (ok) root.tree = r.departments || []
        })
        falcon.call("updates.rollout_health", {}, function (ok, r) { if (ok) root.behind = r.pcs_behind || [] })
        falcon.call("resource.violations", {}, function (ok, r) { if (ok) root.violations = r.violations || [] })
        falcon.call("task.list", {}, function (ok, r) { if (ok) root.tasks = r.tasks || [] })
        falcon.call("flow.list", {}, function (ok, r) { if (ok) root.flows = r.flows || [] })
        falcon.call("assistance.ping_status", {}, function (ok, r) { if (ok) root.pings = r.pings || [] })
        falcon.call("reports.list", {}, function (ok, r) { if (ok) root.reports = r.reports || [] })
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.loaded = false }
        function onPushReceived(type) { root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s5
        spacing: Theme.s4

        PageHeader {
            width: parent.width
            title: root.needs.length === 0 ? "Nothing needs you" : "What needs you"
            subtitle: root.needs.length === 0
                      ? "Everything the system watches is where it should be."
                      : Theme.many(root.needs.length, "thing") + " to look at"
        }

        Rectangle {
            width: parent.width
            height: list.implicitHeight + 2
            visible: root.needs.length > 0
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Column {
                id: list
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.topMargin: 1
                spacing: 0

                Repeater {
                    model: root.needs
                    delegate: Rectangle {
                        required property var modelData
                        // a Super User sees what is wrong in a department without having the page
                        // that fixes it -- that is oversight. It is still worth knowing, so the line
                        // stays; it just stops pretending to be a link.
                        readonly property bool canGo: root.reach.indexOf(modelData.where) >= 0
                        width: parent.width
                        height: 60
                        color: canGo && hover.hovered ? Theme.hover : "transparent"

                        Dot {
                            id: mark
                            tone: modelData.tone
                            anchors.left: parent.left
                            anchors.leftMargin: Theme.s4
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Column {
                            anchors.left: mark.right
                            anchors.leftMargin: Theme.s3
                            anchors.right: chev.left
                            anchors.rightMargin: Theme.s3
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 1
                            Txt {
                                width: parent.width
                                text: modelData.what
                                strong: true
                                tone: modelData.tone
                            }
                            Txt {
                                width: parent.width
                                text: modelData.why
                                tone: "mid"
                                font.pixelSize: Theme.fSmall
                            }
                        }
                        Icon {
                            id: chev
                            name: "chevr"
                            size: 15
                            visible: parent.canGo
                            color: Theme.quiet
                            anchors.right: parent.right
                            anchors.rightMargin: Theme.s4
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 1
                            color: Theme.split
                        }
                        HoverHandler { id: hover; enabled: parent.canGo; cursorShape: Qt.PointingHandCursor }
                        TapHandler { enabled: parent.canGo; onTapped: root.go(modelData.where) }
                    }
                }
            }
        }

        Empty {
            width: parent.width
            visible: root.loaded && root.needs.length === 0
            text: "All quiet"
            hint: "Nothing here is good news dressed up: there is simply nothing that needs a person."
        }

        // the quiet facts, which are not an act and so are not a tile
        Txt {
            width: parent.width
            visible: root.loaded
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
            tone: "quiet"
            font.pixelSize: Theme.fSmall
            text: Theme.many(root.people, "person", "people") + " on "
                  + Theme.many(root.machines, "machine") + ", across "
                  + Theme.many(root.tree.length, "department") + "."
        }
    }
}
