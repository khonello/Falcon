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
    property string view: "record"
    // derived, never set: a crumb that has to be remembered gets forgotten
    readonly property var crumbs: {
        for (var i = 0; i < areas.length; i++)
            if (areas[i].key === view) return ["Falcon", areas[i].label]
        return ["Falcon"]
    }

    function toggleMaximised() { shell.maximised ? shell.showNormal() : shell.showMaximized() }

    readonly property var areas: [
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
        { key: "record",      icon: "history", label: "Record" }
    ]

    Row {
        anchors.fill: parent
        spacing: 0

        SideMenu {
            id: sider
            objectName: "sideMenu"
            height: parent.height
            entries: shell.areas
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

            // --- the content -----------------------------------------------------------------------
            Item {
                anchors.top: header.bottom
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

                // every other area, until its page is built
                Empty {
                    visible: ["record", "machines", "departments", "tasks", "flows",
                              "automation", "actions"].indexOf(shell.view) < 0
                    anchors.centerIn: parent
                    width: 360
                    text: "Not built yet"
                    hint: "Seven pages are built. The rest follow, in the order in docs/UI-COMPONENTS.md."
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
