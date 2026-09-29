import QtQuick
import "."

// FOLDERS AS POLICY. A tier folder is not storage with a label on it -- which shelf a file sits on IS
// who may have it. So the shelves come first and the violations second: a violation is only ever a
// file that ended up on the wrong shelf.
Item {
    id: root

    property var shelves: []
    property var violations: []
    property bool loaded: false
    property var chosen: null

    readonly property var words: ({
        "admin": "Admins only",
        "restricted": "Named people only",
        "worker_dept": "The department",
        "workers": "The department",
        "common": "Anybody here"
    })

    readonly property var rows: violations.map(function (v) {
        return { violation_id: v.violation_id || v.id, file: v.filename || v.path || "a file",
                 machine: v.hostname || "a machine",
                 tier: root.words[v.resource_tag] || v.resource_tag || "",
                 when: Task.when(v.detected_at || v.created_at),
                 resolved: !!v.resolved_at,
                 stateWord: v.resolved_at ? "sorted" : "out of place",
                 stateTone: v.resolved_at ? "" : "danger" }
    })
    readonly property int loose: rows.filter(function (r) { return !r.resolved }).length

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("resource.shelves", {}, function (ok, r) {
            root.loaded = true
            if (ok) root.shelves = r.shelves || []
        })
        falcon.call("resource.violations", { include_resolved: true }, function (ok, r) {
            if (ok) root.violations = r.violations || []
        })
    }
    function resolve() {
        if (!chosen) return
        falcon.call("resource.resolve", { violation_id: chosen.violation_id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not marked"); return }
            Msg.ok("Marked sorted")
            detail.close()
            root.refresh()
        })
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.shelves = []; root.violations = []; root.loaded = false }
        function onPushReceived(type) { if (String(type).indexOf("resource.") === 0) root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s5
        spacing: Theme.s3

        PageHeader {
            width: parent.width
            title: "Resources"
            subtitle: Theme.many(root.shelves.length, "shelf", "shelves")
                      + (root.loose > 0 ? " · " + Theme.many(root.loose, "file")
                                          + " out of place" : "")
        }

        // the shelves: which folder means which access, and how much is on it
        Row {
            width: parent.width
            spacing: Theme.s3

            Repeater {
                model: root.shelves
                delegate: Rectangle {
                    required property var modelData
                    width: (root.width - 2 * Theme.s5 - 3 * Theme.s3) / 4
                    height: 84
                    radius: Theme.radiusLg
                    color: Theme.fill
                    border.width: 1
                    border.color: Theme.split

                    Column {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.margins: Theme.s3
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        Txt {
                            width: parent.width
                            text: modelData.folder
                            strong: true
                            mono: true
                            font.pixelSize: Theme.fSmall
                        }
                        Txt {
                            width: parent.width
                            text: root.words[modelData.tag] || modelData.tag
                            tone: "mid"
                            font.pixelSize: Theme.fSmall
                        }
                        Txt {
                            width: parent.width
                            text: Theme.many(modelData.files, "file")
                            tone: "quiet"
                            font.pixelSize: Theme.fSmall
                        }
                    }
                }
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
                objectName: "violationsTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                loading: !root.loaded
                pageSize: 10
                rows: root.rows
                emptyText: "Everything is where it belongs"
                emptyHint: "A file on the wrong shelf shows up here the moment the index sees it."
                onRowActivated: function (row) { root.chosen = row; detail.open() }
                columns: [
                    { title: "File", key: "file", mono: true, strong: true },
                    { title: "Found on", key: "machine", width: 150, mono: true },
                    { title: "Belongs to", key: "tier", width: 180,
                      tone: function () { return "mid" } },
                    { title: "State", key: "stateWord", width: 150, tag: true,
                      filters: ["out of place", "sorted"],
                      tone: function (r) { return r.stateTone } },
                    { title: "Found", key: "when", width: 160, mono: true,
                      tone: function () { return "mid" } }
                ]
            }
        }
    }

    Drawer {
        id: detail
        objectName: "violationDrawer"
        page: root
        title: root.chosen ? root.chosen.file : ""
        subtitle: root.chosen ? ("on " + root.chosen.machine) : ""

        Descriptions {
            width: parent.width
            items: root.chosen ? [
                { label: "Found on", value: root.chosen.machine, mono: true },
                { label: "Belongs to", value: root.chosen.tier },
                { label: "State", value: root.chosen.stateWord, tag: true, tone: root.chosen.stateTone },
                { label: "Found", value: root.chosen.when, mono: true }
            ] : []
        }
        Alert {
            width: parent.width
            visible: root.chosen && !root.chosen.resolved
            kind: "danger"
            text: "Move it or delete it on the machine first. Marking it sorted here only stops the "
                  + "reminder -- if the copy is still there, the next event flags it again."
        }

        // the Drawer's footer is a Row: order places these, not anchors
        footer: [
            Btn {
                objectName: "resolveViolation"
                kind: "primary"
                text: "Mark sorted"
                visible: root.chosen && !root.chosen.resolved
                onClicked: root.resolve()
            }
        ]
    }
}
