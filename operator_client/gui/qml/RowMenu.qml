import QtQuick
import QtQuick.Controls.Basic
import "."

// THE ACTS ON ONE ROW, without opening it. A table row carries a quiet "more" button; this is what it
// opens. Destructive entries sit last, under a divider, and say so in red -- the same rule the footer
// of a drawer follows.
Item {
    id: root
    property var items: []                // [{key, label, danger, divided, enabled}]
    signal chose(string key)

    implicitWidth: Theme.controlSm
    implicitHeight: Theme.controlSm

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSm
        color: hov.containsMouse || pop.opened ? Theme.hover : "transparent"
        Icon {
            anchors.centerIn: parent
            name: "more"
            size: 15
            color: hov.containsMouse || pop.opened ? Theme.ink : Theme.quiet
        }
        MouseArea {
            id: hov
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: pop.opened ? pop.close() : pop.open()
        }
    }

    Popup {
        id: pop
        x: root.width - width
        y: root.height + 4
        width: 180
        padding: Theme.s1
        height: list.implicitHeight + 2 * Theme.s1

        background: Rectangle {
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.split
            MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true }
        }

        Column {
            id: list
            width: parent.width

            Repeater {
                model: root.items
                delegate: Item {
                    required property var modelData
                    width: list.width
                    height: modelData.divided ? 31 + Theme.s1 * 2 : 31

                    Rectangle {
                        anchors.top: parent.top
                        width: parent.width
                        height: 1
                        visible: !!modelData.divided
                        color: Theme.split
                    }
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 31
                        radius: Theme.radiusSm
                        color: mh.containsMouse ? (modelData.danger ? Theme.dangerSoft : Theme.hover)
                                                : "transparent"
                        Txt {
                            anchors.left: parent.left
                            anchors.leftMargin: Theme.s2
                            anchors.right: parent.right
                            anchors.rightMargin: Theme.s2
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.label
                            tone: modelData.danger ? "danger" : "ink"
                            font.pixelSize: Theme.fSmall
                            opacity: modelData.enabled === false ? 0.4 : 1
                        }
                        MouseArea {
                            id: mh
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: modelData.enabled !== false
                            cursorShape: Qt.PointingHandCursor
                            onClicked: { pop.close(); root.chose(String(modelData.key)) }
                        }
                    }
                }
            }
        }
    }
}
