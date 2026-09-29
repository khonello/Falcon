import QtQuick
import "."

// EVERYBODY, AND THE ONE MACHINE EACH OF THEM HAS. One account is one PC -- they are provisioned
// together and they stay together, so this page and Machines are two views of the same fact.
//
// A name here is the name YOU gave them. Display Names do not travel between layers: what you call
// someone is yours, what they call themselves is what those below them see, and neither leaks.
Item {
    id: root

    property var tree: []
    property bool loaded: false
    property var chosen: null

    readonly property bool boss: falcon.role === "super_user"
    readonly property var rows: {
        var out = []
        for (var d = 0; d < tree.length; d++) {
            var dept = tree[d]
            // which list somebody is in IS their role here -- the tree is built that way, so it is
            // the answer even when the row does not carry the field
            var members = (dept.admins || []).map(function (a) { return { p: a, role: "admin" } })
                          .concat((dept.workers || []).map(function (a) { return { p: a, role: "worker" } }))
            for (var i = 0; i < members.length; i++) {
                var a = members[i].p
                var known = a.role || members[i].role
                // only an explicit non-active status means gone: a row that does not
                // carry one is not evidence that somebody left
                var away = !!a.status && a.status !== "active"
                out.push({ account_id: a.account_id, name: a.name || "unnamed",
                           role: known === "admin" ? "Admin" : known === "super_user" ? "Super User" : "Worker",
                           department: dept.name, machine: a.hostname || "",
                           pc_id: a.pc_id, status: a.status,
                           stateWord: away ? "offboarded" : a.session ? "signed in" : "not signed in",
                           stateTone: "",
                           here: !away && !!a.session })
            }
        }
        out.sort(function (a, b) { return String(a.name).localeCompare(String(b.name)) })
        return out
    }
    readonly property int unnamed: rows.filter(function (r) { return r.name === "unnamed" }).length

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function (ok, r) {
            root.loaded = true
            if (ok) root.tree = r.departments || []
        })
    }
    function rename(label) {
        if (!chosen) return
        falcon.call("hierarchy.set_display_name",
                    { account_id: chosen.account_id, label: label }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not renamed"); return }
            Msg.ok("Renamed, for you")
            root.refresh()
        })
    }
    function offboard() {
        falcon.call("hierarchy.account_offboard", { account_id: chosen.account_id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not offboarded"); return }
            Msg.ok("Offboarded")
            detail.close()
            root.refresh()
        })
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
            title: "People"
            subtitle: Theme.many(root.rows.length, "person", "people")
                      + (root.unnamed > 0 ? " · " + root.unnamed + " you have not named" : "")
            Btn {
                objectName: "newPerson"
                kind: "primary"
                iconName: "plus"
                text: "Add person"
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
                objectName: "peopleTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                loading: !root.loaded
                pageSize: 12
                rows: root.rows
                emptyText: "Nobody yet"
                emptyHint: "Adding a person provisions their machine at the same time: one account, one PC."
                onRowActivated: function (row) { root.chosen = row; detail.open() }
                columns: [
                    { title: "Name", key: "name", strong: true,
                      tone: function (r) { return r.name === "unnamed" ? "quiet" : "ink" } },
                    { title: "Role", key: "role", width: 140, tag: true,
                      filters: ["Super User", "Admin", "Worker"] },
                    { title: "Department", key: "department", width: 170,
                      filters: root.tree.map(function (d) { return d.name }) },
                    { title: "Machine", key: "machine", width: 150, mono: true,
                      tone: function () { return "mid" } },
                    { title: "State", key: "stateWord", width: 150, tag: true,
                      filters: ["signed in", "not signed in", "offboarded"] }
                ]
            }
        }
    }

    NewPerson {
        id: maker
        objectName: "newPersonModal"
        page: root
        departments: root.tree
        onMade: root.refresh()
    }

    Confirm {
        id: leaving
        objectName: "offboardConfirm"
        page: root
        title: "Offboard this person"
        cost: "Their account stops working and any session they are in ends now. Nothing is deleted: "
              + "the account, its machine and everything either of them did stay on the record."
        verb: "Offboard"
        destructive: true
        onAccepted: root.offboard()
    }

    Drawer {
        id: detail
        objectName: "personDrawer"
        page: root
        title: root.chosen ? root.chosen.name : ""
        subtitle: root.chosen ? (root.chosen.role + " · " + root.chosen.department) : ""

        Descriptions {
            width: parent.width
            items: root.chosen ? [
                { label: "Role", value: root.chosen.role, tag: true },
                { label: "Department", value: root.chosen.department },
                { label: "Machine", value: root.chosen.machine || "none", mono: true },
                { label: "State", value: root.chosen.stateWord, tag: true }
            ] : []
        }

        FormRow {
            width: parent.width
            label: "What you call them"
            hint: "Yours alone. They never see it, and neither does anybody else."
            Field {
                id: label
                objectName: "displayName"
                width: parent.width
                text: root.chosen && root.chosen.name !== "unnamed" ? root.chosen.name : ""
                placeholderText: "A name you will recognise"
                onAccepted: root.rename(text)
            }
        }

        // the Drawer's footer is a Row: order places these, not anchors
        footer: [
            Btn {
                objectName: "offboardPerson"
                danger: true
                text: "Offboard"
                visible: root.chosen && root.chosen.status === "active"
                onClicked: leaving.open()
            },
            Btn {
                objectName: "renamePerson"
                kind: "primary"
                text: "Rename"
                enabled: label.text.trim() !== ""
                onClicked: root.rename(label.text.trim())
            }
        ]
    }
}
