import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The persistent surface the design asks for on every screen: who you are, the session you
// occupy, the red "Super User in charge" banner, the BLOCKED marker, and the pulsing indicators
// (unaddressed pings, deadlines reached, task completed, flow failures, violations, offers).
Rectangle {
    id: bar
    height: falcon.superUserBanner || falcon.blocked ? 64 : 40
    color: "#2b2d31"

    property bool pulseOn: true
    Timer { interval: 700; running: falcon.indicators.length > 0; repeat: true; onTriggered: bar.pulseOn = !bar.pulseOn }

    function indicatorColor(kind) {
        switch (kind) {
        case "deadline_reached": case "flow_failed": case "violation": return "#ff6b6b"
        case "task_completed": return "#6bff8a"
        case "unaddressed_ping": case "offer": return "#ffd166"
        case "blocked": return "#ff6b6b"
        default: return "#9fd0ff"
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            spacing: 16
            Label { text: falcon.roleLabel; font.bold: true; color: "white" }
            Label { visible: falcon.isConnected; color: "#c8c8c8"
                    text: "account " + falcon.accountId + " · pc " + falcon.pcId + (falcon.departmentId ? " · dept " + falcon.departmentId : "") }
            Label { visible: falcon.isConnected; color: "#9fd0ff"; text: falcon.sessionText }
            Item { Layout.fillWidth: true }
            Row {
                spacing: 12
                Repeater {
                    model: falcon.indicators
                    delegate: Row {
                        required property var modelData
                        spacing: 4
                        Rectangle { width: 10; height: 10; radius: 5; anchors.verticalCenter: parent.verticalCenter
                                    color: bar.pulseOn ? bar.indicatorColor(modelData.kind) : "#555" }
                        Label { text: modelData.text; color: bar.indicatorColor(modelData.kind); font.bold: true }
                    }
                }
            }
        }

        // RED BANNER (Super User inside another user's view) / BLOCKED (our PC is occupied)
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 24
            visible: falcon.superUserBanner || falcon.blocked
            color: "#b00020"
            Label {
                anchors.centerIn: parent
                color: "white"; font.bold: true
                text: falcon.superUserBanner ? "SUPER USER IN CHARGE — you are inside another user's view"
                                             : "BLOCKED — your PC is occupied by " + falcon.blockedBy + " (traversal in progress)"
            }
        }
    }
}
