import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import "."

// THE CONSOLE (docs/UI.md). Sider, header, content -- and the window's own chrome, because it is
// frameless and the top bar IS the title bar.
ApplicationWindow {
    id: shell

    width: 1440
    height: 900
    visible: true
    color: Theme.page
    title: "Falcon"
    flags: Qt.Window | Qt.FramelessWindowHint

    readonly property bool maximised: shell.visibility === Window.Maximized
    property string view: "overview"
    // derived, never set: a crumb that has to be remembered gets forgotten
    readonly property var crumbs: {
        for (var i = 0; i < areas.length; i++)
            if (areas[i].key === view) return ["Falcon", areas[i].label]
        return ["Falcon"]
    }

    function toggleMaximised() { shell.maximised ? shell.showNormal() : shell.showMaximized() }

    // WHICH LEVEL YOU ARE AT DECIDES WHAT THE CONSOLE IS (hierarchy-system-design.md).
    //
    // The Admin is where the operating features live: "the source of all monitoring and control
    // operations... all features concentrated at this level". The Super User governs -- reports,
    // audit, system status, high-level summaries -- and "does not perform day-to-day operations".
    // They reach the operating features by traversing into an Admin, and then the console shows
    // exactly what that Admin sees, with the red banner up and reads answered as them.
    readonly property bool boss: falcon.role === "super_user"

    // THE SIDER SAYS WHAT NEEDS A PERSON. Overview already works out that list for its own page, so
    // it is the one that counts them; a second count somewhere else would drift from the first.
    readonly property var needBadges: {
        var out = ({})
        var needs = overviewPage && overviewPage.needs ? overviewPage.needs : []
        for (var i = 0; i < needs.length; i++)
            out[needs[i].where] = (out[needs[i].where] || 0) + 1
        return out
    }
    readonly property var allAreas: baseAreas.map(function (a) {
        return { key: a.key, icon: a.icon, label: a.label, badge: shell.needBadges[a.key] || 0 }
    })
    readonly property bool lookingThrough: boss && falcon.traversing
    readonly property var governance: ["overview", "departments", "people", "tasks", "reports",
                                       "rollout", "record", "settings"]
    readonly property var areas: (!boss || lookingThrough) ? allAreas
        : allAreas.filter(function (a) { return governance.indexOf(a.key) >= 0 })

    // a Super User who leaves a session cannot stay on a page that was the Admin's
    onViewChanged: shell.settle()
    onAreasChanged: shell.settle()
    function settle() {
        if (view === "kit") return                 // the kit board: reachable only from the preview
        for (var i = 0; i < areas.length; i++)
            if (areas[i].key === view) return
        view = "overview"
    }

    // the Engine re-answers reads as the Admin being looked through (protocol/viewing.py); holding
    // a session without looking through it does not, which is why this is a binding and not a flag
    Binding { target: falcon; property: "viewThroughSession"; value: shell.lookingThrough }

    readonly property var baseAreas: [
        { key: "overview",    icon: "pulse",   label: "Overview" },
        { key: "departments", icon: "dept",    label: "Departments" },
        { key: "people",      icon: "people",  label: "People" },
        { key: "machines",    icon: "monitor", label: "Machines" },
        { key: "tasks",       icon: "tasks",   label: "Tasks" },
        { key: "flows",       icon: "flows",   label: "Flows" },
        { key: "automation",  icon: "bolt",    label: "Automation" },
        { key: "actions",     icon: "play",    label: "Actions" },
        { key: "assistance",  icon: "message", label: "Assistance" },
        { key: "resources",   icon: "folder",  label: "Resources" },
        { key: "reports",     icon: "file",    label: "Reports" },
        { key: "rollout",     icon: "cloud",   label: "Rollout" },
        { key: "record",      icon: "history", label: "Record" },
        { key: "settings",    icon: "gear",    label: "Settings" }
    ]

    Row {
        anchors.fill: parent
        spacing: 0

        SideMenu {
            id: sider
            objectName: "sideMenu"
            height: parent.height
            entries: shell.areas
            level: shell.lookingThrough && falcon.session && falcon.session.hostname
                   ? "inside " + falcon.session.hostname : falcon.roleLabel
            current: shell.view
            onPicked: function (key) { shell.view = key }
        }

        Item {
            width: parent.width - sider.width
            height: parent.height

            // --- the header: the title bar, the crumb, the state, the window's own buttons --------
            Rectangle {
                id: header
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 48
                color: Theme.surface
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.split }

                // the empty part of the bar drags the window; a double click maximises it
                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    onPressed: if (!shell.maximised) shell.startSystemMove()
                    onDoubleClicked: shell.toggleMaximised()
                }

                Crumb {
                    objectName: "crumb"
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.s4
                    anchors.verticalCenter: parent.verticalCenter
                    path: shell.crumbs
                }

                Row {
                    anchors.right: parent.right
                    anchors.rightMargin: Theme.s2
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Theme.s3

                    Row {
                        spacing: Theme.s2
                        anchors.verticalCenter: parent.verticalCenter
                        Dot {
                            tone: falcon.isConnected ? "mid" : "danger"
                            hollow: !falcon.isConnected
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Txt {
                            text: falcon.isConnected ? "Connected" : "Not connected"
                            tone: "mid"
                            font.pixelSize: Theme.fSmall
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Row {
                        spacing: Theme.s2
                        anchors.verticalCenter: parent.verticalCenter
                        Rectangle {
                            width: 24; height: 24; radius: 12; color: Theme.primary
                            anchors.verticalCenter: parent.verticalCenter
                            Txt {
                                anchors.centerIn: parent
                                text: Theme.initials(falcon.roleLabel)
                                color: Theme.onDark
                                font.pixelSize: 10
                                strong: true
                            }
                        }
                        Txt {
                            text: falcon.roleLabel
                            font.pixelSize: Theme.fSmall
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Row {
                        spacing: 0
                        anchors.verticalCenter: parent.verticalCenter
                        Btn { objectName: "winMinimize"; kind: "text"; small: true; iconName: "min"
                              onClicked: shell.showMinimized() }
                        Btn { objectName: "winMaximize"; kind: "text"; small: true
                              iconName: shell.maximised ? "restore" : "max"; onClicked: shell.toggleMaximised() }
                        Btn { objectName: "winClose"; kind: "text"; small: true; iconName: "close"
                              onClicked: Qt.quit() }
                    }
                }
            }

            // --- you are inside somebody's machine, and only then --------------------------------
            SessionBanner {
                id: banner
                objectName: "sessionBanner"
                anchors.top: header.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                visible: falcon.traversing || falcon.blocked
                mode: falcon.blocked ? "held" : "inside"
                inCharge: falcon.superUserBanner
                who: falcon.blocked ? falcon.blockedBy : ""
                session: falcon.blocked ? falcon.blockedSession : falcon.session
                until: session && session.deadline_at ? session.deadline_at : ""
                since: session && session.entered_at ? session.entered_at : ""
                onLeave: falcon.call("hierarchy.end_session",
                                     { session_id: falcon.session.session_id }, function (ok, r) {
                    if (!ok) { Msg.failed(r && r.message ? r.message : "Still inside"); return }
                    Msg.ok("Left")
                })
                onExtend: falcon.call("hierarchy.extend_session",
                                      { session_id: falcon.session.session_id }, function (ok, r) {
                    if (!ok) { Msg.failed(r && r.message ? r.message : "Not extended"); return }
                    Msg.ok("Extended")
                })
            }

            // --- the content -----------------------------------------------------------------------
            Item {
                anchors.top: banner.visible ? banner.bottom : header.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom

                RecordView {
                    objectName: "recordView"
                    anchors.fill: parent
                    visible: shell.view === "record"
                }
                MachinesView {
                    objectName: "machinesView"
                    anchors.fill: parent
                    visible: shell.view === "machines"
                }
                DepartmentsView {
                    objectName: "departmentsView"
                    anchors.fill: parent
                    visible: shell.view === "departments"
                }

                TasksView {
                    objectName: "tasksView"
                    anchors.fill: parent
                    visible: shell.view === "tasks"
                }

                FlowsView {
                    objectName: "flowsView"
                    anchors.fill: parent
                    visible: shell.view === "flows"
                }

                AutomationView {
                    objectName: "automationView"
                    anchors.fill: parent
                    visible: shell.view === "automation"
                }
                ActionsView {
                    objectName: "actionsView"
                    anchors.fill: parent
                    visible: shell.view === "actions"
                }

                AssistanceView {
                    objectName: "assistanceView"
                    anchors.fill: parent
                    visible: shell.view === "assistance"
                }
                ResourcesView {
                    objectName: "resourcesView"
                    anchors.fill: parent
                    visible: shell.view === "resources"
                }
                ReportsView {
                    objectName: "reportsView"
                    anchors.fill: parent
                    visible: shell.view === "reports"
                }
                RolloutView {
                    objectName: "rolloutView"
                    anchors.fill: parent
                    visible: shell.view === "rollout"
                }

                OverviewView {
                    id: overviewPage
                    objectName: "overviewView"
                    anchors.fill: parent
                    visible: shell.view === "overview"
                    reach: shell.areas.map(function (a) { return a.key })
                    onGo: function (view) { shell.view = view }
                }
                PeopleView {
                    objectName: "peopleView"
                    anchors.fill: parent
                    visible: shell.view === "people"
                }
                SettingsView {
                    objectName: "settingsView"
                    anchors.fill: parent
                    visible: shell.view === "settings"
                }

                // the kit drawn in itself, for judging it. Not an area: `--view kit` only.
                Loader {
                    objectName: "kitView"
                    anchors.fill: parent
                    active: shell.view === "kit"
                    source: "KitView.qml"
                }
            }
        }
    }

    // every `Msg` from anywhere in the console lands here, over everything, including a modal
    Toast {
        objectName: "toast"
        parent: Overlay.overlay
        anchors.fill: parent
        anchors.topMargin: header.height          // it belongs under the title bar, not across it
        z: 100
    }

    // --- resizing, since there is no frame to grab ----------------------------------------------
    component Grip: MouseArea {
        property int edges: 0
        enabled: !shell.maximised
        acceptedButtons: Qt.LeftButton
        onPressed: shell.startSystemResize(edges)
    }
    Grip {
        edges: Qt.LeftEdge; cursorShape: Qt.SizeHorCursor; width: 5
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom; topMargin: 8; bottomMargin: 8 }
    }
    Grip {
        edges: Qt.RightEdge; cursorShape: Qt.SizeHorCursor; width: 5
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom; topMargin: 8; bottomMargin: 8 }
    }
    Grip {
        edges: Qt.TopEdge; cursorShape: Qt.SizeVerCursor; height: 5
        anchors { top: parent.top; left: parent.left; right: parent.right; leftMargin: 8; rightMargin: 8 }
    }
    Grip {
        edges: Qt.BottomEdge; cursorShape: Qt.SizeVerCursor; height: 5
        anchors { bottom: parent.bottom; left: parent.left; right: parent.right; leftMargin: 8; rightMargin: 8 }
    }
    Grip {
        edges: Qt.LeftEdge | Qt.TopEdge; cursorShape: Qt.SizeFDiagCursor; width: 8; height: 8
        anchors.left: parent.left; anchors.top: parent.top
    }
    Grip {
        edges: Qt.RightEdge | Qt.TopEdge; cursorShape: Qt.SizeBDiagCursor; width: 8; height: 8
        anchors.right: parent.right; anchors.top: parent.top
    }
    Grip {
        edges: Qt.LeftEdge | Qt.BottomEdge; cursorShape: Qt.SizeBDiagCursor; width: 8; height: 8
        anchors.left: parent.left; anchors.bottom: parent.bottom
    }
    Grip {
        edges: Qt.RightEdge | Qt.BottomEdge; cursorShape: Qt.SizeFDiagCursor; width: 8; height: 8
        anchors.right: parent.right; anchors.bottom: parent.bottom
    }
}
