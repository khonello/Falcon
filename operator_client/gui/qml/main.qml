import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import QtCore
import "."

// THE CONSOLE, as the published concept (Falcon Concepts) draws it. A fixed sider of grouped areas
// with what needs a person counted beside each; a top bar with the path, search, the time range,
// the live mark and the theme; the page under it. The window is frameless, so the top bar is also
// its title bar.
//
// WHICH LEVEL YOU ARE AT DECIDES WHAT THE CONSOLE IS (hierarchy-system-design.md). A Super User at
// their own level governs: Core, Organisation, Govern. Inside an Admin's console -- an Admin's own,
// or one a Super User entered by blocking or ending that Admin's session -- it is the Admin's full
// menu for one department, and a Super User sees "Super User in charge" across the top.
ApplicationWindow {
    id: shell

    width: 1440
    height: 900
    visible: true
    color: Theme.bg
    title: "Falcon"
    flags: Qt.Window | Qt.FramelessWindowHint

    readonly property bool maximised: shell.visibility === Window.Maximized
    function toggleMaximised() { shell.maximised ? shell.showNormal() : shell.showMaximized() }

    // the preview and the tests open a page by name
    property string view: ""
    onViewChanged: if (view !== "") { var parts = view.split("/"); Nav.go(parts[0], parts.length > 1 ? parts.slice(1).join("/") : null) }
    // what the tests read: the menu this level has, and the page open now as "page/sub"
    readonly property var menuKeys: [].concat.apply([], Nav.menu.map(function (g) { return g[1].map(function (i) { return i[0] }) }))
    readonly property string where: Nav.page + (Nav.sub !== null && Nav.sub !== undefined ? "/" + Nav.sub : "")

    Settings {
        id: prefs
        category: "console"
        property string themeMode: "system"
    }
    Binding { target: Theme; property: "mode"; value: prefs.themeMode }

    // --- the level ---------------------------------------------------------------------------------
    readonly property bool superUser: falcon.role === "super_user"
    readonly property bool inside: superUser && falcon.traversing
    Binding { target: Nav; property: "boss"; value: shell.superUser && !shell.inside }
    Binding { target: Nav; property: "inside"; value: shell.inside }
    Binding { target: Nav; property: "me"; value: shell.inside ? (enter.who || "the Admin") : (Nav.myName || falcon.roleLabel) }
    // the Engine re-answers reads as the Admin being looked through (protocol/viewing.py)
    Binding { target: falcon; property: "viewThroughSession"; value: shell.inside }

    // a page the level does not have opens the Overview instead
    Connections {
        target: Nav
        function onBossChanged() { if (!Nav.allowed(Nav.page)) Nav.go("overview") }
        function onPageChanged() { if (!Nav.allowed(Nav.page)) Nav.page = "overview" }
    }

    // --- what needs a person, counted on the menu ------------------------------------------------
    Counter { id: counter }

    // --- the pages -----------------------------------------------------------------------------------
    // A page not yet ported to the concept keeps its earlier view until its own lands.
    readonly property var pages: ({
        overview: Nav.boss ? "SuOverviewPage.qml" : "OverviewPage.qml",
        messages: "MessagesPage.qml",
        detective: Nav.boss ? "DetectiveOverviewPage.qml" : "DetectivePage.qml",
        tasks: Nav.boss ? "GivenTasksPage.qml" : "TasksPage.qml",
        restricted: "RestrictedPage.qml",
        flows: Nav.boss ? "FlowsOverviewPage.qml" : "FlowsPage.qml",
        machines: "MachinesPage.qml",
        issues: "IssuesPage.qml",
        automation: "AutomationPage.qml",
        actions: "ActionsPage.qml",
        audit: "AuditPage.qml",
        departments: "DepartmentsPage.qml",
        registry: "RegistryPage.qml",
    })

    // a page and the thing open on it: some open a page of their own (a machine, an editor)
    function pageFile(p, s) {
        if (p === "machines" && s) return "MachinePage.qml"
        if (p === "messages" && s === "announcements") return "AnnouncementsPage.qml"
        if (p === "tasks" && s === "new") return Nav.boss ? "GiveTaskPage.qml" : "NewTaskPage.qml"
        if (p === "restricted" && s === "mark") return "MarkPage.qml"
        if (p === "flows" && s && (s === "new" || String(s).indexOf("edit-") === 0)) return "NewFlowPage.qml"
        if (p === "automation" && s && (s === "new" || String(s).indexOf("edit-") === 0)) return "NewRulePage.qml"
        if (p === "actions" && s && (s === "new" || String(s).indexOf("edit-") === 0)) return "NewActionPage.qml"
        var f = shell.pages[p]
        return f === undefined || f === "" ? "Pending.qml" : f
    }

    Row {
        anchors.fill: parent
        spacing: 0

        Sider {
            id: sider
            objectName: "sideMenu"
            height: parent.height
            onLeave: enter.leaveConsole()
        }

        Item {
            id: mainArea
            width: parent.width - sider.width
            height: parent.height

            Column {
                id: tops
                width: parent.width

                // --- Super User in charge: a tint across the full width, never a stripe ----------------
                Rectangle {
                    objectName: "sessionBanner"
                    visible: shell.inside
                    width: parent.width
                    height: visible ? 38 : 0
                    color: Theme.mix(Theme.crit, Theme.surface, 0.12)
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.alpha(Theme.crit, 0.3) }
                    Row {
                        x: 20
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 10
                        Icon { name: "safety"; size: 15; color: Theme.crit; anchors.verticalCenter: parent.verticalCenter }
                        Txt { text: "Super User in charge"; color: Theme.crit; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
                        Txt {
                            anchors.verticalCenter: parent.verticalCenter
                            width: Math.max(0, mainArea.width - 520)
                            text: "You are in " + Nav.me + "'s console" + (Nav.deptName ? " · " + Nav.deptName : "")
                                  + " · their session is " + (enter.how === "block" ? "blocked" : "ended")
                        }
                    }
                    Row {
                        anchors.right: parent.right
                        anchors.rightMargin: 20
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 10
                        Txt {
                            mono: true
                            color: Theme.crit
                            anchors.verticalCenter: parent.verticalCenter
                            elide: Text.ElideNone
                            text: {
                                var s = falcon.session && falcon.session.entered_at
                                        ? Math.max(0, Math.floor((Time.now - Time.ms(falcon.session.entered_at)) / 1000)) : 0
                                return Math.floor(s / 60) + ":" + Time.pad(s % 60)
                            }
                        }
                        Btn { small: true; text: "Leave"; anchors.verticalCenter: parent.verticalCenter; onClicked: enter.leaveConsole() }
                    }
                }

                // --- a task from the Super User nobody has marked seen ---------------------------------
                NewTaskStrip { id: strip; width: parent.width; tasks: counter.unseenTasks; onMarked: counter.refresh() }

                // --- the top bar, which is also the title bar --------------------------------------------
                Rectangle {
                    id: header
                    width: parent.width
                    height: 50
                    color: Theme.surface
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }

                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton
                        onPressed: if (!shell.maximised) shell.startSystemMove()
                        onDoubleClicked: shell.toggleMaximised()
                    }

                    Row {
                        x: 20
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 12
                        Crumb {
                            objectName: "crumb"
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        // search, which is a jump: pages, machines, issues
                        Rectangle {
                            width: 240; height: 30; radius: 5
                            color: Theme.surface2
                            border.width: 1
                            border.color: Theme.border
                            anchors.verticalCenter: parent.verticalCenter
                            Row {
                                x: 10
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 8
                                Icon { name: "search"; size: 13; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                                Txt { text: "Search or jump to"; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                            }
                            Rectangle {
                                anchors.right: parent.right
                                anchors.rightMargin: 8
                                anchors.verticalCenter: parent.verticalCenter
                                width: kbd.implicitWidth + 10; height: 18; radius: 3
                                color: "transparent"
                                border.width: 1
                                border.color: Theme.borderStrong
                                Txt { id: kbd; anchors.centerIn: parent; text: "Ctrl K"; mono: true; font.pixelSize: 11; color: Theme.text3 }
                            }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: palette.open() }
                        }
                    }

                    Row {
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 12

                        Segmented {
                            objectName: "range"
                            visible: (Nav.boss ? ["machines", "audit"] : ["overview", "machines", "audit"]).indexOf(Nav.page) >= 0
                            anchors.verticalCenter: parent.verticalCenter
                            options: ["1h", "6h", "24h", "7d"]
                            value: Nav.range
                            onPicked: function (v) { Nav.range = v }
                        }
                        Row {
                            spacing: 6
                            anchors.verticalCenter: parent.verticalCenter
                            Rectangle {
                                width: 7; height: 7; radius: 4
                                color: falcon.isConnected ? Theme.ok : Theme.crit
                                anchors.verticalCenter: parent.verticalCenter
                                Rectangle { anchors.centerIn: parent; width: 13; height: 13; radius: 7; color: Theme.alpha(parent.color, 0.22); z: -1 }
                            }
                            Txt {
                                anchors.verticalCenter: parent.verticalCenter
                                color: Theme.text3
                                font.pixelSize: Theme.fSmall
                                elide: Text.ElideNone
                                text: falcon.isConnected ? "Live · " + Math.floor((Math.max(0, Time.now - counter.at) / 1000) % 60) + "s ago" : "Not connected"
                            }
                        }
                        Segmented {
                            objectName: "themeSwitch"
                            anchors.verticalCenter: parent.verticalCenter
                            options: [{ value: "system", icon: "desktop" }, { value: "light", icon: "sun" }, { value: "dark", icon: "moon" }]
                            value: prefs.themeMode
                            onPicked: function (v) { prefs.themeMode = v }
                        }
                        Row {
                            spacing: 0
                            anchors.verticalCenter: parent.verticalCenter
                            Btn { objectName: "winMinimize"; kind: "text"; small: true; iconName: "min"; onClicked: shell.showMinimized() }
                            Btn { objectName: "winMaximize"; kind: "text"; small: true; iconName: shell.maximised ? "restore" : "max"; onClicked: shell.toggleMaximised() }
                            Btn { objectName: "winClose"; kind: "text"; small: true; iconName: "close"; onClicked: Qt.quit() }
                        }
                    }
                }
            }

            // --- the page --------------------------------------------------------------------------------
            Item {
                id: content
                anchors.top: tops.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom

                Loader {
                    id: pageLoader
                    objectName: "page"
                    anchors.fill: parent
                    active: falcon.isConnected
                    source: shell.pageFile(Nav.page, Nav.sub)
                }
                Connect {
                    anchors.fill: parent
                    visible: !falcon.isConnected
                }
            }
        }
    }

    EnterConsole { id: enter }
    Connections { target: Nav; function onEnterRequested(admin, to) { enter.ask(admin, to) } }
    SessionWindow { }
    Palette { id: palette }
    Shortcut { sequences: ["Ctrl+K", "Ctrl+P"]; onActivated: palette.visible ? palette.close() : palette.open() }
    Shortcut { sequences: ["Ctrl+Shift+P"]; onActivated: palette.openWith(">") }

    // every `Msg` from anywhere in the console lands here, over everything, including a modal
    Toast {
        objectName: "toast"
        parent: Overlay.overlay
        anchors.fill: parent
        z: 100
    }

    // --- resizing, since there is no frame to grab ----------------------------------------------
    component Grip: MouseArea {
        property int edges: 0
        enabled: !shell.maximised
        acceptedButtons: Qt.LeftButton
        onPressed: shell.startSystemResize(edges)
    }
    Grip { edges: Qt.LeftEdge; cursorShape: Qt.SizeHorCursor; width: 5
           anchors { left: parent.left; top: parent.top; bottom: parent.bottom; topMargin: 8; bottomMargin: 8 } }
    Grip { edges: Qt.RightEdge; cursorShape: Qt.SizeHorCursor; width: 5
           anchors { right: parent.right; top: parent.top; bottom: parent.bottom; topMargin: 8; bottomMargin: 8 } }
    Grip { edges: Qt.TopEdge; cursorShape: Qt.SizeVerCursor; height: 5
           anchors { top: parent.top; left: parent.left; right: parent.right; leftMargin: 8; rightMargin: 8 } }
    Grip { edges: Qt.BottomEdge; cursorShape: Qt.SizeVerCursor; height: 5
           anchors { bottom: parent.bottom; left: parent.left; right: parent.right; leftMargin: 8; rightMargin: 8 } }
    Grip { edges: Qt.LeftEdge | Qt.TopEdge; cursorShape: Qt.SizeFDiagCursor; width: 8; height: 8
           anchors.left: parent.left; anchors.top: parent.top }
    Grip { edges: Qt.RightEdge | Qt.TopEdge; cursorShape: Qt.SizeBDiagCursor; width: 8; height: 8
           anchors.right: parent.right; anchors.top: parent.top }
    Grip { edges: Qt.LeftEdge | Qt.BottomEdge; cursorShape: Qt.SizeBDiagCursor; width: 8; height: 8
           anchors.left: parent.left; anchors.bottom: parent.bottom }
    Grip { edges: Qt.RightEdge | Qt.BottomEdge; cursorShape: Qt.SizeFDiagCursor; width: 8; height: 8
           anchors.right: parent.right; anchors.bottom: parent.bottom }
}
