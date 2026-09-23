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
    function show(key) {
        var i = rail.indexOfKey(key)
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
                Layout.preferredWidth: Theme.railWidth
                Layout.fillHeight: true
                role: falcon.role
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

                Rectangle {
                    id: sheet
                    anchors.fill: parent
                    radius: Theme.radiusMd
                    color: Theme.pane
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
                                visible: shell.viewKey === "overview"
                            }

                            HomeView {
                                id: home
                                objectName: "hierarchyRail"      // the hierarchy tree lives here now
                                anchors.fill: parent
                                visible: shell.viewKey === "hierarchy"
                            }

                            // ported one at a time; mounted so their state and tests keep working
                            Item {
                                width: 0
                                height: 0
                                clip: true
                                TasksView { objectName: "tasksView"; width: 600; height: 400 }
                                FlowsView { objectName: "flowsView"; width: 600; height: 400 }
                                ControlView { objectName: "controlView"; width: 600; height: 400 }
                                AssistanceView { objectName: "assistanceView"; width: 600; height: 400 }
                                ReportsView { objectName: "reportsView"; width: 600; height: 400 }
                            }
                            // the views not yet rebuilt on the new kit keep their own surface
                            Item {
                                anchors.fill: parent
                                visible: shell.viewKey !== "hierarchy" && shell.viewKey !== "overview"
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 12
                                    Rectangle {
                                        width: 52; height: 52; radius: Theme.radiusLg
                                        color: Theme.ground
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        Icon { anchors.centerIn: parent; name: "automation"; color: Theme.faint; size: 23 }
                                    }
                                    Txt {
                                        text: "Being rebuilt on the new kit"
                                        color: Theme.dim
                                        font.pixelSize: Theme.fRow
                                        font.weight: Font.DemiBold
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                    Txt {
                                        text: "Hierarchy is done. This one is next."
                                        color: Theme.faint
                                        font.pixelSize: Theme.fBody
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                }
                            }
                        }
                    }

                    // state, as a floating pill over the sheet -- the frame never changes
                    Rectangle {
                        id: statePill
                        visible: falcon.superUserBanner || falcon.blocked || falcon.traversing
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
