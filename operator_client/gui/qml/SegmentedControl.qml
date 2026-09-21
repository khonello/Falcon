import QtQuick
import QtQuick.Controls
import "."

// A choice *within* a page: one recessed track, the active segment tinted and underlined in its
// own colour. Never the same shape as the header tabs, so the two levels never look alike.
// segments: [{ text: "Pending", count: 3 }, { text: "Force", tint: Theme.danger }]
Item {
    id: root
    property var segments: []
    property int currentIndex: 0
    property color tint: Theme.accent

    function tintOf(index) {
        var s = root.segments[index]
        return (s && s.tint !== undefined) ? s.tint : root.tint
    }

    implicitHeight: 28
    implicitWidth: track.implicitWidth

    Rectangle {
        id: track
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.canvas
        border.width: 1
        border.color: Theme.border
        implicitWidth: row.implicitWidth + 4

        Row {
            id: row
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 2
            spacing: 2

            Repeater {
                model: root.segments
                delegate: Rectangle {
                    required property int index
                    required property var modelData
                    readonly property bool active: root.currentIndex === index
                    readonly property color segTint: root.tintOf(index)

                    height: root.height - 4
                    width: label.implicitWidth + 26
                    radius: Theme.radius - 1
                    color: active ? Theme.wash(segTint, 0.18) : (hover.hovered ? Qt.rgba(1, 1, 1, 0.05) : "transparent")
                    border.width: active ? 1 : 0
                    border.color: Theme.wash(segTint, 0.5)
                    Behavior on color { ColorAnimation { duration: Theme.durationFast } }

                    Rectangle {
                        visible: active
                        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                        anchors.leftMargin: 5; anchors.rightMargin: 5
                        height: 2; radius: 1
                        color: segTint
                    }
                    Row {
                        id: label
                        anchors.centerIn: parent
                        spacing: 6
                        Label {
                            text: modelData.text
                            color: active ? segTint : Theme.textDim
                            font.pixelSize: Theme.fontBody
                            font.bold: active
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Rectangle {
                            visible: modelData.count !== undefined
                            anchors.verticalCenter: parent.verticalCenter
                            width: countLabel.implicitWidth + 10; height: 16; radius: 8
                            color: active ? Theme.wash(segTint, 0.3) : Qt.rgba(1, 1, 1, 0.06)
                            Label {
                                id: countLabel
                                anchors.centerIn: parent
                                text: modelData.count !== undefined ? modelData.count : ""
                                color: active ? Theme.text : Theme.textFaint
                                font.pixelSize: Theme.fontTiny
                                font.bold: true
                            }
                        }
                    }
                    HoverHandler { id: hover }
                    TapHandler { onTapped: root.currentIndex = index }
                }
            }
        }
    }
}
