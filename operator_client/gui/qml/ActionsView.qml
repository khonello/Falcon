import QtQuick
import "."

// THE LIBRARY: the things that can be made to happen on a machine. An Action is written once and run
// from here or from an automation. Every one of them has its own timeout, because every one of them
// is a detached process on somebody's PC -- the console never hides that.
Item {
    id: root

    property var builtin: ({})
    property var groups: ({})
    property bool loaded: false
    property var chosen: null

    readonly property var rows: {
        var out = []
        var kinds = ["control", "monitoring", "custom"]
        for (var k = 0; k < kinds.length; k++) {
            var list = groups[kinds[k]] || []
            for (var i = 0; i < list.length; i++) {
                var a = list[i]
                out.push({ action_id: a.id, kind: kinds[k], name: Doing.actionName(a),
                           does: Doing.kindWord(kinds[k]),
                           language: a.custom_script_language || "",
                           timeout: a.timeout_seconds + "s",
                           script: a.custom_script || "",
                           description: a.description || "",
                           action: a })
            }
        }
        out.sort(function (a, b) { return String(a.name).localeCompare(String(b.name)) })
        return out
    }

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("control.action_list", {}, function (ok, r) {
            root.loaded = true
            if (!ok) return
            root.builtin = r.builtin || {}
            root.groups = r.actions || {}
        })
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.groups = ({}); root.loaded = false }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s5
        spacing: Theme.s3

        PageHeader {
            width: parent.width
            title: "Actions"
            subtitle: root.rows.length + " in the library"
            Btn {
                objectName: "newAction"
                kind: "primary"
                iconName: "plus"
                text: "New action"
                onClicked: maker.open()
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
                objectName: "actionsTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                loading: !root.loaded
                pageSize: 12
                rows: root.rows
                emptyText: "Nothing in the library yet"
                emptyHint: "An Action is one thing a machine can be made to do. Write it once, run it anywhere."
                onRowActivated: function (row) { root.chosen = row; detail.open() }
                columns: [
                    { title: "Action", key: "name", strong: true },
                    { title: "Kind", key: "kind", width: 140, tag: true,
                      filters: ["control", "monitoring", "custom"] },
                    { title: "What it is", key: "does", width: 200,
                      tone: function () { return "mid" } },
                    { title: "Gives up after", key: "timeout", width: 130, mono: true, align: "right",
                      tone: function () { return "mid" } }
                ]
            }
        }
    }

    NewAction {
        id: maker
        objectName: "newActionModal"
        page: root
        builtin: root.builtin
        onMade: root.refresh()
    }

    RunAction {
        id: runner
        objectName: "runActionModal"
        page: root
        action: root.chosen
        onRan: detail.close()
    }

    Drawer {
        id: detail
        objectName: "actionDrawer"
        page: root
        title: root.chosen ? root.chosen.name : ""
        subtitle: root.chosen ? root.chosen.does : ""

        Descriptions {
            width: parent.width
            items: root.chosen ? [
                { label: "Kind", value: root.chosen.kind, tag: true },
                { label: "Gives up after", value: root.chosen.timeout, mono: true },
                { label: "Language", value: root.chosen.language || "not a script" }
            ] : []
        }
        Txt {
            width: parent.width
            visible: root.chosen && root.chosen.description !== ""
            text: root.chosen ? root.chosen.description : ""
            tone: "mid"
            font.pixelSize: Theme.fSmall
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
        }

        ScriptPanel {
            objectName: "actionScript"
            width: parent.width
            visible: root.chosen && root.chosen.script !== ""
            readOnly: true
            language: root.chosen ? root.chosen.language : "python"
            text: root.chosen ? root.chosen.script : ""
        }

        Alert {
            width: parent.width
            visible: root.chosen && root.chosen.kind === "custom"
            kind: "warn"
            text: "A custom Action runs unsandboxed, as the machine's own user."
        }

        // the Drawer's footer is a Row: order places these, not anchors
        footer: [
            Btn {
                objectName: "runAction"
                kind: "primary"
                text: "Run"
                onClicked: runner.open()
            }
        ]
    }
}
