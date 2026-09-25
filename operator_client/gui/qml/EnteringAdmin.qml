import QtQuick
import QtQuick.Layouts
import "."

// AN ADMIN, OPENED IN PLACE -- still level 2 (boards DP06, DP07, DP08).
//
// Double-clicking an Admin on the department opens them here, and the crumb grows. Nothing is held
// yet: no lid, no clock. The lane on the left states the cost BEFORE the act, and it is the lane the
// answer lands in -- no modal, no new page -- and then the lane that carries the session. Only then is
// anything held, and going in (level 3) is one more double click, on the lane itself.
//
// Four cells, the lane narrow and tall: the subject here is a decision, so the reading leads.
Item {
    id: root

    property var admin: null
    property string deptName: ""
    property color tint: Theme.accent
    property string clock: ""
    property var lanes: []
    property var people: ({})
    property var tasks: []
    property var flows: []
    property int machines: 0
    property var heldAdmin: null
    property double nowMs: Date.now()
    signal back()
    signal goInside()
    signal leaveSession()
    signal openRecord()

    // what the last ask said, when it did not simply say yes; null while nothing has been asked
    property var answer: null
    property bool asking: false
    onAdminChanged: { answer = null; asking = false }

    readonly property bool held: heldAdmin !== null && admin !== null && heldAdmin.account_id === admin.account_id
    readonly property string name: admin ? (admin.name || "Admin") : ""
    readonly property var lane: held
        ? falcon.narrate("held", { name: name, hostname: admin.hostname,
                                   entered_at: falcon.session.entered_at, deadline_at: falcon.session.deadline_at })
        : answer !== null
            ? falcon.narrate("enter_answer", { kind: answer.kind, name: name, hostname: admin ? admin.hostname : "",
                                               holder: answer.holder || "", message: answer.message || "" })
            : falcon.narrate("enter_cost", { name: name, hostname: admin ? admin.hostname : "",
                                             session: admin ? admin.session : null })
    readonly property var station: falcon.narrate("workstation", {
        hostname: admin ? admin.hostname : "", held_by_me: held,
        session: held ? falcon.session : (admin ? admin.session : null) })
    // what is theirs: the tasks they assigned and the flows they made -- never machines
    readonly property int theirTasks: tasks.filter(function (t) {
        return admin && t.assigner_account_id === admin.account_id }).length
    readonly property int theirFlows: flows.filter(function (f) {
        return admin && f.created_by_account_id === admin.account_id && f.status !== "inactive" }).length

    // Ask the Engine. The reply decides which answer the lane shows; the Engine decides, the page says.
    function ask(force) {
        if (!admin || !admin.pc_id || asking) return
        asking = true
        falcon.call("hierarchy.traverse", { pc_id: admin.pc_id, force: !!force }, function (ok, r) {
            root.asking = false
            if (ok) { root.answer = null; return }       // held: `falcon.session` now names it
            var msg = r.message || ""
            if (r.code === "conflict" && msg.indexOf("force=true") >= 0)
                root.answer = { kind: "occupied" }
            else if (r.code === "conflict" && msg.indexOf("un-evictable") >= 0)
                root.answer = { kind: "super_user",
                                holder: root.admin.session ? root.admin.session.occupant_name : "" }
            else
                root.answer = { kind: "refused", message: msg }
        })
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 22
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 16

        // --- the crumb has grown by one: that is the sign you went somewhere --------------------
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 48

            Column {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4
                Row {
                    spacing: 6
                    Txt { text: "Authority"; color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody }
                    Icon { name: "chev"; color: Qt.rgba(1, 1, 1, 0.45); size: 12
                           anchors.verticalCenter: parent.verticalCenter }
                    Txt {
                        text: root.deptName
                        color: Qt.rgba(1, 1, 1, 0.45)
                        font.pixelSize: Theme.fBody
                        MouseArea { anchors.fill: parent; anchors.margins: -6
                                    cursorShape: Qt.PointingHandCursor; onClicked: root.back() }
                    }
                    Icon { name: "chev"; color: Qt.rgba(1, 1, 1, 0.45); size: 12
                           anchors.verticalCenter: parent.verticalCenter }
                    Txt {
                        objectName: "enterCrumbHere"
                        text: root.name
                        color: "#ffffff"
                        font.pixelSize: Theme.fBody
                        font.weight: Font.DemiBold
                    }
                }
                Row {
                    spacing: 10
                    Txt { text: root.deptName; color: "#ffffff"; font.pixelSize: Theme.fTitle; font.weight: Font.Bold
                          anchors.verticalCenter: parent.verticalCenter }
                    Rectangle { width: 9; height: 9; radius: 3; color: root.tint
                                anchors.verticalCenter: parent.verticalCenter }
                    Txt {
                        text: root.held ? "you are holding one workstation" : "choosing whether to enter"
                        color: root.held ? Theme.danger : Theme.accent
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

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            // --- the lane: the cost, then the answer, then the session ---------------------------
            GridCell {
                objectName: "enterLane"
                Layout.preferredWidth: 420
                Layout.fillHeight: true
                topAlign: true
                title: (root.held ? "Holding " : "Entering ") + root.name
                narration: root.lane
                // held, the lane IS the session's container: double click goes in
                openable: root.held
                openOnDoubleClick: true
                onOpened: root.goInside()

                Column {
                    width: parent.width
                    spacing: 14

                    // the clock, while held
                    Row {
                        visible: root.held
                        spacing: 10
                        Ring {
                            width: 22; height: 22
                            color: Theme.danger
                            fraction: Day.leftFraction(falcon.session.entered_at, falcon.session.deadline_at, root.nowMs)
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Txt {
                            text: Day.leftText(falcon.session.deadline_at, root.nowMs) + " left"
                            color: Theme.danger
                            monospace: true
                            font.pixelSize: Theme.fSection
                            font.weight: Font.Bold
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    // their screen: nothing carries the picture yet (the screenshot Action returns a
                    // path on the worker), so the frame stays and says so -- never a fake preview
                    Rectangle {
                        visible: root.held
                        width: parent.width
                        height: width * 0.5
                        radius: Theme.radiusMd
                        color: Qt.rgba(1, 1, 1, 0.03)
                        border.color: Theme.line
                        Column {
                            anchors.centerIn: parent
                            spacing: 6
                            Icon { name: "monitor"; color: Theme.faint; size: 22
                                   anchors.horizontalCenter: parent.horizontalCenter }
                            Txt { text: "Their screen is not carried yet"; color: Theme.faint
                                  font.pixelSize: Theme.fMeta; anchors.horizontalCenter: parent.horizontalCenter }
                        }
                    }

                    ReadingBody {
                        width: parent.width
                        narration: root.lane
                        maxFacts: 5
                        showAction: false
                    }

                    // one forcing act at most, and it names its cost first; a refusal names somewhere
                    // else to go
                    Row {
                        spacing: 10
                        TBtn {
                            objectName: "enterAct"
                            visible: (root.lane.action || "") !== "" && (root.lane.action || "") !== "Close"
                            enabled: !root.asking
                            text: root.asking ? "Asking…" : (root.lane.action || "")
                            iconName: root.held ? "fwd" : root.answer && root.answer.kind === "super_user" ? "eye" : "lock"
                            tone: root.answer && root.answer.kind === "occupied" ? "danger" : "accent"
                            onClicked: root.held ? root.goInside()
                                       : root.answer === null ? root.ask(false)
                                       : root.answer.kind === "occupied" ? root.ask(true)
                                       : root.openRecord()
                        }
                        GBtn {
                            objectName: "enterSecond"
                            visible: root.held || root.answer !== null
                            text: root.held ? "Leave" : root.answer && root.answer.kind === "refused" ? "Close" : "Cancel"
                            iconName: root.held ? "back" : ""
                            onClicked: root.held ? root.leaveSession() : root.answer = null
                        }
                    }
                    Txt {
                        visible: root.held
                        text: "Double-click this lane to go in"
                        color: Theme.faint
                        font.pixelSize: Theme.fMeta
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 20

                // --- the Admin, and what is theirs -------------------------------------------------
                GridCell {
                    objectName: "enterAdmin"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    topAlign: true
                    title: root.name
                    narration: ({ brief: root.held ? "blocked out of their own machine" : "chosen",
                                  tone: root.held ? "danger" : "accent", state: "ok" })

                    Column {
                        width: parent.width
                        spacing: 16
                        Row {
                            spacing: 13
                            Avatar { initials: Theme.initials(root.name); size: 44 }
                            Column {
                                spacing: 3
                                anchors.verticalCenter: parent.verticalCenter
                                Txt { text: root.name; color: Theme.ink; font.pixelSize: Theme.fSection
                                      font.weight: Font.DemiBold }
                                Txt { text: root.admin ? (root.admin.hostname || "no workstation") : ""
                                      color: Theme.faint; monospace: true; font.pixelSize: Theme.fBody }
                            }
                        }
                        Rectangle { width: parent.width; height: 1; color: Theme.line }
                        Row {
                            spacing: 56
                            Repeater {
                                model: [ { n: root.theirTasks, label: "tasks", sub: "they assigned" },
                                         { n: root.theirFlows, label: "flows", sub: "they made" },
                                         { n: root.machines, label: "machines", sub: "in the department" } ]
                                delegate: Column {
                                    required property var modelData
                                    spacing: 2
                                    Txt { text: String(modelData.n); color: Theme.ink; font.pixelSize: 34
                                          font.weight: Font.Bold }
                                    Txt { text: modelData.label; color: Theme.dim; font.pixelSize: Theme.fBody }
                                    Txt { text: modelData.sub; color: Theme.faint; font.pixelSize: Theme.fMeta }
                                }
                            }
                        }
                        Txt {
                            width: parent.width
                            text: root.people.sentence || ""
                            color: Theme.ink
                            font.pixelSize: Theme.fRow
                            font.weight: Font.Medium
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 20

                    // --- their workstation: the one machine entering takes -------------------------
                    GridCell {
                        objectName: "enterStation"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.fillHeight: true
                        topAlign: true
                        title: "Their workstation"
                        narration: root.station

                        Column {
                            width: parent.width
                            spacing: 14
                            Rectangle {
                                width: 46; height: 46; radius: Theme.radiusMd
                                color: root.held ? Theme.dangerSoft : Theme.okSoft
                                Txt {
                                    anchors.centerIn: parent
                                    text: root.admin ? String(root.admin.hostname || "").slice(-2) : ""
                                    color: root.held ? Theme.danger : Theme.ok
                                    monospace: true
                                    font.pixelSize: Theme.fBody
                                    font.weight: Font.Bold
                                }
                            }
                            ReadingBody { width: parent.width; narration: root.station; maxFacts: 3 }
                        }
                    }

                    // --- the day here ----------------------------------------------------------------
                    GridCell {
                        objectName: "enterDay"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.fillHeight: true
                        topAlign: true
                        title: "The day here"
                        narration: ({ brief: root.held ? "you are on it now" : "", tone: "danger", state: "ok" })

                        DayTimeline {
                            width: parent.width
                            height: Math.max(100, parent.height - 20)
                            labelWidth: 80
                            laneGap: 8
                            laneHeight: Math.max(10, Math.min(20, (parent.height - 70)
                                                                  / Math.max(1, root.lanes.length) - laneGap))
                            lanes: root.lanes
                        }
                    }
                }
            }
        }
    }
}
