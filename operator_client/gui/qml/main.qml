import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "."

// The Operator Client shell.
//
// One gradient frame that never changes, whatever your session state. On it: the rail, the minimal
// top bar, and the sheet -- sidebar, body, lane. State is said by the floating pill under the top
// bar, by the status line, and by the session control in the detail card; never by the frame.
ApplicationWindow {
    id: shell

    Material.theme: Material.Dark
    Material.background: Theme.pane
    Material.accent: Theme.accent
    Material.foreground: Theme.ink
    Material.roundedScale: Material.SmallScale

    width: 1440
    height: 900
    visible: true
    color: "transparent"
    title: "Falcon" + (falcon.isConnected ? "  —  " + Theme.roleLabel(falcon.role) : "")
    flags: Qt.Window | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint | Qt.CustomizeWindowHint

    property int view: 0
    // which surface is up is a name, not a number: the two roles have different rails, and the
    // rail owns the list. Views switch each other with shell.show("hierarchy").
    readonly property string viewKey: rail.currentKey
    // a page opened from another without a rail entry of its own (Resources, from the Admin's home)
    property string subPage: ""
    onViewKeyChanged: subPage = ""
    // The Super User rail is the five areas; the Admin rail is still the old list until level 3 is
    // opened, so the two spell the same place differently. These two names are what the views test,
    // rather than a literal key, so neither rail has to know about the other.
    readonly property bool onMustSee: shell.viewKey === "mustsee"
    readonly property bool onAuthority: shell.viewKey === "authority" || shell.viewKey === "hierarchy"
    // A department is a place INSIDE Authority, not a rail entry: entering one changes the crumb and
    // the page, never the rail. 0 = the area itself.
    property int departmentId: 0
    readonly property bool inDepartment: !insideNow && onAuthority && departmentId !== 0
    // drawn on the gradient, with no sheet behind it. Inside an Admin never is: their interface is
    // shown exactly as they see it, grey sheet and all.
    // The pages rebuilt in the Overview's language sit on the gradient. The Admin's pages join as they are rebuilt; a
    // Super User inside an Admin sees exactly the Admin's page, so the same list holds there.
    readonly property var framedAdminKeys: ["hierarchy", "tasks", "flows", "automation", "actions", "assistance", "reports"]
    readonly property bool onFrame: insideNow ? framedAdminKeys.indexOf(viewKey) >= 0
                                    : (onMustSee || inDepartment || viewKey === "rollout" || framedAdminKeys.indexOf(viewKey) >= 0)

    // LEVEL 3 -- INSIDE AN ADMIN. Holding a session and looking through it are different things:
    // `hierarchy.traverse` makes the session and the department page draws it as a container;
    // double-clicking that container is what sets `inside`. Escape clears it and the session runs on.
    // Inside, the window IS the Admin's interface -- their seven-entry rail, their home page, their
    // grey sheet -- and the red lid is the only thing that says it is not your own.
    property bool inside: false
    // whose workstation the held session is on, found in the tree the Overview already has: derived,
    // so a session that was already running when the window connected is still named
    readonly property var heldAdmin: {
        var s = falcon.session
        if (!falcon.traversing || !s || !s.pc_id) return null
        var t = overview.tree
        for (var i = 0; i < t.length; i++)
            for (var j = 0; j < t[i].admins.length; j++)
                if (t[i].admins[j].pc_id === s.pc_id) {
                    var o = {}
                    for (var k in t[i].admins[j]) o[k] = t[i].admins[j][k]
                    o.department_id = t[i].department_id
                    o.department_name = t[i].name
                    return o
                }
        return null
    }
    readonly property bool insideNow: inside && heldAdmin !== null
    // the one ticking clock: every countdown reads it, so they can never disagree by a second
    property double nowMs: Date.now()
    Timer {
        interval: 1000
        repeat: true
        running: falcon.traversing
        triggeredOnStart: true
        onTriggered: shell.nowMs = Date.now()
    }
    function goInside() {
        if (shell.heldAdmin === null) return
        shell.departmentId = shell.heldAdmin.department_id
        shell.inside = true
        shell.view = 0                  // the Admin's rail starts at their home, as theirs does
    }
    function stepOut() {
        shell.inside = false
        shell.show("authority")         // back to the department, the session still held
    }
    function leaveSession() {
        var s = falcon.session
        falcon.call("hierarchy.end_session", { session_id: s ? s.session_id : 0 }, function (ok, r) {
            shell.notify(ok ? "You left; the workstation is theirs again" : r.message, !ok)
        })
    }
    function extendSession() {
        var s = falcon.session
        falcon.call("hierarchy.extend_session", { session_id: s ? s.session_id : 0 }, function (ok, r) {
            shell.notify(ok ? "Extended" : r.message, !ok)
        })
    }
    // the session ended -- left, expired, or the link dropped past its deadline: out, never quietly
    // (Watched on heldAdmin, not insideNow: writing `inside` from insideNow's own handler is a loop,
    // and the rail has to be the Super User's again before "authority" can be found on it.)
    onHeldAdminChanged: if (heldAdmin === null && inside) stepOut()
    // reads look THROUGH the session only while the window is inside it -- holding is not looking
    Binding {
        target: falcon
        property: "viewThroughSession"
        value: shell.insideNow
    }
    Shortcut {
        sequence: "Escape"
        enabled: shell.insideNow
        onActivated: shell.stepOut()
    }
    function enterDepartment(id) {
        shell.departmentId = id
        shell.show("authority")
    }
    function show(key) {
        if (key === "resources") { show("hierarchy"); subPage = "resources"; return }
        var i = rail.indexOfKey(key)
        if (i < 0 && key === "authority") i = rail.indexOfKey("hierarchy")
        if (i < 0 && key === "hierarchy") i = rail.indexOfKey("authority")
        if (i >= 0) shell.view = i
    }
    // the views not yet rebuilt call root.notify(): keep that name resolving while they are ported
    property var root: shell
    function notify(text, alert) { toast.show(text, alert) }
    function select(accountId) { home.selected = home.find(accountId) }

    Connections {
        target: falcon
        function onPushText(text, alert) { shell.notify(text, alert) }
        function onConnectionFailed(message) { shell.notify("connection failed: " + message, true) }
        function onConnected() { shell.notify("connected as " + Theme.roleLabel(falcon.role), false) }
        function onDisconnected() { shell.notify("disconnected", true) }
    }
    Component.onCompleted: {
        if (autoConnect && falcon.defaultClientId.length > 0)
            falcon.connectTo(falcon.defaultHost, falcon.defaultPort, falcon.defaultClientId,
                             falcon.defaultClientKey, falcon.defaultPlaintext, falcon.defaultCaCert)
    }

    // the frame: ink at the top left, violet at the bottom right
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: Theme.frameA }
            GradientStop { position: 0.45; color: Theme.frameB }
            GradientStop { position: 1.0; color: Theme.frameC }
        }
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Qt.rgba(0.07, 0.07, 0.12, 0.35) }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TopBar {
            Layout.fillWidth: true
            indicators: falcon.indicators
            onMinimizeClicked: shell.showMinimized()
            onCloseClicked: Qt.quit()
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            IconRail {
                id: rail
                objectName: "iconRail"
                Layout.preferredWidth: Theme.railWidth
                Layout.fillHeight: true
                // inside an Admin the rail is theirs, entry for entry; the foot still says who you are
                role: shell.insideNow ? "admin" : falcon.role
                current: shell.view
                onPicked: function (i) { shell.view = i }
            }

            // the sheet
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.rightMargin: 8
                Layout.topMargin: 2
                Layout.bottomMargin: 8

                SessionLid {
                    id: lid
                    objectName: "sessionLid"
                    visible: shell.insideNow
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: 38
                    name: shell.heldAdmin ? (shell.heldAdmin.name || "an Admin") : ""
                    hostname: shell.heldAdmin ? (shell.heldAdmin.hostname || "") : ""
                    session: falcon.session
                    nowMs: shell.nowMs
                    onExtend: shell.extendSession()
                    onLeave: shell.leaveSession()
                    onStepOut: shell.stepOut()
                }

                Rectangle {
                    id: sheet
                    anchors.fill: parent
                    anchors.topMargin: shell.insideNow ? 46 : 0
                    radius: Theme.radiusMd
                    // The dashboards are drawn on the frame itself: the panels are the surfaces and
                    // the gradient shows between them, as on the boards. Only the views that still
                    // carry a sidebar -- the pre-kit ones -- keep the sheet under them. A department
                    // is drawn in the Overview's language, so it gets the frame too: the grey sheet
                    // under it was the old Admin-console shell showing through.
                    color: shell.onFrame ? "transparent" : Theme.pane
                    clip: true

                    StackLayout {
                        anchors.fill: parent
                        currentIndex: falcon.isConnected ? 1 : 0

                        ConnectView { objectName: "connectView" }

                        Item {
                            // Super User leads with the dashboards; both roles keep the hierarchy
                            // screen as the place work is actually done.
                            OverviewView {
                                id: overview
                                objectName: "overviewView"
                                anchors.fill: parent
                                visible: shell.onMustSee
                                heldAdmin: shell.heldAdmin
                                nowMs: shell.nowMs
                                onGoInside: shell.goInside()
                                onLeaveSession: shell.leaveSession()
                            }

                            HomeView {
                                id: home
                                objectName: "hierarchyRail"      // the hierarchy tree lives here now
                                anchors.fill: parent
                                // inside, it is the Admin's home: their department, drawn as theirs
                                asDepartment: 0
                                // the Super User's Authority area; an Admin's home is AdminHome below
                                visible: shell.viewKey === "authority" && !shell.inDepartment
                            }

                            // an Admin's home, at home or with a Super User inside them (HO03)
                            ResourcesView {
                                objectName: "resourcesView"
                                anchors.fill: parent
                                visible: shell.viewKey === "hierarchy" && shell.subPage === "resources"
                                clock: overview.clock
                                focus: visible
                                Keys.onEscapePressed: shell.subPage = ""
                                onBack: shell.subPage = ""
                            }
                            AdminHome {
                                id: adminHome
                                objectName: "adminHome"
                                anchors.fill: parent
                                visible: shell.viewKey === "hierarchy" && shell.subPage === ""
                                departmentId: shell.insideNow ? shell.heldAdmin.department_id : 0
                                clock: overview.clock
                            }

                            // level 2: the department, drawn in the Overview's language and fed by
                            // the same handlers the Overview already asked for
                            DepartmentView {
                                objectName: "departmentView"
                                anchors.fill: parent
                                visible: shell.inDepartment
                                departmentId: shell.departmentId
                                tree: overview.tree
                                rollout: overview.rollout
                                sessions: overview.sessions
                                violations: overview.violations
                                deviations: overview.deviations
                                clock: overview.clock
                                heldAdmin: shell.heldAdmin
                                nowMs: shell.nowMs
                                tasks: overview.tasks
                                flows: overview.flows
                                onOpenRecord: shell.show("record")
                                onBack: shell.departmentId = 0
                                onGoInside: shell.goInside()
                                onLeaveSession: shell.leaveSession()
                            }

                            // THE ADMIN'S OWN SCREENS, on the Admin rail's entries. They are the pre-kit
                            // views and are shown as they are: an Admin at home and a Super User inside
                            // that Admin see the same window (LEVELS.md, level 3). The Super User's own
                            // rail has no such entries, so there they stay mounted out of sight.
                            TasksView { objectName: "tasksView"; anchors.fill: parent
                                        visible: shell.viewKey === "tasks"; clock: overview.clock }
                            FlowsView { objectName: "flowsView"; anchors.fill: parent
                                        visible: shell.viewKey === "flows"; clock: overview.clock }
                            AutomationView { objectName: "automationView"; anchors.fill: parent
                                             visible: shell.viewKey === "automation"; clock: overview.clock }
                            ActionsView { objectName: "actionsView"; anchors.fill: parent
                                          visible: shell.viewKey === "actions"; clock: overview.clock }
                            AssistanceView { objectName: "assistanceView"; anchors.fill: parent
                                             visible: shell.viewKey === "assistance" ; clock: overview.clock }
                            ReportsView { objectName: "reportsView"; anchors.fill: parent
                                          visible: shell.viewKey === "reports" ; clock: overview.clock }
                            // Rollout (boards RO05, RO06): departments, then one maximised
                            RolloutView {
                                objectName: "rolloutView"
                                anchors.fill: parent
                                visible: shell.viewKey === "rollout" && !shell.insideNow
                                clock: overview.clock
                            }
                            // Record (board RC05): past and present
                            RecordView {
                                objectName: "recordView"
                                anchors.fill: parent
                                visible: shell.viewKey === "record" && !shell.insideNow
                                clock: overview.clock
                            }
                            // Work (board WK03): by department, yours, help watched
                            WorkView {
                                objectName: "workView"
                                anchors.fill: parent
                                visible: shell.viewKey === "work" && !shell.insideNow
                                clock: overview.clock
                            }
                        }
                    }

                    // state, as a floating pill over the sheet -- the frame never changes
                    Rectangle {
                        id: statePill
                        // A Super User's held session is carried by the container on the department
                        // page and, inside, by the lid -- a third copy floating over every page
                        // would be the same fact said twice.
                        visible: falcon.blocked || (falcon.traversing && falcon.role !== "super_user")
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 10
                        height: 36
                        width: pillRow.implicitWidth + 28
                        radius: Theme.pill
                        color: falcon.blocked ? Theme.dangerDeep : Theme.warnDeep

                        Row {
                            id: pillRow
                            anchors.centerIn: parent
                            spacing: 9
                            Icon {
                                name: falcon.blocked ? "shield" : "lock"
                                color: "#ffffff"
                                size: 15
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            Txt {
                                text: falcon.blocked
                                      ? ("Super User is in charge of your view" + (falcon.blockedBy ? " — " + falcon.blockedBy : ""))
                                      : falcon.sessionText
                                color: "#ffffff"
                                font.pixelSize: Theme.fBody
                                font.weight: Font.Medium
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            GBtn {
                                text: falcon.blocked ? "Claim" : "Leave"
                                small: true
                                anchors.verticalCenter: parent.verticalCenter
                                onClicked: falcon.blocked
                                    ? falcon.call("hierarchy.claim_native", {}, function (ok, r) { shell.notify(ok ? "claimed" : r.message, !ok) })
                                    : falcon.call("hierarchy.end_session", { session_id: falcon.session ? falcon.session.session_id : 0 },
                                                  function (ok, r) { shell.notify(ok ? "left" : r.message, !ok) })
                            }
                        }
                    }

                    // a toast confirms what you did; it never changes the detail card
                    Rectangle {
                        id: toast
                        function show(text, alert) { label.text = text; toast.alert = !!alert; anim.restart() }
                        property bool alert: false

                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 26
                        height: 44
                        width: toastRow.implicitWidth + 28
                        radius: Theme.radiusMd
                        color: Theme.ground
                        opacity: 0
                        visible: opacity > 0

                        Row {
                            id: toastRow
                            anchors.centerIn: parent
                            spacing: 10
                            Icon {
                                name: toast.alert ? "warn" : "check"
                                color: toast.alert ? Theme.danger : Theme.ok
                                size: 16
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            Txt {
                                id: label
                                color: Theme.ink
                                font.pixelSize: Theme.fBody
                                font.weight: Font.Medium
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                        SequentialAnimation {
                            id: anim
                            NumberAnimation { target: toast; property: "opacity"; to: 1; duration: Theme.durFast }
                            PauseAnimation { duration: 3200 }
                            NumberAnimation { target: toast; property: "opacity"; to: 0; duration: Theme.durBase }
                        }
                    }
                }
            }
        }

        // the status line: the link, and the session in words
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.statusHeight

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Rectangle {
                    width: 7
                    height: 7
                    radius: 4
                    color: falcon.isConnected ? Theme.ok : Theme.danger
                    anchors.verticalCenter: parent.verticalCenter
                    SequentialAnimation on opacity {
                        running: falcon.isConnected
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.35; duration: 1400; easing.type: Easing.InOutQuad }
                        NumberAnimation { to: 1.0; duration: 1400; easing.type: Easing.InOutQuad }
                    }
                }
                Txt {
                    text: falcon.isConnected ? ("Connected to " + falcon.engineAddress) : "Not connected"
                    color: Qt.rgba(1, 1, 1, 0.68)
                    font.pixelSize: Theme.fSmall
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            Txt {
                anchors.right: parent.right
                anchors.rightMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                text: falcon.isConnected ? falcon.sessionText : ""
                color: Qt.rgba(1, 1, 1, 0.45)
                monospace: true
                font.pixelSize: Theme.fSmall
            }
        }
    }
}
