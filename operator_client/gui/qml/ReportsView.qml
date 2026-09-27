import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// REPORTS (board RP03): a tall queue and three beside it.
//
//   left    to address (newest first), then what was addressed this week -- cards with bare icons
//   right   the chosen report said in a sentence, with where / found / who was told, and Mark addressed;
//           beneath, this week as ticks on a line (the ones still waiting stand taller, in their tone) and the
//           count by kind routed here
//
// A report row carries only its kind and a pointer to its source, so the sentence is found by reading the source
// through what the page may already read (violations, flows). What the Engine does not keep -- a summary, whether
// a report was seen -- is in design/ENGINE-WORK.md.
Item {
    id: root

    property var reports: []
    property var violations: []
    property var flows: []
    property int chosenId: 0
    property string clock: ""

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("reports.list", {}, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            root.reports = r.reports
            if (!root.chosen && r.reports.length) root.chosenId = (root.waiting[0] || r.reports[0]).id
        })
        falcon.call("resource.violations", { include_resolved: true }, function (ok, r) { if (ok) root.violations = r.violations })
        falcon.call("flow.list", {}, function (ok, r) { if (ok) root.flows = r.flows })
    }
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onScopeChanged() { if (falcon.isConnected) root.refresh() }
        function onPushReceived(type, p) { if (type.indexOf("report.") === 0) root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    readonly property var kinds: ({
        resource_violation: { word: "Resource violation", icon: "shield", tone: "danger", plural: "Violations" },
        directory_structure_conflict: { word: "Directory conflict", icon: "folder", tone: "warn", plural: "Conflicts" },
        flow_failure: { word: "Flow failure", icon: "flows", tone: "warn", plural: "Flow failures" },
        listener_report: { word: "Listener report", icon: "eye", tone: "accent", plural: "Listener" },
        cross_department_assistance: { word: "Help across departments", icon: "dept", tone: "accent", plural: "Across departments" },
        update_status: { word: "Update", icon: "pulse", tone: "warn", plural: "Updates" },
        deviation: { word: "Something unexpected", icon: "warn", tone: "danger", plural: "Unexpected" }
    })
    function kind(r) { return kinds[r.category] || { word: r.category, icon: "bell", tone: "", plural: r.category } }
    readonly property var chosen: { for (var i = 0; i < reports.length; i++) if (reports[i].id === chosenId) return reports[i]; return null }
    readonly property var waiting: reports.filter(function (r) { return !r.addressed_at })
    readonly property var addressedThisWeek: reports.filter(function (r) {
        return r.addressed_at && (Date.now() - new Date(r.addressed_at).getTime()) < 7 * 86400000
    })
    function timeOf(iso) { return iso ? Qt.formatDateTime(new Date(iso), "HH:mm") : "" }
    function dayOf(iso) {
        if (!iso) return ""
        var d = new Date(iso), now = new Date()
        return d.toDateString() === now.toDateString() ? timeOf(iso) : Qt.formatDateTime(d, "ddd")
    }

    // what a report is about, read from its source: { title, sentence, rows: [[label, value, tone]] }
    function about(r) {
        if (!r) return { title: "", sentence: "", rows: [] }
        var k = kind(r)
        if (r.source_table === "resource_violations") {
            var v = violations.filter(function (x) { return x.id === r.source_id })[0]
            if (v) {
                var tier = String(v.expected_tag || v.resource_tag || "").replace("worker_dept", "workers")
                return { title: "A " + tier + " file on " + v.hostname,
                         sentence: v.filename + ", " + tier + ", is on " + v.hostname + ".",
                         rows: [["Where", v.hostname + " · " + Automate.folderName(String(v.path).replace(/[\\/][^\\/]*$/, "")), ""],
                                ["Found", dayOf(v.detected_at) === timeOf(v.detected_at) ? "today, " + timeOf(v.detected_at) : dayOf(v.detected_at), ""],
                                ["The file", v.resolved_at ? "moved; it is in place now" : "still there, ignored until it moves", v.resolved_at ? "ok" : "warn"]] }
            }
        }
        if (r.source_table === "flow_destinations") {
            for (var i = 0; i < flows.length; i++) {
                var ds = flows[i].destinations || []
                for (var j = 0; j < ds.length; j++) if (ds[j].id === r.source_id) {
                    var f = flows[i], d = ds[j]
                    return { title: "A flow to " + (d.destination_hostname || "remote storage") + " stopped",
                             sentence: "Copying " + Automate.folderName(f.source_path) + " from " + f.source_hostname + " to "
                                       + (d.destination_hostname || "remote storage") + (d.paused_reason ? " is paused." : " failed, and has since resumed."),
                             rows: [["From", f.source_hostname + " · " + Automate.folderName(f.source_path), ""],
                                    ["To", (d.destination_hostname || "remote storage") + " · " + Automate.folderName(d.destination_path), ""],
                                    ["Now", d.paused_reason ? (d.suggestion || "paused") : "running again", d.paused_reason ? "warn" : "ok"]] }
                }
            }
        }
        var generic = {
            listener_report: "Someone added a listener to a conversation in your department.",
            cross_department_assistance: "Someone asked for help from outside their department.",
            update_status: "A machine is behind on its update.",
            directory_structure_conflict: "Two folders disagree about what they hold.",
            deviation: "Something happened that the rules did not expect."
        }
        return { title: k.word, sentence: generic[r.category] || k.word + ".", rows: [["Raised", dayOf(r.generated_at), ""]] }
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
                Txt { text: "Reports"; color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                Row {
                    spacing: 12
                    Txt { text: "Reports"; color: "#ffffff"; font.pixelSize: Theme.fTitle; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                    Txt { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody
                          color: root.waiting.length ? Theme.warn : Qt.rgba(1, 1, 1, 0.55)
                          text: root.waiting.length === 0 ? "nothing to address" : root.waiting.length + " to address" }
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
                id: queueCell
                objectName: "reportsQueue"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "To address"
                narration: ({ brief: root.waiting.length ? root.waiting.length + " waiting" : "none waiting", tone: root.waiting.length ? "warn" : "ok",
                              state: root.reports.length ? "ok" : "empty", note: "No reports", sentence: "Nothing routed here has happened yet." })
                Column {
                    width: parent.width
                    spacing: 10
                    PagedColumn {
                        width: parent.width
                        height: Math.min(root.waiting.length * 67, Math.max(67, queueCell.room * 0.55))
                        itemHeight: 58
                        model: root.waiting
                        delegate: InfoCard {
                            iconName: modelData ? root.kind(modelData).icon : ""
                            iconTone: modelData ? root.kind(modelData).tone : ""
                            title: modelData ? root.about(modelData).title : ""
                            line: modelData ? root.kind(modelData).word + " · " + root.dayOf(modelData.generated_at) : ""
                            stateWord: "to address"; stateTone: modelData ? root.kind(modelData).tone : ""
                            selected: modelData && modelData.id === root.chosenId
                            onClicked: root.chosenId = modelData.id
                        }
                    }
                    Txt { visible: root.waiting.length === 0; text: "Nothing waits on you."; color: Theme.ok; font.pixelSize: Theme.fBody }
                    Txt { visible: root.addressedThisWeek.length > 0; topPadding: 6; text: "Addressed this week"; color: Theme.dim
                          font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
                    PagedColumn {
                        visible: root.addressedThisWeek.length > 0
                        width: parent.width
                        height: Math.min(root.addressedThisWeek.length * 67, Math.max(67, queueCell.room * 0.4))
                        itemHeight: 58
                        model: root.addressedThisWeek
                        delegate: InfoCard {
                            iconName: modelData ? root.kind(modelData).icon : ""
                            iconTone: "ok"
                            title: modelData ? root.about(modelData).title : ""
                            line: modelData ? "addressed " + root.dayOf(modelData.addressed_at) : ""
                            stateWord: "addressed"
                            selected: modelData && modelData.id === root.chosenId
                            onClicked: root.chosenId = modelData.id
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                spacing: 20

                GridCell {
                    objectName: "reportChosen"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    topAlign: true
                    readonly property var info: root.about(root.chosen)
                    title: info.title || "A report"
                    narration: ({ brief: !root.chosen ? "" : root.chosen.addressed_at ? "addressed" : "new",
                                  tone: root.chosen && root.chosen.addressed_at ? "ok" : "danger",
                                  state: root.chosen ? "ok" : "empty", note: "Nothing chosen", sentence: "Pick a report on the left." })
                    Column {
                        visible: root.chosen !== null
                        width: parent.width
                        spacing: 12
                        Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.ink; font.pixelSize: Theme.fSection + 1; font.weight: Font.DemiBold
                              text: root.about(root.chosen).sentence }
                        Repeater {
                            model: root.about(root.chosen).rows
                            delegate: Item {
                                required property var modelData
                                width: parent.width; height: 34
                                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                                Txt { anchors.verticalCenter: parent.verticalCenter; text: modelData[0]; color: Theme.dim; font.pixelSize: Theme.fBody }
                                Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: modelData[1]
                                      color: modelData[2] ? Theme.tone(modelData[2]) : Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                            }
                        }
                        Item {
                            width: parent.width; height: 36
                            TBtn { objectName: "markAddressed"; visible: root.chosen && !root.chosen.addressed_at && falcon && falcon.role === "admin"
                                   tone: "ok"; text: "Mark addressed"; iconName: "check"; anchors.verticalCenter: parent.verticalCenter
                                   onClicked: falcon.call("reports.mark", { report_id: root.chosen.id }, function (ok, r) {
                                       shell.notify(ok ? "Addressed" : r.message, !ok); root.refresh() }) }
                            Txt { visible: root.chosen && !!root.chosen.addressed_at; anchors.verticalCenter: parent.verticalCenter
                                  text: root.chosen ? "Addressed " + root.dayOf(root.chosen.addressed_at) : ""; color: Theme.ok; font.pixelSize: Theme.fBody }
                            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; color: Theme.faint; font.pixelSize: Theme.fMeta
                                  text: "the Super User keeps their own copy" }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 300
                    Layout.maximumHeight: 300
                    Layout.fillHeight: false
                    spacing: 20

                    // this week: a tick per report on a line; the waiting ones stand taller, in their tone
                    GridCell {
                        objectName: "reportsWeek"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 3
                        Layout.fillHeight: true
                        topAlign: true
                        title: "This week"
                        narration: ({ brief: "a timeline", state: "ok" })
                        Column {
                            width: parent.width
                            spacing: 12
                            Item {
                                id: week
                                width: parent.width; height: 110
                                readonly property var start: { var d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() - 6); return d }
                                Rectangle { y: 80; width: parent.width; height: 1; color: Theme.line2 }
                                Repeater {
                                    model: 7
                                    delegate: Txt {
                                        required property int index
                                        x: week.width * index / 7; y: 90
                                        text: { var d = new Date(week.start); d.setDate(d.getDate() + index); return Qt.formatDate(d, "ddd") }
                                        color: Theme.faint; font.pixelSize: Theme.fMeta
                                    }
                                }
                                Repeater {
                                    model: root.reports.filter(function (r) { return new Date(r.generated_at) >= week.start })
                                    delegate: Rectangle {
                                        required property var modelData
                                        readonly property real at: (new Date(modelData.generated_at) - week.start) / (7 * 86400000)
                                        x: week.width * at; width: 3; radius: 1.5
                                        height: modelData.addressed_at ? 18 : 40; y: 80 - height
                                        color: modelData.addressed_at ? Theme.line2 : Theme.tone(root.kind(modelData).tone || "warn")
                                    }
                                }
                            }
                            Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta
                                  text: "Every report is a tick. The ones still waiting stand taller, in their tone." }
                        }
                    }
                    GridCell {
                        objectName: "reportsKinds"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 2
                        Layout.fillHeight: true
                        topAlign: true
                        title: "By kind"
                        narration: ({ brief: "routed here", state: "ok" })
                        Column {
                            width: parent.width
                            Repeater {
                                model: {
                                    var counts = {}, out = []
                                    for (var i = 0; i < root.reports.length; i++) counts[root.reports[i].category] = (counts[root.reports[i].category] || 0) + 1
                                    for (var k in counts) out.push({ k: k, n: counts[k] })
                                    return out.sort(function (a, b) { return b.n - a.n })
                                }
                                delegate: Item {
                                    required property var modelData
                                    width: parent.width; height: 32
                                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                                    Txt { anchors.verticalCenter: parent.verticalCenter; text: root.kind({ category: modelData.k }).plural; color: Theme.dim; font.pixelSize: Theme.fBody }
                                    Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: String(modelData.n)
                                          color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.Bold }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
