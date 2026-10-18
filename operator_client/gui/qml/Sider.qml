import QtQuick
import "."

// THE SIDER. Who this console is for at the top, the areas in their groups, and at the foot the
// person at the console -- and, inside an Admin's console, Leave console. Beside an area, how many
// of its things need a person: red when someone must act, a pulsing pill for an unanswered ping.
Rectangle {
    id: root
    signal leave()
    width: 216
    color: Theme.surface
    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.border }

    // who the console is for
    Row {
        id: org
        x: 16; y: 16
        spacing: 9
        Rectangle {
            width: 26; height: 26; radius: 5
            color: Theme.text
            anchors.verticalCenter: parent.verticalCenter
            Icon { anchors.centerIn: parent; name: "logo"; size: 14; color: Theme.surface; weight: 2 }
        }
        Column {
            width: 150
            anchors.verticalCenter: parent.verticalCenter
            Txt { text: "Falcon"; font.weight: Font.DemiBold; width: parent.width }
            Txt {
                width: parent.width
                color: Theme.text3
                font.pixelSize: 11
                text: Nav.boss ? "Head office" + (Nav.departments ? " · " + Theme.many(Nav.departments, "department") : "")
                               : (Nav.deptName || falcon.roleLabel)
            }
        }
    }

    Flickable {
        id: list
        anchors.top: org.bottom
        anchors.topMargin: 8
        anchors.bottom: foot.top
        width: parent.width - 1
        contentHeight: groups.height
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: groups
            x: 8
            width: parent.width - 16
            Repeater {
                model: Nav.menu
                delegate: Column {
                    required property var modelData
                    width: groups.width
                    Txt {
                        text: modelData[0].toUpperCase()
                        color: Theme.text4
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.66
                        leftPadding: 10
                        topPadding: 14
                        bottomPadding: 4
                    }
                    Repeater {
                        model: modelData[1]
                        delegate: Rectangle {
                            id: item
                            required property var modelData
                            readonly property string key: modelData[0]
                            readonly property bool on: Nav.page === key || Nav.parentOf(Nav.page) === key
                            readonly property var c: Nav.counts[key]
                            objectName: "nav_" + key
                            width: groups.width
                            height: 32
                            radius: 5
                            color: on ? Theme.accentSoft : area.containsMouse ? Theme.surface3 : "transparent"

                            Row {
                                x: 10
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 10
                                Icon {
                                    name: item.modelData[2]
                                    size: 15
                                    color: item.on ? Theme.accent : area.containsMouse ? Theme.text : Theme.text2
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Txt {
                                    text: item.modelData[1]
                                    color: item.on ? Theme.accent : area.containsMouse ? Theme.text : Theme.text2
                                    font.weight: item.on ? Font.Medium : Font.Normal
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                            Rectangle {
                                id: pill
                                visible: !!item.c && item.c.n > 0
                                anchors.right: parent.right
                                anchors.rightMargin: 10
                                anchors.verticalCenter: parent.verticalCenter
                                readonly property bool pulse: !!item.c && item.c.pulse
                                width: cnt.implicitWidth + (pulse ? 12 : 0)
                                height: 18
                                radius: 9
                                color: pulse ? Theme.crit : "transparent"
                                Txt {
                                    id: cnt
                                    anchors.centerIn: parent
                                    mono: true
                                    font.pixelSize: 11
                                    font.weight: pill.pulse || (item.c && item.c.hot) ? Font.DemiBold : Font.Normal
                                    color: pill.pulse ? Theme.inverse : (item.c && item.c.hot) ? Theme.crit : Theme.text3
                                    elide: Text.ElideNone
                                    text: item.c ? (item.c.n > 999 ? "999+" : Theme.fmt(item.c.n)) : ""
                                }
                                // unanswered: bright and pulsing until everything is answered
                                Rectangle {
                                    visible: pill.pulse
                                    anchors.centerIn: parent
                                    width: parent.width; height: parent.height; radius: 9
                                    color: "transparent"
                                    border.width: 2
                                    border.color: Theme.alpha(Theme.crit, 0.5)
                                    SequentialAnimation on scale {
                                        running: pill.pulse
                                        loops: Animation.Infinite
                                        NumberAnimation { from: 1; to: 1.35; duration: 800 }
                                        NumberAnimation { from: 1.35; to: 1; duration: 800 }
                                    }
                                    SequentialAnimation on opacity {
                                        running: pill.pulse
                                        loops: Animation.Infinite
                                        NumberAnimation { from: 1; to: 0; duration: 800 }
                                        NumberAnimation { from: 0; to: 1; duration: 800 }
                                    }
                                }
                            }
                            MouseArea {
                                id: area
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Nav.go(item.key)
                            }
                        }
                    }
                }
            }
        }
    }

    // the person at this console
    Column {
        id: foot
        anchors.bottom: parent.bottom
        width: parent.width - 1
        Rectangle { width: parent.width; height: 1; color: Theme.border }
        Item {
            width: parent.width
            height: inner.height + 20
            Column {
                id: inner
                x: 10; y: 10
                width: parent.width - 20
                spacing: 8
                Btn {
                    visible: Nav.inside
                    width: parent.width
                    danger: true
                    iconName: "logout"
                    text: "Leave console"
                    onClicked: root.leave()
                }
                Row {
                    spacing: 8
                    Rectangle {
                        width: 24; height: 24; radius: 4
                        color: Theme.surface3
                        anchors.verticalCenter: parent.verticalCenter
                        Txt { anchors.centerIn: parent; text: falcon.role === "super_user" ? "SU" : Theme.initials(Nav.myName || falcon.roleLabel); font.pixelSize: 11; font.weight: Font.DemiBold }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        Txt { text: falcon.role === "super_user" ? "Super User" : (Nav.myName || falcon.roleLabel); font.weight: Font.Medium; font.pixelSize: Theme.fSmall }
                        Txt { text: falcon.defaultClientId || ""; mono: true; color: Theme.text3; font.pixelSize: 11 }
                    }
                }
            }
        }
    }
}
