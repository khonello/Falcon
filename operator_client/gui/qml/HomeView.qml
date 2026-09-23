import QtQuick
import "."

// Hierarchy, for whichever role is connected.
//
//   Admin       -- the department: its PCs as a card strip, then what needs you.
//   Super User  -- everything: the departments, then what waits on your authority.
//
// Everything on screen comes from hierarchy.tree; the detail card follows the selection and nothing
// else, so it never jumps to what just arrived.
Item {
    id: root

    property bool isSuper: falcon.role === "super_user"
    property var tree: []
    property var selected: null            // {account_id, name, pc_id, hostname, role, session, ...}
    property int page: 0
    property int strip: 0

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            root.tree = r.departments
            if (root.selected) root.selected = root.find(root.selected.account_id)
        })
    }
    function find(accountId) {
        for (var i = 0; i < tree.length; i++) {
            var d = tree[i]
            var all = d.admins.concat(d.workers)
            for (var j = 0; j < all.length; j++)
                if (all[j].account_id === accountId) {
                    var o = {}
                    for (var k in all[j]) o[k] = all[j][k]
                    o.department_id = d.department_id
                    o.department_name = d.name
                    return o
                }
        }
        return null
    }
    function initials(name) {
        if (!name) return "?"
        var parts = String(name).replace(".", " ").split(" ").filter(function (p) { return p.length > 0 })
        return (parts.length > 1 ? parts[0][0] + parts[1][0] : String(name).substring(0, 2)).toUpperCase()
    }
    function stateOf(account) { return Theme.stateOf(account ? account.session : null) }

    readonly property var department: tree.length > 0 ? tree[0] : null
    readonly property var workers: department ? department.workers : []
    readonly property var admins: department ? department.admins : []
    readonly property int pcCount: tree.reduce(function (n, d) { return n + d.workers.length }, 0)
    readonly property int adminCount: tree.reduce(function (n, d) { return n + d.admins.length }, 0)

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.tree = []; root.selected = null }
        function onPushReceived(type, p) {
            if (type.indexOf("session.") === 0 || type.indexOf("assisted_access.") === 0 || type === "hierarchy.changed")
                root.refresh()
        }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    // =========================================================================================
    Sidebar {
        id: side
        width: Theme.sideWidth
        height: parent.height
        title: root.isSuper ? "Everything" : (root.department ? root.department.name : "Department")

        Item { width: 1; height: 4 }

        SbSection { title: "Admins"; count: String(root.adminCount) }
        Repeater {
            model: root.admins
            delegate: SbRow {
                required property var modelData
                initials: root.initials(modelData.name)
                name: modelData.name
                sub: modelData.hostname === undefined ? "" : modelData.hostname
                sessionState: Theme.stateOf(modelData.session)
                selected: root.selected && root.selected.account_id === modelData.account_id
                onClicked: root.selected = root.find(modelData.account_id)
            }
        }

        SbSection { title: root.isSuper ? "Client PCs, in this department" : "Client PCs"; count: String(root.workers.length) }
        Repeater {
            model: root.workers
            delegate: SbRow {
                required property var modelData
                initials: root.initials(modelData.name)
                name: modelData.name
                sub: modelData.hostname === undefined ? "" : modelData.hostname
                sessionState: Theme.stateOf(modelData.session)
                selected: root.selected && root.selected.account_id === modelData.account_id
                onClicked: root.selected = root.find(modelData.account_id)
            }
        }
    }

    // =========================================================================================
    Body {
        id: body
        anchors.left: side.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom

        crumbs: root.isSuper ? ["Everything"] : [root.department ? root.department.name : "Department"]
        glyph: root.isSuper ? "shield" : "dept"
        title: root.isSuper ? "Everything" : (root.department ? root.department.name : "Department")
        sub: root.isSuper
             ? (root.tree.length + " departments, " + root.adminCount + " Admins, " + root.pcCount + " Client PCs")
             : (root.workers.length + " PCs, " + root.adminCount + " Admins")
        pills: root.isSuper
               ? [{ label: "Waiting on you", count: "" }, { label: "Watching", count: "" }, { label: "Trail", count: "" }]
               : [{ label: "Needs you", count: String(falcon.indicators.length) }, { label: "Quiet", count: "" }, { label: "Reports", count: "" }]
        pill: root.page
        onPillPicked: function (i) { root.page = i }

        actions: Component {
            GBtn {
                text: root.isSuper ? "New department" : "Department action"
                iconName: root.isSuper ? "plus" : "automation"
                small: true
            }
        }

        // the card strip: the entities of this level, across the whole body. It pages; the dots say so.
        strip: Column {
            width: parent ? parent.width : 0
            spacing: 10

        Item {
            width: parent.width
            height: 104
            clip: true

            Row {
                id: strip
                spacing: 10
                anchors.top: parent.top
                Repeater {
                    model: root.isSuper ? root.tree : root.workers
                    delegate: Rectangle {
                        required property var modelData
                        readonly property bool isDept: root.isSuper
                        readonly property bool sel: !isDept && root.selected && root.selected.account_id === modelData.account_id

                        width: 206
                        height: 104
                        radius: Theme.radiusLg
                        color: Theme.ground

                        Rectangle {
                            anchors.fill: parent
                            radius: parent.radius
                            color: "transparent"
                            border.width: sel ? 1 : 0
                            border.color: Theme.selectLine
                        }

                        Column {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8

                            Row {
                                spacing: 10
                                width: parent.width
                                Avatar {
                                    initials: root.initials(modelData.name)
                                    size: 34
                                    visible: !isDept
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Rectangle {
                                    width: 32
                                    height: 32
                                    radius: Theme.radiusMd
                                    color: Theme.pane
                                    visible: isDept
                                    anchors.verticalCenter: parent.verticalCenter
                                    Icon { anchors.centerIn: parent; name: "dept"; color: Theme.dim; size: 17 }
                                }
                                Column {
                                    spacing: 0
                                    width: parent.width - 46
                                    anchors.verticalCenter: parent.verticalCenter
                                    Txt {
                                        width: parent.width
                                        text: modelData.name
                                        font.pixelSize: Theme.fRow
                                        font.weight: Font.DemiBold
                                    }
                                    Txt {
                                        width: parent.width
                                        text: isDept
                                              ? (modelData.admins.length + " Admins, " + modelData.workers.length + " PCs")
                                              : (modelData.hostname === undefined ? "" : modelData.hostname)
                                        color: Theme.faint
                                        font.pixelSize: Theme.fSmall
                                        monospace: !isDept
                                    }
                                }
                            }
                            Item { width: 1; height: 6 }
                            Txt {
                                text: isDept
                                      ? (modelData.admins.length === 0 ? "No Admin" : "")
                                      : Theme.sessionWord(Theme.stateOf(modelData.session))
                                color: isDept && modelData.admins.length === 0 ? Theme.danger : Theme.dim
                                font.pixelSize: Theme.fMeta
                                font.weight: isDept && modelData.admins.length === 0 ? Font.Medium : Font.Normal
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: if (!isDept) root.selected = root.find(modelData.account_id)
                        }
                    }
                }
            }
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 6
            Repeater {
                model: Math.max(1, Math.ceil((root.isSuper ? root.tree.length : root.workers.length) / 5))
                delegate: Rectangle {
                    required property int index
                    width: 6
                    height: 6
                    radius: 3
                    color: index === root.strip ? Theme.ink : Theme.line2
                }
            }
        }
        }

        // what needs you: the indicators, which stay lit until addressed

        Repeater {
            model: falcon.indicators
            delegate: CardRow {
                required property var modelData
                width: Theme.bodyWidth
                icon: modelData.kind === "unaddressed_ping" ? "ping"
                      : modelData.kind === "deadline_reached" ? "clock"
                      : modelData.kind === "flow_failure" ? "flows"
                      : modelData.kind === "violation" ? "shield"
                      : modelData.kind === "task_completed" ? "check" : "bell"
                iconColor: modelData.kind === "task_completed" ? Theme.ok
                           : modelData.kind === "unaddressed_ping" ? Theme.warn : Theme.danger
                title: modelData.text
                sub: modelData.key
            }
        }
        CardRow {
            width: Theme.bodyWidth
            visible: falcon.indicators.length === 0
            icon: "check"
            iconColor: Theme.ok
            title: "Nothing needs you"
            sub: falcon.isConnected ? "Everything in this department is quiet" : "Not connected"
            chevron: false
        }

        // ---------------------------------------------------------------- the lane
        lane: DetailCard {
            id: card
            empty: root.selected === null
            emptyIcon: "monitor"
            emptyLine: "Nothing selected"
            emptyHint: "Pick a PC or a row and it opens here."
            leadInitials: root.selected ? root.initials(root.selected.name) : ""
            title: root.selected ? root.selected.name : ""
            sub: root.selected ? (root.selected.hostname === undefined ? "" : root.selected.hostname) : ""

            // the session is a control, not a row
            Rectangle {
                width: parent ? parent.width : 0
                height: sessionCol.implicitHeight + 24
                radius: Theme.radiusMd
                color: Theme.ground
                visible: root.selected !== null

                Column {
                    id: sessionCol
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Row {
                        width: parent.width
                        spacing: 8
                        Icon {
                            name: Theme.sessionIcon(root.stateOf(root.selected))
                            color: Theme.sessionColor(root.stateOf(root.selected))
                            size: 16
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Txt {
                            text: Theme.sessionWord(root.stateOf(root.selected))
                            font.pixelSize: Theme.fBody
                            font.weight: Font.DemiBold
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    Row {
                        spacing: 8
                        TBtn {
                            text: "Enter"
                            iconName: "lock"
                            tone: "accent"
                            onClicked: falcon.call("hierarchy.traverse", { target_account_id: root.selected.account_id },
                                                   function (ok, r) { shell.notify(ok ? "entered " + root.selected.name : r.message, !ok) })
                        }
                        GBtn {
                            text: "End session"
                            onClicked: falcon.call("hierarchy.end_session", { pc_id: root.selected.pc_id },
                                                   function (ok, r) { shell.notify(ok ? "session ended" : r.message, !ok) })
                        }
                    }
                    Txt {
                        width: parent.width
                        text: "Entering blocks " + (root.selected ? root.selected.name : "") + " until you leave. 30 min."
                        color: Theme.faint
                        font.pixelSize: Theme.fMeta
                        wrapMode: Text.WordWrap
                        elide: Text.ElideNone
                    }
                }
            }

            KeyRow { label: "Account"; value: root.selected ? String(root.selected.account_id) : ""; monospace: true; visible: root.selected !== null }
            KeyRow { label: "PC"; value: root.selected ? String(root.selected.pc_id) : ""; monospace: true; visible: root.selected !== null }
            KeyRow {
                label: "Department"
                value: root.selected ? String(root.selected.department_name) : ""
                visible: root.selected !== null
            }
        }
    }
}
