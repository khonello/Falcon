import QtQuick
import "."

// THE RECORD: everything that happened, and who did it. The most table-shaped page in the console,
// and the one the whole idiom is proved on -- sort, filter, page, and an honest empty state.
Item {
    id: root

    property var entries: []
    property bool loaded: false

    readonly property var rows: {
        var out = []
        for (var i = 0; i < entries.length; i++) {
            var e = entries[i]
            var t = String(e.action || e.type || "")
            var kind = t.indexOf("deviation") >= 0 ? "deviation"
                     : t.indexOf("resource.") === 0 ? "violation"
                     : t.indexOf("session.") === 0 || t.indexOf("hierarchy.") === 0 ? "session"
                     : t.indexOf("assistance") >= 0 || t.indexOf("assisted") >= 0 ? "assistance"
                     : t.indexOf("control.") === 0 || t.indexOf("action") >= 0 ? "action"
                     : t.indexOf("task.") === 0 ? "task"
                     : t.indexOf("flow.") === 0 ? "flow"
                     : t.indexOf("updates.") === 0 ? "rollout"
                     : "other"
            out.push({
                at: String(e.occurred_at || e.at || "").substring(11, 16),
                who: e.actor_name || e.who || "System",
                what: e.summary || e.what || t.replace(/[._]/g, " "),
                subject: e.target_hostname || e.subject || "",
                kind: kind
            })
        }
        return out
    }

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("audit.recent", { limit: 200 }, function (ok, r) {
            root.loaded = true
            if (ok) root.entries = r.entries || []
            else shell.notify ? shell.notify(r.message, true) : console.log("record:", r.message)
        })
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.entries = []; root.loaded = false }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s5
        spacing: Theme.s3

        PageHeader {
            width: parent.width
            title: "Record"
            subtitle: "Everything that happened, and who did it"
            Field {
                objectName: "recordSearch"
                width: 220
                iconName: "search"
                placeholderText: "Search the record"
                anchors.verticalCenter: parent.verticalCenter
                onTextEdited: root.searchText = text
            }
            Btn { objectName: "recordExport"; kind: "primary"; iconName: "download"; text: "Export" }
        }

        Rectangle {
            width: parent.width
            height: parent.height - y
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Table {
                id: table
                objectName: "recordTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                loading: !root.loaded
                pageSize: 12
                emptyText: "Nothing recorded yet"
                emptyHint: "Every act anyone takes lands here, with who took it."
                rows: root.searchText === "" ? root.rows : root.rows.filter(function (r) {
                    var q = root.searchText.toLowerCase()
                    return (r.who + " " + r.what + " " + r.subject).toLowerCase().indexOf(q) >= 0
                })
                columns: [
                    { title: "Time", key: "at", width: 80, mono: true,
                      tone: function () { return "mid" } },
                    { title: "Who", key: "who", width: 160,
                      filters: root.whoFilters },
                    { title: "What happened", key: "what" },
                    { title: "Subject", key: "subject", width: 130, mono: true,
                      tone: function () { return "mid" } },
                    { title: "Kind", key: "kind", width: 120, tag: true,
                      filters: ["session", "violation", "deviation", "action", "assistance", "task", "flow", "rollout"],
                      tone: function (r) {
                          return r.kind === "violation" ? "danger" : r.kind === "deviation" ? "warn" : ""
                      } }
                ]
            }
        }
    }

    property string searchText: ""
    readonly property var whoFilters: {
        var seen = {}, out = []
        for (var i = 0; i < rows.length; i++) if (!seen[rows[i].who]) { seen[rows[i].who] = true; out.push(rows[i].who) }
        return out.slice(0, 8)
    }
}
