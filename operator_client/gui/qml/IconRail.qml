import QtQuick
import "."

// The rail: icons with labels, on the frame itself. Its entries come from the role, in one place --
// Super User is not the Admin rail with things removed, it is its own list.
Item {
    id: root

    property string role: "admin"
    property int current: 0
    signal picked(int index)

    readonly property var adminNav: [
        { key: "hierarchy",  icon: "hierarchy",  label: "Hierarchy" },
        { key: "tasks",      icon: "tasks",      label: "Tasks" },
        { key: "flows",      icon: "flows",      label: "Flows" },
        { key: "automation", icon: "automation", label: "Automation" },
        { key: "actions",    icon: "play",       label: "Actions" },
        { key: "assistance", icon: "assistance", label: "Assistance" },
        { key: "reports",    icon: "reports",    label: "Reports" }
    ]
    // governance, not operation: no Automation, no Actions -- that combo is reached by entering an
    // Admin. It leads with Overview because the Super User's first job is to see the whole system.
    readonly property var superNav: [
        { key: "overview",   icon: "pulse",      label: "Overview" },
        { key: "hierarchy",  icon: "hierarchy",  label: "Hierarchy" },
        { key: "views",      icon: "eye",        label: "Views" },
        { key: "reports",    icon: "reports",    label: "Reports" },
        { key: "updates",    icon: "shield",     label: "Updates" },
        { key: "tasks",      icon: "tasks",      label: "Tasks" },
        { key: "flows",      icon: "flows",      label: "Flows" },
        { key: "assistance", icon: "assistance", label: "Assistance" }
    ]
    readonly property var nav: role === "super_user" ? superNav : adminNav
    readonly property string currentKey: current < nav.length ? nav[current].key : ""

    function indexOfKey(key) {
        for (var i = 0; i < nav.length; i++) if (nav[i].key === key) return i
        return -1
    }

    implicitWidth: Theme.railWidth

    Column {
        anchors.top: parent.top
        anchors.topMargin: Theme.s2
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 6

        Repeater {
            model: root.nav
            delegate: Rectangle {
                required property var modelData
                required property int index
                readonly property bool on: index === root.current

                width: 56
                height: 48
                radius: Theme.radiusMd
                color: on ? Qt.rgba(1, 1, 1, 0.18) : area.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent"
                Behavior on color { ColorAnimation { duration: Theme.durFast } }

                Column {
                    anchors.centerIn: parent
                    spacing: 3
                    Icon {
                        name: modelData.icon
                        color: on ? "#ffffff" : Qt.rgba(1, 1, 1, 0.68)
                        size: 20
                        weight: 1.6
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                    Txt {
                        text: modelData.label
                        color: on ? "#ffffff" : Qt.rgba(1, 1, 1, 0.68)
                        font.pixelSize: 10
                        font.weight: Font.Medium
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
                MouseArea {
                    id: area
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.picked(index)
                }
            }
        }
    }

    // who you are, at the foot of the rail
    Column {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.s3
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 4

        Rectangle {
            width: 34
            height: 34
            radius: Theme.radiusMd
            color: "#ffffff"
            anchors.horizontalCenter: parent.horizontalCenter
            Txt {
                anchors.centerIn: parent
                text: falcon.role === "super_user" ? "SU" : "AD"
                color: Theme.frameSolid
                font.pixelSize: 12
                font.weight: Font.Bold
            }
        }
        Txt {
            text: Theme.roleLabel(falcon.role)
            color: Qt.rgba(1, 1, 1, 0.68)
            font.pixelSize: 10
            font.weight: Font.Medium
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }
}
