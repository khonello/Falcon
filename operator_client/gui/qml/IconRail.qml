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
    // AREAS, NOT FEATURES (design/TABS.md, settled 25 Sep 2026). Five entries, each named after the
    // question a person is asking rather than after a module, and the same noun means the same thing
    // at every level -- Work is Work whether you see three departments or one.
    //
    //   Must see   what needs me right now          Record   what happened, and who was where
    //   Authority  who governs what, and where nobody does
    //   Rollout    what version is where, and what is stuck
    //   Work       what is moving through the organisation (Assistance folded in, watched not started)
    //
    // A department page is INSIDE Authority: going there does not change the rail, only the crumb
    // and the title. `adminNav` keeps its old shape deliberately -- the Admin rail is level 3 and is
    // deferred (TABS.md issue 8).
    readonly property var superNav: [
        { key: "mustsee",   icon: "pulse",     label: "Must see" },
        { key: "authority", icon: "hierarchy", label: "Authority" },
        { key: "rollout",   icon: "shield",    label: "Rollout" },
        { key: "record",    icon: "eye",       label: "Record" },
        { key: "work",      icon: "tasks",     label: "Work" }
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
