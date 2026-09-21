import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Department -> Admin -> Client PC, with live session state. Traverse / end / extend, display
// names, assisted access. Everything comes from hierarchy.tree; pushes trigger a refresh.
Item {
    id: view
    property var tree: []
    property var selected: null      // {account_id, name, pc_id, hostname, role, session}

    function refresh() {
        falcon.call("hierarchy.tree", {}, function(ok, r) { if (ok) view.tree = r.departments; else root.notify(r.message, true) })
    }
    function sessionText(s) {
        if (!s) return "free"
        var tag = s.occupied_via === "native" ? "native" : s.occupied_via.toUpperCase()
        return tag + " by " + s.occupant_name + (s.deadline_at ? " until " + s.deadline_at.substring(11, 16) : "")
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Connections {
        target: falcon
        function onConnected() { view.refresh() }
        function onPushReceived(type, p) {
            if (type.indexOf("session.") === 0 || type.indexOf("assisted_access.") === 0) view.refresh()
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 10

        // the tree
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            RowLayout {
                Label { text: "Hierarchy"; font.pixelSize: 18; color: "white" }
                Item { Layout.fillWidth: true }
                Button { text: "Refresh"; onClicked: view.refresh() }
            }
            ListView {
                id: list
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: view.tree
                spacing: 6
                delegate: ColumnLayout {
                    required property var modelData
                    width: list.width
                    spacing: 2
                    Label { text: modelData.name + "   (department " + modelData.department_id + ")"; color: "#ffd166"; font.bold: true }
                    Repeater {
                        model: modelData.admins.concat(modelData.workers)
                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            height: 30
                            color: view.selected && view.selected.account_id === modelData.account_id ? "#3a4a6a" : "#232529"
                            radius: 4
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: modelData.role === "admin" ? 12 : 32
                                anchors.rightMargin: 8
                                Label { text: modelData.role === "admin" ? "ADMIN" : "WORKER"; color: "#9aa"; font.pixelSize: 11; Layout.preferredWidth: 60 }
                                Label { text: modelData.name; color: "white"; Layout.preferredWidth: 200; elide: Text.ElideRight }
                                Label { text: modelData.hostname + " (pc " + modelData.pc_id + ")"; color: "#ccc"; Layout.preferredWidth: 180 }
                                Label { text: view.sessionText(modelData.session); Layout.fillWidth: true
                                        color: !modelData.session ? "#6bff8a" : (modelData.session.occupied_via === "native" ? "#ccc" : "#ff9f43") }
                            }
                            MouseArea { anchors.fill: parent; onClicked: view.selected = modelData }
                        }
                    }
                }
                ScrollBar.vertical: ScrollBar { }
            }
        }

        // the selection pane
        Rectangle {
            Layout.preferredWidth: 340
            Layout.fillHeight: true
            color: "#26282c"
            radius: 6
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8
                Label { text: view.selected ? view.selected.name : "Select an account"; font.pixelSize: 16; color: "white" }
                Label { visible: !!view.selected; color: "#ccc"; wrapMode: Text.Wrap; Layout.fillWidth: true
                        text: view.selected ? (view.selected.role + " · account " + view.selected.account_id + " · pc " + view.selected.pc_id
                                               + " · " + view.selected.hostname + "\n" + view.sessionText(view.selected.session)) : "" }

                GroupBox { title: "Traversal"; Layout.fillWidth: true; visible: !!view.selected
                    ColumnLayout { anchors.fill: parent
                        RowLayout {
                            Button { text: "Traverse"; enabled: !!view.selected
                                     onClicked: falcon.call("hierarchy.traverse", {pc_id: view.selected.pc_id, force: false}, view.afterTraverse) }
                            Button { text: "Block-or-end & enter"; enabled: !!view.selected
                                     onClicked: falcon.call("hierarchy.traverse", {pc_id: view.selected.pc_id, force: true}, view.afterTraverse) }
                        }
                        RowLayout {
                            Button { text: "End my session"; enabled: falcon.traversing
                                     onClicked: falcon.call("hierarchy.end_session", {session_id: falcon.session.session_id}, view.afterSimple) }
                            Button { text: "Extend"; enabled: falcon.traversing
                                     onClicked: falcon.call("hierarchy.extend_session", {session_id: falcon.session.session_id}, view.afterSimple) }
                            Button { text: "End their session"; visible: view.selected && view.selected.session && view.selected.session.occupied_via !== "native"
                                     onClicked: falcon.call("hierarchy.end_session", {session_id: view.selected.session.session_id}, view.afterSimple) }
                        }
                    }
                }

                GroupBox { title: "Display name (private to your view)"; Layout.fillWidth: true; visible: !!view.selected
                    RowLayout { anchors.fill: parent
                        TextField { id: label; Layout.fillWidth: true; placeholderText: "label" }
                        Button { text: "Set"; enabled: label.text.length > 0
                                 onClicked: falcon.call("hierarchy.set_display_name", {account_id: view.selected.account_id, label: label.text},
                                                        function(ok, r) { root.notify(ok ? "named " + r.label : r.message, !ok); if (ok) { label.text = ""; view.refresh() } }) }
                    }
                }

                GroupBox { title: "Your self name (seen by those below you)"; Layout.fillWidth: true
                    RowLayout { anchors.fill: parent
                        TextField { id: selfName; Layout.fillWidth: true; placeholderText: "name" }
                        Button { text: "Set"; onClicked: falcon.call("hierarchy.set_self_name", {label: selfName.text},
                                                                  function(ok, r) { root.notify(ok ? "self name set" : r.message, !ok); view.refresh() }) }
                    }
                }

                GroupBox { title: "Assisted access (Admin ↔ Admin, by consent)"; Layout.fillWidth: true; visible: falcon.role === "admin"
                    ColumnLayout { anchors.fill: parent
                        RowLayout {
                            CheckBox { id: avail; text: "I am available to help"
                                       onToggled: falcon.call("assisted_access.set_available", {available: checked},
                                                              function(ok, r) { root.notify(ok ? (r.available ? "available for assistance" : "not available") : r.message, !ok) }) }
                        }
                        RowLayout {
                            TextField { id: deptReq; Layout.preferredWidth: 90; placeholderText: "dept id" }
                            Button { text: "Request help"
                                     onClicked: falcon.call("assisted_access.request", deptReq.text.length ? {department_id: parseInt(deptReq.text)} : {},
                                                            function(ok, r) { root.notify(ok ? (r.matched ? "offered to " + r.helper_name + " (request " + r.request_id + ")" : r.message) : r.message, !ok) }) }
                        }
                        RowLayout {
                            TextField { id: reqId; Layout.preferredWidth: 90; placeholderText: "request id" }
                            Button { text: "Accept"; onClicked: falcon.call("assisted_access.accept", {request_id: parseInt(reqId.text)},
                                                                            function(ok, r) { root.notify(ok ? "assisting: session " + r.session_id : r.message, !ok); view.refresh() }) }
                            Button { text: "Decline"; onClicked: falcon.call("assisted_access.decline", {request_id: parseInt(reqId.text)}, view.afterSimple) }
                            Button { text: "Close"; onClicked: falcon.call("assisted_access.close", {request_id: parseInt(reqId.text)}, view.afterSimple) }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }
    }

    function afterTraverse(ok, r) {
        if (!ok) { root.notify(r.message, true); return }
        var s = r.session
        root.notify((r.already_occupying ? "already in" : "entered") + " pc " + s.pc_id + " (session " + s.session_id + ", until " + s.deadline_at.substring(11, 16) + ")"
                    + (s.restricted_view ? " — restricted view" : ""), false)
        view.refresh()
    }
    function afterSimple(ok, r) { root.notify(ok ? falcon.pretty(r) : r.message, !ok); view.refresh() }
}
