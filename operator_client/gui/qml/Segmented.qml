import QtQuick
import "."

// A small switch between views of the same thing, or between a few filters of one list. Options are
// [{value, label, icon?}] or plain strings. `block` stretches the segments across the width.
Item {
    id: root
    property var options: []
    property var value: null
    property bool small: true
    property bool block: false
    property bool enabled: true
    signal picked(var value)

    readonly property var items: options.map(function (o) {
        return typeof o === "object" ? o : { value: o, label: String(o) }
    })
    implicitWidth: strip.implicitWidth + 4
    implicitHeight: small ? Theme.controlSm : Theme.control
    opacity: enabled ? 1 : 0.5

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSm
        color: Theme.surface3

        Row {
            id: strip
            x: 2
            anchors.verticalCenter: parent.verticalCenter
            spacing: 0

            Repeater {
                model: root.items
                delegate: Rectangle {
                    id: seg
                    required property var modelData
                    required property int index
                    readonly property bool on: modelData.value === root.value

                    width: root.block ? (root.width - 4) / root.items.length
                                      : content.implicitWidth + 2 * (root.small ? 9 : 12)
                    height: root.height - 4
                    radius: Theme.radiusSm - 1
                    color: on ? Theme.surface : "transparent"
                    border.width: on && Theme.dark ? 1 : 0
                    border.color: Theme.border
                    Behavior on color { ColorAnimation { duration: Theme.durFast } }

                    Row {
                        id: content
                        anchors.centerIn: parent
                        spacing: 5
                        Icon {
                            visible: !!seg.modelData.icon
                            name: seg.modelData.icon || ""
                            size: 13
                            color: seg.on ? Theme.text : Theme.text3
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Txt {
                            visible: seg.modelData.label !== undefined && seg.modelData.label !== ""
                            text: seg.modelData.label || ""
                            color: seg.on ? Theme.text : (area.containsMouse ? Theme.text : Theme.text2)
                            font.pixelSize: root.small ? Theme.fSmall : Theme.fBody
                            font.weight: seg.on ? Font.Medium : Font.Normal
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    MouseArea {
                        id: area
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: root.enabled
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { root.value = seg.modelData.value; root.picked(seg.modelData.value) }
                    }
                }
            }
        }
    }
}
