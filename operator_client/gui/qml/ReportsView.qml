import QtQuick
import "."

// WHAT THE SYSTEM WROTE DOWN ABOUT ITSELF. A report is written once and never edited; who sees it is
// decided when it is read. The Super User sees all of them, always. An Admin sees the categories
// routed to their department, and marking one addressed writes a separate row -- it never touches the
// report. That is why "addressed" is the Super User's View and a second table, not a column here.
Item {
    id: root

    property var reports: []
    property var views: []
    property bool loaded: false
    property bool showingViews: false
    property var chosen: null

    readonly property bool boss: falcon.role === "super_user"
    readonly property var words: ({
        "flow_failure": "A flow stopped",
        "resource_violation": "A file turned up where it should not",
        "cross_department_assistance": "Someone was helped across departments",
        "listener_report": "Somebody was added to a conversation",
        "update_status": "A machine could not update"
    })

    readonly property var rows: reports.map(function (r) {
        return { report_id: r.id, what: root.words[r.category] || String(r.category).replace(/_/g, " "),
                 category: r.category, from: String(r.source_table).replace(/_/g, " "),
                 when: Task.when(r.generated_at),
                 stateWord: r.addressed_at ? "addressed" : "open",
                 addressed: !!r.addressed_at }
    })
    readonly property var viewRows: views.map(function (v) {
        return { report_id: v.report_id, what: root.words[v.category] || String(v.category),
                 who: v.addressed_by_name || v.department_name || "an Admin",
                 when: Task.when(v.addressed_at) }
    })
    readonly property int open: rows.filter(function (r) { return !r.addressed }).length

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("reports.list", {}, function (ok, r) {
            root.loaded = true
            if (ok) root.reports = r.reports || []
        })
        if (boss)
            falcon.call("reports.addressed_view", {}, function (ok, r) {
                if (ok) root.views = r.views || r.addressed || []
            })
    }
    function mark() {
        if (!chosen) return
        falcon.call("reports.mark", { report_id: chosen.report_id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not marked"); return }
            Msg.ok("Marked addressed")
            detail.close()
            root.refresh()
        })
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.reports = []; root.loaded = false }
        function onPushReceived(type) { if (String(type).indexOf("report.") === 0) root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s5
        spacing: Theme.s3

        PageHeader {
            width: parent.width
            title: "Reports"
            subtitle: root.boss ? Theme.many(root.rows.length, "report") + ", all of them"
                                : root.rows.length + " routed here"
                                  + (root.open > 0 ? " · " + root.open + " not addressed" : "")
            // the same reports seen two ways, so a Segmented and not a Select
            Segmented {
                objectName: "reportsPane"
                anchors.verticalCenter: parent.verticalCenter
                visible: root.boss
                value: false
                options: [{ value: false, label: "The reports" },
                          { value: true, label: "Who addressed what" }]
                onPicked: function (v) { root.showingViews = v }
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
                objectName: "reportsTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                visible: !root.showingViews
                loading: !root.loaded
                pageSize: 12
                rows: root.rows
                emptyText: root.boss ? "Nothing has been reported" : "Nothing is routed here"
                emptyHint: root.boss ? "A report is written when something happens that somebody should know."
                                     : "Reports reach a department because the Super User routed that category to it."
                onRowActivated: function (row) { root.chosen = row; detail.open() }
                // "addressed" is an Admin's pane and the Super User's View, never a field on the
                // report -- so the Super User does not get a column that would always read "open"
                columns: root.boss ? [
                    { title: "What", key: "what", strong: true },
                    { title: "Written from", key: "from", width: 220,
                      tone: function () { return "mid" } },
                    { title: "When", key: "when", width: 180, mono: true,
                      tone: function () { return "mid" } }
                ] : [
                    { title: "What", key: "what", strong: true },
                    { title: "Written from", key: "from", width: 200,
                      tone: function () { return "mid" } },
                    { title: "When", key: "when", width: 160, mono: true,
                      tone: function () { return "mid" } },
                    { title: "State", key: "stateWord", width: 130, tag: true,
                      filters: ["open", "addressed"] }
                ]
            }

            // The View. Super-User-only, and structurally never a Report: it says who addressed what,
            // which is a different question from what happened.
            Table {
                objectName: "addressedTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                visible: root.showingViews
                loading: !root.loaded
                pageSize: 12
                rows: root.viewRows
                emptyText: "Nobody has addressed anything yet"
                emptyHint: "This is yours alone. An Admin cannot see it, and it is never a report itself."
                columns: [
                    { title: "Report", key: "what", strong: true },
                    { title: "Addressed by", key: "who", width: 220 },
                    { title: "When", key: "when", width: 160, mono: true,
                      tone: function () { return "mid" } }
                ]
            }
        }
    }

    Drawer {
        id: detail
        objectName: "reportDrawer"
        page: root
        title: root.chosen ? root.chosen.what : ""
        subtitle: root.chosen ? root.chosen.when : ""

        Descriptions {
            width: parent.width
            items: root.chosen ? [
                { label: "Category", value: root.chosen.category, mono: true },
                { label: "Written from", value: root.chosen.from },
                { label: "State", value: root.chosen.stateWord, tag: true }
            ] : []
        }
        Txt {
            width: parent.width
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
            tone: "mid"
            font.pixelSize: Theme.fSmall
            text: root.boss
                  ? "You see every report, whatever the routing says. Marking addressed is an Admin's act."
                  : "Marking this addressed tells the Super User you have it. It does not change the report."
        }

        // the Drawer's footer is a Row: order places these, not anchors
        footer: [
            Btn {
                objectName: "markReport"
                kind: "primary"
                text: "Mark addressed"
                visible: !root.boss && root.chosen && !root.chosen.addressed
                onClicked: root.mark()
            }
        ]
    }
}
