import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    // Opens full screen: app.fit_to_screen() pins the window to the screen's work area as a fixed
    // size once the native frame exists. Title bar offers minimize and close only; no resize frame.
    width: 1280
    height: 820
    flags: Qt.Window | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint | Qt.CustomizeWindowHint
    visible: true
    title: "Falcon Operator Client" + (falcon.isConnected ? "  —  " + falcon.roleLabel + " @ " + falcon.engineAddress : "")
    color: "#1e1f22"
    // Fusion honours the palette; a dark one keeps every control readable on the dark ground.
    palette {
        window: "#1e1f22"; windowText: "#dddddd"; base: "#26282c"; alternateBase: "#232529"; text: "#dddddd"
        button: "#3a3d42"; buttonText: "#eeeeee"; highlight: "#3a4a6a"; highlightedText: "#ffffff"
        placeholderText: "#888888"; light: "#4a4d52"; mid: "#2b2d31"; dark: "#151618"; shadow: "#000000"; brightText: "#ff8a80"
    }

    property int currentView: 0
    readonly property var views: [
        { name: "Hierarchy", roles: ["super_user", "admin"] },
        { name: "Tasks", roles: ["super_user", "admin"] },
        { name: "Flows", roles: ["super_user", "admin"] },
        { name: "Automation", roles: ["super_user", "admin"] },
        { name: "Assistance", roles: ["super_user", "admin"] },
        { name: "Reports", roles: ["super_user", "admin"] }
    ]

    function notify(text, alert) { feed.add(text, alert) }

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

    // --- persistent status surface: identity, session, RED BANNER, BLOCKED, pulsing indicators
    header: StatusBar { }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // navigation
            Rectangle {
                Layout.preferredWidth: 170
                Layout.fillHeight: true
                color: "#26282c"
                visible: falcon.isConnected
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 4
                    Repeater {
                        model: root.views
                        delegate: Button {
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            text: modelData.name
                            flat: root.currentView !== index
                            highlighted: root.currentView === index
                            onClicked: root.currentView = index
                        }
                    }
                    Item { Layout.fillHeight: true }
                    Button { Layout.fillWidth: true; text: "Disconnect"; flat: true; onClicked: falcon.disconnect() }
                }
            }

            // content
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
        }

        // live push feed
        PushFeed { id: feed; Layout.fillWidth: true; Layout.preferredHeight: 150 }
    }
}
