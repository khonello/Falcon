import QtQuick
import "."

// WHO GOVERNS WHAT, and where nobody does -- the one condition on this page that needs an act.
Item {
    id: root

    property var tree: []
    property bool loaded: false
    property var chosen: null
    property string look: "list"
    property var open: ({})

    // the same departments, seen as the shape they actually are: who governs, and what sits under them
    readonly property var branches: {
        var out = []
        for (var d = 0; d < tree.length; d++) {
            var dept = tree[d]
            var admins = dept.admins || [], workers = dept.workers || []
            out.push({ key: "d" + dept.department_id, label: dept.name,
                       sub: Theme.many(workers.length, "machine")
                            + (admins.length === 0 ? "  ·  nobody governs it" : ""),
                       depth: 0, kids: true,
                       tone: admins.length === 0 ? "danger" : "ink" })
            for (var a = 0; a < admins.length; a++)
                out.push({ key: "a" + admins[a].account_id, label: admins[a].name || "unnamed",
                           sub: "Admin", depth: 1 })
            for (var w = 0; w < workers.length; w++)
                out.push({ key: "w" + workers[w].pc_id, label: workers[w].hostname || "a machine",
                           sub: workers[w].name || "", depth: 1 })
        }
        return out
    }

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
    // opened the first time the hierarchy is looked at, however the look was changed
    onLookChanged: if (look === "tree" && Object.keys(open).length === 0) openAll()
    function openAll() {
        var all = ({})
        for (var i = 0; i < tree.length; i++) all["d" + tree[i].department_id] = true
        open = all
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
            Segmented {
                objectName: "departmentsLook"
                anchors.verticalCenter: parent.verticalCenter
                value: root.look
                options: [{ value: "list", label: "List" }, { value: "tree", label: "Hierarchy" }]
                onPicked: function (v) { root.look = v }
            }
            Btn { objectName: "newDepartment"; kind: "primary"; iconName: "plus"; text: "New department" }
        }

        Rectangle {
            width: parent.width
            height: parent.height - y
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Flickable {
                anchors.fill: parent
                anchors.margins: Theme.s4
                visible: root.look === "tree"
                contentHeight: hierarchy.implicitHeight
                clip: true

                Tree {
                    id: hierarchy
                    objectName: "departmentsTree"
                    width: parent.width
                    nodes: root.branches
                    open: root.open
                }
            }

            Table {
                objectName: "departmentsTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                visible: root.look === "list"
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
