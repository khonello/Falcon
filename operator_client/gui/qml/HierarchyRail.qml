import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// The hierarchy, always visible: Department -> Admin -> Client PC, each PC with its session state.
// A left rail rather than a page of its own so selection can never become a hidden mode -- the
// selected account/PC is the context every page works on (traverse it, assign it a task, run an
// action on it, ping it). Rows are dense and quiet; colour appears only where it means something:
// a session dot per PC, a role tint, an accent edge on the selected row.
Rectangle {
    id: rail
    color: Theme.surface

    property var tree: []                  // hierarchy.tree departments
    property var selected: null            // {account_id, name, pc_id, hostname, role, session, department_id, department_name}
    readonly property int pcCount: tree.reduce(function(n, d) { return n + d.admins.length + d.workers.length }, 0)

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function(ok, r) {
            if (!ok) { root.notify(r.message, true); return }
            rail.tree = r.departments
            if (rail.selected) {                     // keep the selection pointing at fresh data
                var again = rail.find(rail.selected.account_id)
                rail.selected = again
            }
        })
    }
    function find(accountId) {
        for (var i = 0; i < tree.length; i++) {
            var d = tree[i], all = d.admins.concat(d.workers)
            for (var j = 0; j < all.length; j++)
                if (all[j].account_id === accountId) return rail.withDept(all[j], d)
        }
        return null
    }
    function withDept(a, d) {
        var o = {}
        for (var k in a) o[k] = a[k]
        o.department_id = d.department_id; o.department_name = d.name
        return o
    }
    function sessionWord(s) {
        if (!s) return "free"
        if (s.occupied_via === "native") return "native"
        return s.occupied_via + " · " + (s.occupant_name || "")
    }

    Connections {
        target: falcon
        function onConnected() { rail.refresh() }
        function onDisconnected() { rail.tree = []; rail.selected = null }
        function onPushReceived(type, p) {
            if (type.indexOf("session.") === 0 || type.indexOf("assisted_access.") === 0 || type === "hierarchy.changed") rail.refresh()
        }
    }
    Component.onCompleted: refresh()

    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.border }

    ColumnLayout {
        anchors.fill: parent
        anchors.rightMargin: 1
        spacing: 0

        // --- header ------------------------------------------------------------------------------
        Item {
            Layout.fillWidth: true
            implicitHeight: 40
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space3; anchors.rightMargin: Theme.space2
                spacing: Theme.space2
                Eyebrow { label: "Hierarchy" }
                Rectangle {
                    implicitWidth: countLabel.implicitWidth + 12; implicitHeight: 16; radius: 8
                    color: Qt.rgba(1, 1, 1, 0.06)
                    Label { id: countLabel; anchors.centerIn: parent; text: rail.pcCount; color: Theme.textFaint; font.pixelSize: Theme.fontTiny; font.bold: true }
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: "Refresh"; color: refreshHover.hovered ? Theme.text : Theme.textFaint; font.pixelSize: Theme.fontSmall
                    HoverHandler { id: refreshHover }
                    TapHandler { onTapped: rail.refresh() }
                }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
        }

        // --- me ----------------------------------------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 44
            color: "transparent"
            visible: falcon.isConnected
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.space3; anchors.rightMargin: Theme.space3
                spacing: Theme.space2
                Rectangle { width: 7; height: 7; radius: 4; color: Theme.roleTint(falcon.role) }
                ColumnLayout {
                    spacing: 1
                    Layout.fillWidth: true
                    Label { text: "You"; color: Theme.text; font.pixelSize: Theme.fontBody; font.bold: true }
                    Label { text: Theme.roleLabel(falcon.role) + "  ·  account " + falcon.accountId + "  ·  pc " + falcon.pcId + (falcon.departmentId ? "  ·  dept " + falcon.departmentId : "")
                            color: Theme.textFaint; font.pixelSize: Theme.fontTiny; font.family: Theme.mono; elide: Text.ElideRight; Layout.fillWidth: true }
                }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
        }

        // --- the tree ----------------------------------------------------------------------------
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: rail.tree
            delegate: ColumnLayout {
                id: dept
                required property var modelData
                width: list.width
                spacing: 0

                Item {
                    Layout.fillWidth: true
                    implicitHeight: 30
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.space3; anchors.rightMargin: Theme.space3
                        spacing: Theme.space2
                        Label { text: dept.modelData.name; color: Theme.text; font.pixelSize: Theme.fontSmall; font.bold: true; font.letterSpacing: 0.8 }
                        Label { text: "dept " + dept.modelData.department_id; color: Theme.textFaint; font.pixelSize: Theme.fontTiny; font.family: Theme.mono }
                        Item { Layout.fillWidth: true }
                        Label { text: dept.modelData.admins.length + " admin" + (dept.modelData.admins.length === 1 ? "" : "s") + " · " + dept.modelData.workers.length + " pc" + (dept.modelData.workers.length === 1 ? "" : "s")
                                color: Theme.textFaint; font.pixelSize: Theme.fontTiny }
                    }
                }

                Repeater {
                    model: dept.modelData.admins.concat(dept.modelData.workers)
                    delegate: Rectangle {
                        id: row
                        required property var modelData
                        readonly property bool selected: rail.selected !== null && rail.selected.account_id === modelData.account_id
                        readonly property color sessionTint: Theme.sessionTint(modelData.session)
                        Layout.fillWidth: true
                        implicitHeight: 40
                        color: selected ? Theme.wash(Theme.accent, 0.12) : (hover.hovered ? Qt.rgba(1, 1, 1, 0.04) : "transparent")
                        Behavior on color { ColorAnimation { duration: Theme.durationFast } }

                        Rectangle { visible: row.selected; anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 2; color: Theme.accent }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: row.modelData.role === "admin" ? Theme.space3 : Theme.space5
                            anchors.rightMargin: Theme.space3
                            spacing: Theme.space2
                            Rectangle {
                                width: 7; height: 7; radius: 4; color: row.sessionTint
                                SequentialAnimation on opacity {
                                    running: !!row.modelData.session && row.modelData.session.occupied_via !== "native"
                                    loops: Animation.Infinite
                                    NumberAnimation { to: 0.3; duration: 900 } NumberAnimation { to: 1; duration: 900 }
                                }
                            }
                            ColumnLayout {
                                spacing: 1
                                Layout.fillWidth: true
                                RowLayout {
                                    spacing: Theme.space2
                                    Label { text: Theme.roleLabel(row.modelData.role); color: Theme.roleTint(row.modelData.role); font.pixelSize: 9; font.bold: true; font.letterSpacing: 0.8 }
                                    Label { text: row.modelData.name; color: row.selected ? Theme.text : Theme.textDim; font.pixelSize: Theme.fontBody; font.bold: row.selected; elide: Text.ElideRight; Layout.fillWidth: true }
                                }
                                Label { text: row.modelData.hostname + "  ·  pc " + row.modelData.pc_id; color: Theme.textFaint; font.pixelSize: Theme.fontTiny; font.family: Theme.mono; elide: Text.ElideRight; Layout.fillWidth: true }
                            }
                            Label { text: rail.sessionWord(row.modelData.session).toUpperCase(); color: row.sessionTint; font.pixelSize: 9; font.bold: true; font.letterSpacing: 0.6; elide: Text.ElideRight; Layout.maximumWidth: 110 }
                        }
                        HoverHandler { id: hover }
                        TapHandler { onTapped: rail.selected = rail.withDept(row.modelData, dept.modelData) }
                    }
                }
            }
            ScrollBar.vertical: ScrollBar { }
        }

        Label {
            visible: !falcon.isConnected
            Layout.fillWidth: true
            Layout.margins: Theme.space3
            text: "Not connected to an Engine."
            color: Theme.textFaint
            font.pixelSize: Theme.fontSmall
            horizontalAlignment: Text.AlignHCenter
        }
    }
}
