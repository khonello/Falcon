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
// ONE CONSOLE, THE IT ADMIN'S (docs/design/v1-it-admin.md): every department, which is a label for
// grouping and filtering, not a wall.
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
        property bool pulseOn: true             // the bulb beside the theme: a section a click changed pulses once
        property bool askFirst: true            // a button that opens another page asks first
    }
    Binding { target: Theme; property: "mode"; value: prefs.themeMode }
    Binding { target: Theme; property: "pulseOn"; value: prefs.pulseOn }
    Binding { target: Nav; property: "askFirst"; value: prefs.askFirst }
    Connections { target: Nav; function onAsking(req) { askGo.ask(req) } }
    Connections { target: sider; function onAskAgain() { prefs.askFirst = true } }

    Binding { target: Nav; property: "me"; value: Nav.myName || falcon.roleLabel }

    // a page the console does not have opens the Overview instead
    Connections {
        target: Nav
        function onPageChanged() { if (!Nav.allowed(Nav.page)) Nav.page = "overview" }
    }

    // --- what needs a person, counted on the menu ------------------------------------------------
    Counter { id: counter }

    // --- the pages -----------------------------------------------------------------------------------
    // A page not yet ported to the concept keeps its earlier view until its own lands.
    readonly property var pages: ({
        overview: "OverviewPage.qml",
        messages: "MessagesPage.qml",
        calendar: "CalendarPage.qml",
        detective: "DetectivePage.qml",
        tasks: "TasksPage.qml",
        restricted: "RestrictedPage.qml",
        flows: "FlowsPage.qml",
        machines: "MachinesPage.qml",
        issues: "IssuesPage.qml",
        automation: "AutomationPage.qml",
        actions: "ActionsPage.qml",
        audit: "AuditPage.qml",
        registry: "RegistryPage.qml",
        departments: "DepartmentsPage.qml",
    })

    // a page and the thing open on it: some open a page of their own (a machine, an editor)
    function pageFile(p, s) {
        if (p === "machines" && s) return "MachinePage.qml"
        if (p === "messages" && s === "announcements") return "AnnouncementsPage.qml"
        if (p === "tasks" && s === "new") return "NewTaskPage.qml"
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
        }

        Item {
            id: mainArea
            width: parent.width - sider.width
            height: parent.height

            Column {
                id: tops
                width: parent.width

                // your to-do, when its time comes: one line across the top
                TodoStrip { width: parent.width }

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

                    // the path, at the left; it gives way to the search when it is long
                    Crumb {
                        id: crumbItem
                        objectName: "crumb"
                        x: 20
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    // search, which is a jump: pages, machines, issues. In the middle of the bar, so it is the centre line the page
                    // and the palette share; it shrinks, never moves, when the two ends need the room
                    Rectangle {
                        id: searchBox
                        objectName: "searchBox"
                        readonly property real room: header.width - 2 * Math.max(crumbItem.implicitWidth + 40, rightEnd.width + 20) - 24
                        width: Math.max(240, Math.min(Theme.searchW, room))
                        height: 32; radius: 5
                        x: (header.width - width) / 2
                        color: Theme.surface2
                        border.width: 1
                        border.color: Theme.border
                        anchors.verticalCenter: parent.verticalCenter
                        Row {
                            x: 12
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

                    Row {
                        id: rightEnd
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
                        // the pulse, on or off; not everyone will want it (the user, 1 Nov 2026)
                        Btn {
                            objectName: "pulseSwitch"
                            kind: "text"; small: true; iconName: "bulb"
                            anchors.verticalCenter: parent.verticalCenter
                            tip: prefs.pulseOn ? "Changed sections pulse once · click to stop" : "Changed sections do not pulse · click to turn it on"
                            opacity: prefs.pulseOn ? 1 : 0.45
                            onClicked: prefs.pulseOn = !prefs.pulseOn
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

    SessionWindow { }
    Palette { id: palette }
    AskGo { id: askGo; onStopAsking: prefs.askFirst = false }
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
