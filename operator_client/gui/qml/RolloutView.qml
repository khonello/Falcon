import QtQuick
import "."

// N AND N+1, NEVER MORE. A version is approved only when every machine is confirmed on the current
// one, so this page's real subject is the machines that are not -- they are what the gate is held on.
Item {
    id: root

    property var version: null
    property var departments: []
    property var behind: []
    property bool loaded: false
    property var chosen: null

    readonly property bool boss: falcon.role === "super_user"
    readonly property var rows: behind.map(function (b) {
        return { pc_id: b.pc_id, host: b.hostname || "a machine", department: b.department_name || "",
                 department_id: b.department_id,
                 at: b.version || "unknown", tries: b.attempts !== undefined ? b.attempts : 0,
                 stateWord: b.escalated ? "past the limit" : "behind",
                 stateTone: b.escalated ? "danger" : "warn",
                 line: b.escalated ? "it has tried and failed too often" : "it has not taken it yet" }
    })
    readonly property int stuck: rows.filter(function (r) { return r.stateTone === "danger" }).length
    readonly property bool clear: loaded && rows.length === 0

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("updates.rollout_health", {}, function (ok, r) {
            root.loaded = true
            if (!ok) return
            root.version = r.version || null
            root.departments = r.departments || []
            root.behind = r.pcs_behind || []
        })
    }
    function act(type, payload, said) {
        falcon.call(type, payload, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "It did not go through"); return }
            Msg.ok(said)
            root.refresh()
        })
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.behind = []; root.loaded = false }
        function onPushReceived(type) { if (String(type).indexOf("update") === 0) root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s5
        spacing: Theme.s3

        PageHeader {
            width: parent.width
            title: "Rollout"
            subtitle: (root.version ? "Everyone should be on " + root.version.version_string
                                    : "No version approved yet")
                      + (root.rows.length > 0 ? " · " + root.rows.length + " not there yet" : "")
            Btn {
                objectName: "rollOut"
                kind: "primary"
                text: "Roll out"
                visible: !root.boss
                onClicked: root.act("updates.rollout_department", {}, "Rolling out")
            }
            Btn {
                objectName: "approveVersion"
                kind: "primary"
                text: "Approve next"
                visible: root.boss
                enabled: root.clear
                onClicked: approve.open()
            }
        }

        // how far each department has got, because the gate is held department by department
        Rectangle {
            width: parent.width
            height: bars.implicitHeight + 2 * Theme.s4
            visible: root.departments.length > 0
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Column {
                id: bars
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: Theme.s4
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.s3

                Repeater {
                    model: root.departments
                    delegate: Row {
                        required property var modelData
                        width: bars.width
                        spacing: Theme.s3
                        readonly property int total: modelData.total || 0
                        readonly property int on: modelData.on_current || 0

                        Txt {
                            width: 160
                            text: modelData.name || ""
                            font.pixelSize: Theme.fSmall
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Progress {
                            width: parent.width - 160 - 180 - 2 * Theme.s3
                            anchors.verticalCenter: parent.verticalCenter
                            value: parent.total === 0 ? 0 : parent.on / parent.total
                            tone: parent.on === parent.total ? "accent" : "warn"
                        }
                        Txt {
                            width: 180
                            text: parent.on + " of " + parent.total + " on it"
                            tone: "mid"
                            font.pixelSize: Theme.fSmall
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }
        }

        Alert {
            width: parent.width
            visible: root.boss && !root.clear && root.loaded
            kind: "warn"
            text: "The next version cannot be approved while any machine is still behind. That is the "
                  + "rule, not a setting: the fleet never has more than two versions in flight."
        }

        Rectangle {
            width: parent.width
            height: parent.height - y
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Table {
                objectName: "behindTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                loading: !root.loaded
                pageSize: 12
                rows: root.rows
                emptyText: "Every machine is on it"
                emptyHint: "Nothing is holding the gate. The next version can be approved."
                onRowActivated: function (row) { root.chosen = row; detail.open() }
                columns: [
                    { title: "Machine", key: "host", width: 160, mono: true, strong: true },
                    { title: "Department", key: "department", width: 180 },
                    { title: "State", key: "stateWord", width: 160, tag: true,
                      filters: ["behind", "past the limit"],
                      tone: function (r) { return r.stateTone } },
                    { title: "Why", key: "line",
                      tone: function (r) { return r.stateTone } },
                    { title: "Sitting on", key: "at", width: 130, mono: true,
                      tone: function () { return "mid" } }
                ]
            }
        }
    }

    Confirm {
        id: approve
        objectName: "approveConfirm"
        page: root
        title: "Approve the next version"
        cost: "Every machine starts taking it, department by department, as each Admin rolls it out. "
              + "Until they are all confirmed on it, no version after this one can be approved."
        verb: "Approve"
        onAccepted: nextVersion.open()
    }

    Modal {
        id: nextVersion
        objectName: "versionModal"
        page: root
        width: 440
        title: "Which version"
        subtitle: "The one the machines should end up on."

        property string typed: ""

        onAboutToShow: { typed = ""; field.text = "" }

        FormRow {
            width: parent.width
            label: "Version"
            required: true
            hint: "As the build calls itself, for example 1.4.3."
            Field {
                id: field
                objectName: "versionField"
                width: parent.width
                placeholderText: "1.4.3"
                onTextChanged: nextVersion.typed = text
            }
        }

        footer: [
            Btn {
                text: "Cancel"
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: send.left
                anchors.rightMargin: Theme.s2
                onClicked: nextVersion.close()
            },
            Btn {
                id: send
                objectName: "versionSubmit"
                kind: "primary"
                text: "Approve"
                enabled: nextVersion.typed.trim() !== ""
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: Theme.s5
                onClicked: {
                    root.act("updates.approve", { version: nextVersion.typed.trim() }, "Approved")
                    nextVersion.close()
                }
            }
        ]
    }

    Drawer {
        id: detail
        objectName: "behindDrawer"
        page: root
        title: root.chosen ? root.chosen.host : ""
        subtitle: root.chosen ? root.chosen.line : ""

        Descriptions {
            width: parent.width
            items: root.chosen ? [
                { label: "Department", value: root.chosen.department },
                { label: "Sitting on", value: root.chosen.at, mono: true },
                { label: "Should be on", value: root.version ? root.version.version_string : "—",
                  mono: true },
                { label: "State", value: root.chosen.stateWord, tag: true, tone: root.chosen.stateTone }
            ] : []
        }
        Alert {
            width: parent.width
            visible: root.chosen && root.chosen.stateTone === "danger"
            kind: "danger"
            text: "It has failed often enough that somebody has to look at the machine itself."
        }

        // the Drawer's footer is a Row: order places these, not anchors
        footer: [
            Btn {
                objectName: "promptAdmin"
                kind: "primary"
                text: "Ask Admin"
                visible: root.boss
                onClicked: root.act("updates.prompt_admin",
                                    { department_id: root.chosen.department_id }, "Asked")
            }
        ]
    }
}
