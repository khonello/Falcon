import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "."

// The Operator Client shell. One theme, stated once (Theme.qml); Material dark with the small
// corner radius so controls read as an instrument, not a phone app.
//
// Structure (ui-reference.md): a header carrying identity, primary navigation and the connection;
// a full-width banner for anything with consequences (the Super User is inside your view, your
// PC is blocked); the hierarchy as an always-visible left rail whose selection is the context
// every page works on; the page; the live feed pinned underneath; a footer with the pulsing link
// dot and your session.
ApplicationWindow {
    id: root
    Material.theme: Material.Dark
    Material.background: Theme.canvas
    Material.primary: Theme.surface
    Material.accent: Theme.accent
    Material.foreground: Theme.text
    Material.roundedScale: Material.SmallScale

    // Full screen without resize: app.fit_to_screen() pins the window to the work area once the
    // native frame exists. Title bar offers minimize and close only.
    width: 1280
    height: 820
    flags: Qt.Window | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint | Qt.CustomizeWindowHint
    visible: true
    title: "Falcon" + (falcon.isConnected ? "  —  " + falcon.roleLabel + " @ " + falcon.engineAddress : "")
    color: Theme.canvas

    // --- the context every page works on: the account/PC selected in the rail ----------------
    readonly property var selected: rail.selected
    property int currentView: 0
    readonly property var views: ["Hierarchy", "Tasks", "Flows", "Automation", "Assistance", "Reports"]

    function notify(text, alert) { feed.add(text, alert) }
    function select(accountId) { rail.selected = rail.find(accountId) }

    Connections {
        target: falcon
        function onPushText(text, alert) { feed.add(text, alert) }
        function onConnectionFailed(message) { feed.add("connection failed: " + message, true) }
        function onConnected() { feed.add("connected to " + falcon.engineAddress + " as " + falcon.roleLabel, false) }
        function onDisconnected() { feed.add("disconnected", true) }
    }

    Component.onCompleted: {
        if (autoConnect && falcon.defaultClientId.length > 0)
            falcon.connectTo(falcon.defaultHost, falcon.defaultPort, falcon.defaultClientId, falcon.defaultClientKey, falcon.defaultPlaintext, falcon.defaultCaCert)
    }

    // =========================================================================================
    header: Rectangle {
        implicitHeight: 52
        color: Theme.surface
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.space4; anchors.rightMargin: Theme.space4
            spacing: Theme.space4

            // identity
            RowLayout {
                spacing: Theme.space2
                Rectangle { width: 8; height: 18; radius: 2; color: falcon.isConnected ? Theme.roleTint(falcon.role) : Theme.accent }
                Label { text: "FALCON"; color: Theme.text; font.pixelSize: Theme.fontMedium; font.bold: true; font.letterSpacing: 1.4 }
            }
            Rectangle { width: 1; height: 22; color: Theme.border }

            // primary navigation: underlined tabs, only here
            TabBar {
                id: tabs
                visible: falcon.isConnected
                Layout.preferredWidth: contentWidth
                background: null
                currentIndex: root.currentView
                onCurrentIndexChanged: root.currentView = currentIndex
                Repeater {
                    model: root.views
                    delegate: TabButton {
                        required property var modelData
                        text: modelData
                        width: implicitWidth + 20
                        font.pixelSize: Theme.fontBody
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // indicators: pulse until addressed (pings, deadlines reached, task completed, failures, violations, offers)
            Row {
                spacing: Theme.space2
                Repeater {
                    model: falcon.indicators
                    delegate: StatePill {
                        required property var modelData
                        text: modelData.text
                        pulse: true
                        tint: modelData.kind === "task_completed" ? Theme.ok
                            : (modelData.kind === "unaddressed_ping" || modelData.kind === "offer") ? Theme.warn
                            : modelData.kind === "session" ? Theme.textDim
                            : Theme.danger
                    }
                }
            }

            // who you are, and the link
            Label {
                visible: falcon.isConnected
                text: Theme.roleLabel(falcon.role) + "  ·  account " + falcon.accountId + "  ·  pc " + falcon.pcId + (falcon.departmentId ? "  ·  dept " + falcon.departmentId : "")
                color: Theme.textDim; font.pixelSize: Theme.fontSmall; font.family: Theme.mono
            }
            Label { visible: falcon.isConnected; text: falcon.engineAddress; color: Theme.textFaint; font.pixelSize: Theme.fontSmall; font.family: Theme.mono }
            Btn { visible: falcon.isConnected; text: "Disconnect"; onClicked: falcon.disconnect() }
        }
    }

    // =========================================================================================
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // consequences, full width, with the answer one click away
        Banner {
            Layout.fillWidth: true
            tint: Theme.danger
            text: falcon.superUserBanner ? "SUPER USER IN CHARGE — you are inside another user's view"
                : falcon.blocked ? "BLOCKED — your PC is occupied by " + falcon.blockedBy + " (traversal in progress)"
                : ""
            Btn { visible: falcon.superUserBanner; text: "Extend"; onClicked: falcon.call("hierarchy.extend_session", {session_id: falcon.session.session_id}, function(ok, r) { root.notify(ok ? "deadline now " + r.deadline_at : r.message, !ok) }) }
            Btn { visible: falcon.superUserBanner; text: "End session"; danger: true; onClicked: falcon.call("hierarchy.end_session", {session_id: falcon.session.session_id}, function(ok, r) { root.notify(ok ? "session ended" : r.message, !ok) }) }
            Btn { visible: falcon.blocked; text: "Claim native session"; onClicked: falcon.call("hierarchy.claim_native", {}, function(ok, r) { root.notify(ok ? (r.blocked ? "still blocked" : "claimed native session") : r.message, !ok) }) }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            handle: Rectangle { implicitWidth: 1; color: Theme.border }

            HierarchyRail {
                id: rail
                objectName: "hierarchyRail"
                SplitView.preferredWidth: Theme.railWidth
                SplitView.minimumWidth: 240
            }

            ColumnLayout {
                SplitView.fillWidth: true
                spacing: 0

                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: falcon.isConnected ? root.currentView + 1 : 0
                    ConnectView { objectName: "connectView" }
                    HierarchyView { objectName: "hierarchyView" }
                    TasksView { objectName: "tasksView" }
                    FlowsView { objectName: "flowsView" }
                    ControlView { objectName: "controlView" }
                    AssistanceView { objectName: "assistanceView" }
                    ReportsView { objectName: "reportsView" }
                }

                // the live feed: pushes and command results, pinned, proportional and capped
                PushFeed {
                    id: feed
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(220, Math.round(root.height * 0.24))
                }
            }
        }
    }

    // =========================================================================================
    footer: Rectangle {
        implicitHeight: 26
        color: Theme.surface
        Rectangle { width: parent.width; height: 1; color: Theme.border }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.space4; anchors.rightMargin: Theme.space4
            spacing: Theme.space2
            Rectangle {
                width: 7; height: 7; radius: 4
                color: falcon.isConnected ? Theme.ok : Theme.danger
                SequentialAnimation on opacity {
                    running: falcon.isConnected; loops: Animation.Infinite
                    NumberAnimation { to: 0.35; duration: 1400; easing.type: Easing.InOutQuad }
                    NumberAnimation { to: 1.0; duration: 1400; easing.type: Easing.InOutQuad }
                }
            }
            Label { text: falcon.isConnected ? "Connected to " + falcon.engineAddress : "Not connected"; color: Theme.textDim; font.pixelSize: Theme.fontSmall; elide: Text.ElideRight; Layout.fillWidth: true }
            Label { visible: falcon.isConnected; text: falcon.sessionText; color: falcon.traversing ? Theme.warn : Theme.textFaint; font.pixelSize: Theme.fontSmall; font.family: Theme.mono }
            Label { visible: !!root.selected; text: root.selected ? "selected: " + root.selected.name + " (pc " + root.selected.pc_id + ")" : ""; color: Theme.accent; font.pixelSize: Theme.fontSmall; font.family: Theme.mono }
        }
    }
}
