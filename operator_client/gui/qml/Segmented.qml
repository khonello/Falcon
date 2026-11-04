import QtQuick
import "."

// A small switch between views of the same thing, or between a few filters of one list. Options are
// [{value, label, icon?}] or plain strings. `block` stretches the segments across the width.
// Drawn as the concept's antd Segmented: a 2px track in the page's background, options 0 7px (0 11px at the
// normal size) in 13px label ink, the picked one on the elevated background in full ink.
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
    readonly property int pad: small ? 7 : 11
    implicitWidth: strip.implicitWidth + 4
    implicitHeight: small ? Theme.controlSm : Theme.control
    opacity: enabled ? 1 : 0.5

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSm
        color: Theme.bg

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
                                      : content.implicitWidth + 2 * root.pad
                    height: root.height - 4
                    radius: root.small ? 1 : 2
                    color: on ? Theme.elevated : area.containsMouse ? Theme.fillHover : "transparent"
                    Behavior on color { ColorAnimation { duration: Theme.durFast } }

                    Row {
                        id: content
                        anchors.centerIn: parent
                        spacing: 6
                        Icon {
                            visible: !!seg.modelData.icon
                            name: seg.modelData.icon || ""
                            size: 13
                            color: seg.on || area.containsMouse ? Theme.text : Theme.textLabel
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Txt {
                            visible: seg.modelData.label !== undefined && seg.modelData.label !== ""
                            text: seg.modelData.label || ""
                            // a block switch narrower than its labels cuts them short rather than spilling out
                            width: root.block ? Math.min(implicitWidth, seg.width - 2 * root.pad - (seg.modelData.icon ? 19 : 0)) : implicitWidth
                            color: seg.on || area.containsMouse ? Theme.text : Theme.textLabel
                            font.pixelSize: Theme.fBody
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
