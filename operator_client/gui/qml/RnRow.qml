import QtQuick
import "."

// A row of a list to pick from (rn-row): an icon in a circle or a checkbox, what it is, a line on it, and a tick when picked.
Rectangle {
    id: root
    property bool on: false
    property string icon: ""
    property bool check: false                  // a checkbox in place of the icon
    property string title: ""
    property string desc: ""
    property bool mono: false
    signal picked()
    width: parent ? parent.width : 0
    height: Math.max(tc.height, icon !== "" ? 28 : 16) + 22
    radius: 8
    color: on ? Theme.mix(Theme.accent, Theme.surface2, 0.08) : Theme.surface2
    border.width: 1
    border.color: on ? Theme.accent : ma.containsMouse ? Theme.borderStrong : "transparent"
    readonly property real tx: root.icon !== "" ? 53 : root.check ? 41 : 13
    Rectangle { visible: root.icon !== ""; x: 13; anchors.verticalCenter: parent.verticalCenter; width: 28; height: 28; radius: 14; color: Theme.surface3
                Icon { anchors.centerIn: parent; name: root.icon; size: 13; color: Theme.text2 } }
    Check { visible: root.check; x: 13; anchors.verticalCenter: parent.verticalCenter; checked: root.on; controlled: true; enabled: false; opacity: 1 }
    Column {
        id: tc
        x: root.tx; anchors.verticalCenter: parent.verticalCenter
        width: parent.width - x - 36
        spacing: 1
        Txt { width: parent.width; text: root.title; mono: root.mono; font.pixelSize: 13; font.weight: Font.DemiBold }
        Txt { visible: root.desc !== ""; width: parent.width; text: root.desc; color: Theme.text3; font.pixelSize: 13 }
    }
    Icon { visible: root.on && !root.check; anchors.right: parent.right; anchors.rightMargin: 13; anchors.verticalCenter: parent.verticalCenter; name: "check"; size: 13; color: Theme.accent }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.picked() }
}
