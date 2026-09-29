import QtQuick
import "."

// The sider. One entry per area, and it is the only navigation in the console.
Rectangle {
    id: root
    property var entries: []                 // [{ key, icon, label, badge }]
    property string current: ""
    property bool collapsed: false
    signal picked(string key)

    implicitWidth: collapsed ? 64 : 208
    color: Theme.surface
    Behavior on implicitWidth { NumberAnimation { duration: Theme.durBase; easing.type: Easing.OutCubic } }

    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.split }

    Item {
        id: brand
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 48
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.split }
        Row {
            anchors.left: parent.left
            anchors.leftMargin: Theme.s4
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.s2
            Rectangle {
                width: 18; height: 18; radius: Theme.radiusSm; color: Theme.primary
                anchors.verticalCenter: parent.verticalCenter
            }
            Txt { text: "Falcon"; strong: true; visible: !root.collapsed; anchors.verticalCenter: parent.verticalCenter }
        }
    }

    Column {
        anchors.top: brand.bottom
        anchors.topMargin: Theme.s2
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 2

        Repeater {
            model: root.entries
            delegate: Rectangle {
                required property var modelData
                width: parent.width - Theme.s2
                x: Theme.s1
                height: 36
                radius: Theme.radius
                readonly property bool on: root.current === modelData.key
                color: on ? Theme.primarySoft : hover.hovered ? Theme.hover : "transparent"

                Row {
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.s3
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Theme.s3
                    Icon {
                        name: modelData.icon
                        size: 16
                        color: parent.parent.on ? Theme.primary : Theme.mid
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Txt {
                        visible: !root.collapsed
                        text: modelData.label
                        tone: parent.parent.on ? "accent" : "ink"
                        strong: parent.parent.on
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                Txt {
                    visible: !root.collapsed && (modelData.badge || 0) > 0
                    anchors.right: parent.right
                    anchors.rightMargin: Theme.s3
                    anchors.verticalCenter: parent.verticalCenter
                    text: String(modelData.badge || "")
                    tone: "danger"
                    font.pixelSize: Theme.fSmall
                    strong: true
                }
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.picked(modelData.key) }
            }
        }
    }
}
