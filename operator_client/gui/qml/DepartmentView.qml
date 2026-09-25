import QtQuick
import QtQuick.Layouts
import "."

// A DEPARTMENT: level 2, and the place where you choose whom to enter.
//
// Boards DP05 (at rest) and DP15 (an Admin selected). Four cells in A PINWHEEL -- the two big ones on
// a diagonal, Who governs at the top left and Today at the bottom right -- which no other page has,
// so you know where you are before reading a word. The rail does not change: a department is INSIDE
// Authority, and the crumb and the title are what say how deep you are.
//
// ONE GESTURE. Single click selects: an Admin's foot row fills and the cell swaps to draw them, and
// the crumb does not move. Double click enters, and the crumb grows. Escape comes back out.
//
// WHAT THIS PAGE DELIBERATELY DOES NOT DRAW: the boards group the department's machines under the
// Admin who answers for each. **The system has no such relationship.** `accounts` carries a
// department, never a supervising Admin, and the schema says so on purpose -- report routing resolves
// to "every Admin in the department" rather than one. So the machines are drawn as the department's
// own set, and an Admin is never shown owning a subset of them. If that grouping is wanted it is an
// Engine change first, and a contradiction of the backbone's peer Admins second.
Item {
    id: root

    property int departmentId: 0
    property var tree: []
    property var rollout: ({})
    property var sessions: []
    property var lanes: []
    property var violations: []
    property var deviations: []
    property var reports: []
    property string clock: ""
    // whoever the cell draws is whoever is selected; at rest that is the first in the stable order
    property int selectedAdmin: 0
    signal back()                    // `left` collides with an Item member; do not rename to it
    signal enterAdmin(var admin)

    readonly property var dept: {
        for (var i = 0; i < tree.length; i++)
            if (tree[i].department_id === departmentId) return tree[i]
        return null
    }
    readonly property var admins: dept ? (dept.admins || []) : []
    readonly property var workers: dept ? (dept.workers || []) : []
    readonly property var admin: selectedAdmin < admins.length ? admins[selectedAdmin] : null
    readonly property string deptName: dept ? dept.name : ""

    // the identity colour, from the categorical ramp: it marks the place without touching the four
    // reserved state colours
    readonly property color tint: {
        for (var i = 0; i < tree.length; i++)
            if (tree[i].department_id === departmentId) return Theme.series(i)
        return Theme.accent
    }

    // rollout_health keys its PCs by id; the fleet needs one state per machine of this department
    readonly property var fleet: {
        var behind = {}
        var pcs = (rollout && rollout.pcs) ? rollout.pcs : []
        for (var i = 0; i < pcs.length; i++)
            behind[pcs[i].pc_id] = (pcs[i].failures || 0) >= 3 ? "danger" : "warn"
        var bad = {}
        for (var v = 0; v < violations.length; v++) bad[violations[v].pc_id] = true
        var out = []
        for (var w = 0; w < workers.length; w++) {
            var pc = workers[w]
            if (!pc.pc_id) continue
            out.push({ hostname: pc.hostname || "", pc_id: pc.pc_id,
                       state: bad[pc.pc_id] ? "danger" : (behind[pc.pc_id] || "ok") })
        }
        // a stable order, and the settled one: by hostname, never resorted by state
        out.sort(function (a, b) { return String(a.hostname).localeCompare(String(b.hostname)) })
        return out
    }
    readonly property var deptSessions: {
        var ids = {}
        for (var w = 0; w < workers.length; w++) if (workers[w].pc_id) ids[workers[w].pc_id] = true
        var out = []
        for (var s = 0; s < sessions.length; s++) if (ids[sessions[s].pc_id]) out.push(sessions[s])
        return out
    }
    readonly property var people: falcon.narrate("dept_people",
        { admins: admins, selected: admin, machines: workers.length })
    readonly property var waiting: falcon.narrate("needs_you",
        { tree: dept ? [dept] : [], violations: violations, deviations: deviations, pcs_behind: [] })
    readonly property var fleetSays: falcon.narrate("dept_fleet", { hosts: fleet, biggest: fleet.length })
    readonly property var daySays: falcon.narrate("the_day",
        { sessions: deptSessions, quiet_pcs: quietPcs, pc_count: workers.length })

    readonly property int quietPcs: {
        var seen = {}
        for (var s = 0; s < deptSessions.length; s++) seen[deptSessions[s].pc_id] = true
        var n = 0
        for (var w = 0; w < workers.length; w++) if (workers[w].pc_id && !seen[workers[w].pc_id]) n++
        return n
    }

    function stateWord(a) {
        if (!a) return ""
        if (!a.session) return "Free"
        var via = a.session.occupied_via
        return via === "native" ? "At their workstation"
             : via === "assisted_access" ? "Assisting, by consent" : "Entered"
    }

    Keys.onEscapePressed: root.back()
    focus: true

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 22
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 16

        // --- the crumb, the title, and the department's own colour beside it -----------------
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 48

            Column {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4

                Row {
                    spacing: 6
                    Txt {
                        objectName: "deptCrumbRoot"
                        text: "Authority"
                        color: Qt.rgba(1, 1, 1, 0.45)
                        font.pixelSize: Theme.fBody
                        MouseArea {
                            anchors.fill: parent
                            anchors.margins: -6
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.back()
                        }
                    }
                    Icon { name: "chev"; color: Qt.rgba(1, 1, 1, 0.45); size: 12
                           anchors.verticalCenter: parent.verticalCenter }
                    Txt {
                        objectName: "deptCrumbHere"
                        text: root.deptName
                        color: "#ffffff"
                        font.pixelSize: Theme.fBody
                        font.weight: Font.DemiBold
                    }
                }
                Row {
                    spacing: 10
                    Txt {
                        text: root.deptName
                        color: "#ffffff"
                        font.pixelSize: Theme.fTitle
                        font.weight: Font.Bold
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Rectangle {
                        width: 9; height: 9; radius: 3
                        color: root.tint
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Txt {
                        text: root.admins.length === 0 ? "nobody governs this department"
                              : root.workers.length + " machines, " + root.admins.length
                                + (root.admins.length === 1 ? " Admin" : " Admins")
                        color: root.admins.length === 0 ? Theme.danger : Qt.rgba(1, 1, 1, 0.45)
                        font.pixelSize: Theme.fBody
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
            Txt {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: root.clock
                color: Qt.rgba(1, 1, 1, 0.45)
                font.pixelSize: Theme.fBody
            }
        }

        // --- the pinwheel: the two big cells on a diagonal ------------------------------------
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 1
            spacing: 20

            GridCell {
                objectName: "deptGoverns"
                Layout.preferredWidth: 2
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "Who governs"
                narration: root.people

                // ONE Admin at full width; the others are a line at the foot. Two stations crammed
                // into one cell was rejected outright.
                Column {
                    width: parent.width
                    spacing: 13
                    visible: root.admin !== null

                    Row {
                        width: parent.width
                        spacing: 13
                        Avatar { initials: root.initialsOf(root.admin ? root.admin.name : ""); size: 44 }
                        Column {
                            spacing: 3
                            width: parent.width - 60
                            Txt {
                                text: root.admin ? (root.admin.name || "Admin") : ""
                                color: Theme.ink
                                font.pixelSize: Theme.fSection
                                font.weight: Font.DemiBold
                            }
                            Row {
                                spacing: 7
                                Txt {
                                    text: root.admin ? (root.admin.hostname || "no workstation") : ""
                                    color: Theme.faint
                                    font.pixelSize: Theme.fBody
                                    monospace: true
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Txt {
                                    text: root.stateWord(root.admin)
                                    color: Theme.faint
                                    font.pixelSize: Theme.fBody
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: Theme.line }

                    Txt {
                        width: parent.width
                        text: root.people.sentence || ""
                        color: Theme.ink
                        font.pixelSize: Theme.fRow
                        font.weight: Font.Medium
                        wrapMode: Text.WordWrap
                    }

                    // the others: single click swaps who is drawn, double click enters them
                    Column {
                        width: parent.width
                        spacing: 0
                        visible: root.admins.length > 1

                        Txt { text: "Also here"; color: Theme.faint; font.pixelSize: Theme.fMeta
                              bottomPadding: 6 }

                        Repeater {
                            model: root.admins
                            delegate: Rectangle {
                                required property var modelData
                                required property int index
                                visible: index !== root.selectedAdmin
                                width: parent.width
                                height: visible ? 34 : 0
                                radius: Theme.radiusMd
                                // selection is a filled muted row, never a left-edge accent
                                color: rowArea.containsMouse ? Theme.select : "transparent"

                                Row {
                                    anchors.left: parent.left
                                    anchors.leftMargin: rowArea.containsMouse ? 8 : 0
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 8
                                    Avatar { initials: root.initialsOf(modelData.name || ""); size: 22
                                             anchors.verticalCenter: parent.verticalCenter }
                                    Txt {
                                        text: modelData.name || "Admin"
                                        color: Theme.dim
                                        font.pixelSize: Theme.fBody
                                        font.weight: Font.Medium
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Txt {
                                        text: root.stateWord(modelData).toLowerCase()
                                        color: Theme.faint
                                        font.pixelSize: Theme.fMeta
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }
                                Icon {
                                    anchors.right: parent.right
                                    anchors.rightMargin: rowArea.containsMouse ? 8 : 0
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: "chev"; color: Theme.faint; size: 13
                                }
                                MouseArea {
                                    id: rowArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.selectedAdmin = index          // select
                                    onDoubleClicked: root.enterAdmin(modelData)       // enter
                                }
                            }
                        }
                    }
                }

                // a department with nobody governing it is a result, not an absence
                Txt {
                    width: parent.width
                    visible: root.admin === null
                    text: "Nobody governs this department."
                    color: Theme.danger
                    font.pixelSize: Theme.fRow
                    font.weight: Font.DemiBold
                }
            }

            GridCell {
                objectName: "deptMachines"
                Layout.preferredWidth: 1
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "Its machines"
                narration: root.fleetSays

                FleetGrid {
                    objectName: "deptFleet"
                    width: parent.width
                    hosts: root.fleet
                }
                Legend {
                    width: parent.width
                    items: [ { label: "Confirmed", color: Theme.ok },
                             { label: "Behind", color: Theme.warn },
                             { label: "Out of place", color: Theme.danger } ]
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 1
            spacing: 20

            GridCell {
                objectName: "deptWaiting"
                Layout.preferredWidth: 1
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "Waiting on you"
                narration: root.waiting

                Column {
                    width: parent.width
                    spacing: 14

                    Txt {
                        width: parent.width
                        text: root.waiting.sentence || ""
                        color: Theme.ink
                        font.pixelSize: Theme.fSection
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }
                    Column {
                        width: parent.width
                        spacing: 0
                        Repeater {
                            model: root.waiting.facts || []
                            delegate: Item {
                                required property var modelData
                                width: parent.width
                                height: 33
                                Txt {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.label
                                    color: Theme.dim
                                    font.pixelSize: Theme.fBody
                                }
                                Txt {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.value
                                    color: modelData.tone ? Theme.tone(modelData.tone) : Theme.ink
                                    font.pixelSize: Theme.fBody
                                    font.weight: Font.Medium
                                }
                                Rectangle {
                                    anchors.bottom: parent.bottom
                                    width: parent.width
                                    height: 1
                                    color: Theme.line
                                }
                            }
                        }
                    }
                }
            }

            GridCell {
                objectName: "deptToday"
                Layout.preferredWidth: 2
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "Today"
                narration: root.daySays

                DayTimeline {
                    objectName: "deptDay"
                    width: parent.width
                    height: Math.max(120, parent.height - 30)
                    labelWidth: 96
                    laneGap: 9
                    laneHeight: Math.max(12, Math.min(26, (parent.height - 90)
                                                          / Math.max(1, lanes.length) - laneGap))
                    lanes: root.lanes
                }
            }
        }
    }
}
