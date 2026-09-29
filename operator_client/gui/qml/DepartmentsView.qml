import QtQuick
import "."

// WHO GOVERNS WHAT, and where nobody does -- the one condition on this page that needs an act.
Item {
    id: root

    property var tree: []
    property bool loaded: false
    property var chosen: null

    readonly property var rows: tree.map(function (d) {
        var admins = d.admins || [], machines = (d.workers || []).length
        return { department_id: d.department_id, name: d.name, machines: machines,
                 admins: admins.length,
                 governed: admins.length === 0 ? "nobody" : admins.map(function (a) { return a.name }).join(", "),
                 stateWord: admins.length === 0 ? "nobody governs it" : "governed" }
    })
    readonly property int ungoverned: rows.filter(function (r) { return r.admins === 0 }).length

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function (ok, r) { root.loaded = true; if (ok) root.tree = r.departments })
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
            title: "Departments"
            subtitle: root.rows.length + " departments"
                      + (root.ungoverned > 0 ? " \u00b7 " + root.ungoverned + " with nobody governing" : "")
            Btn { objectName: "newDepartment"; kind: "primary"; iconName: "plus"; text: "New department" }
        }

        Rectangle {
            width: parent.width
            height: parent.height - y
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Table {
                objectName: "departmentsTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                loading: !root.loaded
                pageSize: 12
                rows: root.rows
                emptyText: "No departments yet"
                emptyHint: "A department is where machines and the Admins who govern them live."
                onRowActivated: function (row) { root.chosen = row; detail.open() }
                columns: [
                    { title: "Department", key: "name", width: 200, strong: true },
                    { title: "Governed by", key: "governed",
                      tone: function (r) { return r.admins === 0 ? "danger" : "ink" } },
                    { title: "", key: "stateWord", width: 170, tag: true,
                      tone: function (r) { return r.admins === 0 ? "danger" : "" } },
                    { title: "Machines", key: "machines", width: 110, align: "right",
                      tone: function () { return "mid" } }
                ]
            }
        }
    }

    Drawer {
        id: detail
        objectName: "departmentDrawer"
        page: root
        title: root.chosen ? root.chosen.name : ""
        subtitle: root.chosen ? (root.chosen.machines + " machines") : ""

        Descriptions {
            width: parent.width
            items: root.chosen ? [
                { label: "Admins", value: root.chosen.governed,
                  tone: root.chosen.admins === 0 ? "danger" : "ink" },
                { label: "Machines", value: root.chosen.machines },
                { label: "State", value: root.chosen.stateWord, tag: true,
                  tone: root.chosen.admins === 0 ? "danger" : "" }
            ] : []
        }
        Txt {
            width: parent.width
            visible: root.chosen && root.chosen.admins === 0
            wrapMode: Text.WordWrap
            tone: "danger"
            font.pixelSize: Theme.fSmall
            text: "Nobody governs this department: its machines answer to no Admin, and its reports reach nobody."
        }

        footer: [
            Component { Btn { text: "Open" } },
            Component { Btn { kind: "primary"; text: "Assign Admin" } }
        ]
    }
}
