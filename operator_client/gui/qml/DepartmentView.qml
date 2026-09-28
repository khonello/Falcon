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
    property var violations: []
    property var deviations: []
    property var reports: []
    property string clock: ""
    // whoever the cell draws is whoever is selected; at rest that is the first in the stable order
    property int selectedAdmin: 0
    // A CHART OPENS INTO ITSELF, not into four more charts (board DP11). An area recomposes; a chart
    // is explained by more of that chart -- which is where the hostnames the cell had to drop at
    // scale come back. "" = the four cells.
    property string maximised: ""
    // AN ADMIN OPENED IN PLACE (DP06): the crumb grows by their name and the lane states what
    // entering costs. Still level 2 -- nothing is held until the Engine says yes.
    property bool entering: false
    property var tasks: []
    property var flows: []
    // the session this Super User holds, if it is on an Admin of THIS department (DP09)
    property var heldAdmin: null
    property double nowMs: Date.now()
    readonly property bool heldHere: heldAdmin !== null && heldAdmin.department_id === departmentId
    signal back()                    // `left` collides with an Item member; do not rename to it
    signal goInside()
    signal leaveSession()
    signal openRecord()
    onDepartmentIdChanged: { entering = false; maximised = "" }

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
        // `updates.rollout_health` returns `pcs_behind`, not `pcs`, and a row says `escalated` --
        // reading the wrong names drew every machine green while the page named a violation beside it.
        var behind = {}
        var pcs = (rollout && rollout.pcs_behind) ? rollout.pcs_behind : []
        for (var i = 0; i < pcs.length; i++)
            behind[pcs[i].pc_id] = pcs[i].escalated ? "danger" : "warn"
        // A violation row is `v.*` from resource_violations joined to the PC, so it carries
        // `found_on_pc_id` AND `hostname` -- match on either, because a machine named in "Waiting on
        // you" and drawn green beside it is the page contradicting itself.
        var bad = {}
        for (var v = 0; v < violations.length; v++) {
            var vi = violations[v]
            if (vi.found_on_pc_id || vi.pc_id) bad[vi.found_on_pc_id || vi.pc_id] = true
            if (vi.hostname) bad["host:" + vi.hostname] = true
        }
        var out = []
        for (var w = 0; w < workers.length; w++) {
            var pc = workers[w]
            if (!pc.pc_id) continue
            var wrong = bad[pc.pc_id] || bad["host:" + (pc.hostname || "")]
            out.push({ hostname: pc.hostname || "", pc_id: pc.pc_id,
                       state: wrong ? "danger" : (behind[pc.pc_id] || "ok") })
        }
        // a stable order, and the settled one: by hostname, never resorted by state
        out.sort(function (a, b) { return String(a.hostname).localeCompare(String(b.hostname)) })
        return out
    }
    // each machine as the screen mark reads it -- the shared rule, so this page and the Admin's home agree
    readonly property var machines: Fleet.machines(workers, rollout, violations)
    // what waits on you here, as cards: files out of place, machines behind, and nobody governing
    readonly property var waitItems: {
        var out = []
        if (admins.length === 0)
            out.push({ icon: "dept", tone: "danger", title: "Nobody governs " + deptName, line: "assign an Admin", word: "" })
        for (var v = 0; v < violations.length; v++) {
            var vi = violations[v]
            var ours = root.workers.some(function (w) { return w.pc_id === vi.found_on_pc_id || w.hostname === vi.hostname })
            if (!ours) continue
            out.push({ icon: "shield", tone: "danger", title: (vi.filename || "A file") + " is out of place",
                       line: "on " + (vi.hostname || ""), word: "new" })
        }
        var behindHere = machines.filter(function (m) { return m.line === "a version behind" || m.line === "update past the limit" })
        if (behindHere.length > 0)
            out.push({ icon: "shield", tone: "warn", title: behindHere.length === 1 ? behindHere[0].host + " is a version behind"
                                                                                  : behindHere.length + " machines are a version behind",
                       line: "updates retry by themselves", word: "" })
        return out
    }

    readonly property var deptSessions: {
        var ids = {}
        for (var w = 0; w < workers.length; w++) if (workers[w].pc_id) ids[workers[w].pc_id] = true
        var out = []
        for (var s = 0; s < sessions.length; s++) if (ids[sessions[s].pc_id]) out.push(sessions[s])
        return out
    }
    // its own lanes: a lane is a PC and a block is a session, and the arithmetic is the Day
    // singleton's, so this page does not borrow the Overview's
    readonly property var lanes: Day.lanesFor(sessions, workers)
    readonly property var people: falcon.narrate("dept_people",
        { admins: admins, selected: admin, machines: workers.length })
    readonly property var waiting: falcon.narrate("needs_you",
        { tree: dept ? [dept] : [], violations: violations, deviations: deviations, pcs_behind: [] })
    // A count is drawn against the largest, not against itself: "7 of 7" compared this department
    // with this department and said nothing. `biggest` is the largest department's machine count.
    readonly property int biggestDept: {
        var n = 0
        for (var i = 0; i < tree.length; i++) n = Math.max(n, (tree[i].workers || []).length)
        return n
    }
    readonly property var fleetSays: falcon.narrate("dept_fleet", { hosts: fleet, biggest: biggestDept })
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

    // --- one chart, full size, and nothing else on the page --------------------------------
    Item {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 22
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        visible: root.maximised === "machines"

        Column {
            id: maxHead
            anchors.top: parent.top
            anchors.left: parent.left
            spacing: 4

            Row {
                spacing: 6
                Txt {
                    text: "Authority"
                    color: Qt.rgba(1, 1, 1, 0.45)
                    font.pixelSize: Theme.fBody
                }
                Icon { name: "chev"; color: Qt.rgba(1, 1, 1, 0.45); size: 12
                       anchors.verticalCenter: parent.verticalCenter }
                Txt {
                    text: root.deptName
                    color: Qt.rgba(1, 1, 1, 0.45)
                    font.pixelSize: Theme.fBody
                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -6
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.maximised = ""
                    }
                }
                Icon { name: "chev"; color: Qt.rgba(1, 1, 1, 0.45); size: 12
                       anchors.verticalCenter: parent.verticalCenter }
                Txt {
                    objectName: "deptMaxCrumb"
                    text: "Its machines"
                    color: "#ffffff"
                    font.pixelSize: Theme.fBody
                    font.weight: Font.DemiBold
                }
            }
            Txt {
                text: root.deptName
                color: "#ffffff"
                font.pixelSize: Theme.fTitle
                font.weight: Font.Bold
            }
        }
        Txt {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: 12
            text: "Esc to go back"
            color: Qt.rgba(1, 1, 1, 0.45)
            font.pixelSize: Theme.fBody
        }

        GridCell {
            objectName: "deptMachinesMax"
            anchors.top: maxHead.bottom
            anchors.topMargin: 16
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            topAlign: true
            title: "Its machines"
            narration: root.fleetSays

            Row {
                width: parent.width
                spacing: 36

                // the marks go back up and the hostnames return -- the cell dropped them to fit,
                // and this is where they come back
                // every machine at full size, paging down by rows -- never shrunk (PATTERNS 3a)
                MachineGrid {
                    objectName: "deptFleetMax"
                    width: parent.width - 396
                    height: Math.max(200, root.height - 170)
                    machines: root.machines
                    filterLabel: "Needs you"
                }

                ReadingBody {
                    width: 360
                    narration: root.fleetSays
                    maxFacts: 6
                }
            }
        }
    }

    Keys.onEscapePressed: root.entering ? root.entering = false
                          : root.maximised !== "" ? root.maximised = "" : root.back()

    EnteringAdmin {
        objectName: "enteringAdmin"
        anchors.fill: parent
        visible: root.entering
        admin: root.admin
        deptName: root.deptName
        tint: root.tint
        clock: root.clock
        lanes: root.lanes
        people: root.people
        tasks: root.tasks
        flows: root.flows
        machines: root.workers.length
        heldAdmin: root.heldAdmin
        nowMs: root.nowMs
        onBack: root.entering = false
        onGoInside: root.goInside()
        onLeaveSession: root.leaveSession()
        onOpenRecord: root.openRecord()
    }
    focus: true

    ColumnLayout {
        anchors.fill: parent
        visible: root.maximised === "" && !root.entering
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
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 16
                GBtn { objectName: "registerMachine"; text: "Register a machine"; iconName: "plus"; small: true
                       anchors.verticalCenter: parent.verticalCenter
                       onClicked: shell.registerMachine(root.departmentId, root.deptName, "worker") }
                Txt {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.clock
                    color: Qt.rgba(1, 1, 1, 0.45)
                    font.pixelSize: Theme.fBody
                }
            }
        }

        // --- DP18: its machines wide, what waits on you beside them ------------------------------
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 1
            spacing: 20

            GridCell {
                objectName: "deptMachines"
                Layout.preferredWidth: 2
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Its machines"
                narration: root.fleetSays
                openable: root.machines.length > 0
                openOnDoubleClick: true
                onOpened: root.maximised = "machines"

                // full size, paged sideways; a hidden machine that needs you is named at the edge
                PagedRow {
                    objectName: "deptFleet"
                    width: parent.width
                    height: 124
                    itemWidth: 118
                    model: root.machines
                    attention: function (m) { return m.status === "danger" || m.status === "warn" ? m.host : "" }
                    delegate: MachineMark {
                        property var modelData: ({})
                        size: 70
                        label: modelData.label || ""
                        status: modelData.status || "ok"
                        name: modelData.name || ""
                        line: modelData.line || ""
                        lineTone: modelData.lineTone || ""
                        onDoubleClicked: if (modelData.pc_id) shell.enterPc(modelData.pc_id)
                    }
                }
                Txt {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    text: "Quiet means fine. A machine in colour says why beneath it."
                    color: Theme.faint
                    font.pixelSize: Theme.fMeta
                }
            }

            GridCell {
                objectName: "deptWaiting"
                Layout.preferredWidth: 1
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "Waiting on you"
                narration: root.waiting

                PagedColumn {
                    objectName: "deptWaitingList"
                    width: parent.width
                    height: Math.max(120, parent.height > 0 ? parent.height : 200)
                    itemHeight: 58
                    model: root.waitItems
                    delegate: InfoCard {
                        iconName: modelData ? modelData.icon : ""
                        iconTone: modelData ? modelData.tone : "accent"
                        title: modelData ? modelData.title : ""
                        line: modelData ? modelData.line : ""
                        stateWord: modelData ? modelData.word : ""
                        stateTone: modelData ? modelData.tone : ""
                    }
                }
                Txt {
                    visible: root.waitItems.length === 0
                    text: "Nothing waits on you here."
                    color: Theme.faint
                    font.pixelSize: Theme.fBody
                }
            }
        }

        // --- who governs, and the day ------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 1
            spacing: 20

            GridCell {
                objectName: "deptGoverns"
                Layout.preferredWidth: 1
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "Who governs"
                narration: root.people

                // each Admin a card: single click selects, double click opens them (the crumb grows)
                Column {
                    width: parent.width
                    spacing: 9
                    Repeater {
                        model: root.admins
                        delegate: InfoCard {
                            required property var modelData
                            required property int index
                            width: parent.width
                            initials: Theme.initials(modelData.name || "")
                            title: modelData.name || "Admin"
                            line: root.stateWord(modelData)
                                  + (modelData.hostname ? " · " + modelData.hostname : "")
                            lineTone: modelData.session && modelData.session.occupied_via === "assisted_access" ? "accent" : ""
                            selected: index === root.selectedAdmin
                            stateWord: index === root.selectedAdmin ? "selected" : ""
                            onClicked: root.selectedAdmin = index
                            onDoubleClicked: { root.selectedAdmin = index; root.entering = true }
                        }
                    }
                    Txt {
                        width: parent.width
                        visible: root.admins.length > 0
                        text: root.people.sentence || ""
                        color: Theme.faint
                        font.pixelSize: Theme.fMeta
                        wrapMode: Text.WordWrap
                    }
                    // the held session rides with the Admins, carrying its clock and the way back in
                    HeldCard {
                        objectName: "heldCard"
                        visible: root.heldHere
                        width: parent.width
                        admin: root.heldAdmin
                        session: falcon.session
                        nowMs: root.nowMs
                        onGoInside: root.goInside()
                        onLeave: root.leaveSession()
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
                    TBtn {
                        objectName: "giveAdmin"
                        visible: root.admin === null && falcon.role === "super_user"
                        text: "Give it an Admin"; iconName: "plus"; small: true
                        onClicked: shell.registerMachine(root.departmentId, root.deptName, "admin")
                    }
                }
            }

            GridCell {
                id: todayCell
                objectName: "deptToday"
                Layout.preferredWidth: 2
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "Today"
                narration: root.daySays

                // it draws to its own implicit height (lanes + axis); forcing a height would put the
                // legend on top of the last lane, which is what it used to do
                DayTimeline {
                    objectName: "deptDay"
                    width: parent.width
                    labelWidth: 96
                    laneGap: 9
                    laneHeight: Math.max(12, Math.min(26, (todayCell.room - 76)
                                                          / Math.max(1, lanes.length) - laneGap))
                    lanes: root.lanes
                }
                // a timeline always carries its key (PATTERNS 0): what the colours are, who never signed in
                Legend {
                    items: [{ label: "At the PC", color: Theme.line2, round: false },
                            { label: "An Admin entered", color: Theme.warn, round: false },
                            { label: "You entered", color: Theme.danger, round: false }]
                    note: root.quietPcs === 0 ? ""
                          : root.quietPcs + (root.quietPcs === 1 ? " machine was never signed in" : " machines were never signed in")
                }
            }
        }
    }
}
