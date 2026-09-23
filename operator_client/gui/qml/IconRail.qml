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
        { icon: "hierarchy",  label: "Hierarchy" },
        { icon: "tasks",      label: "Tasks" },
        { icon: "flows",      label: "Flows" },
        { icon: "automation", label: "Automation" },
        { icon: "play",       label: "Actions" },
        { icon: "assistance", label: "Assistance" },
        { icon: "reports",    label: "Reports" }
    ]
    // governance, not operation: no Automation, no Actions -- that combo is reached by entering an Admin
    readonly property var superNav: [
        { icon: "hierarchy",  label: "Hierarchy" },
        { icon: "eye",        label: "Views" },
        { icon: "reports",    label: "Reports" },
        { icon: "shield",     label: "Updates" },
        { icon: "tasks",      label: "Tasks" },
        { icon: "flows",      label: "Flows" },
        { icon: "assistance", label: "Assistance" }
    ]
    readonly property var nav: role === "super_user" ? superNav : adminNav

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
