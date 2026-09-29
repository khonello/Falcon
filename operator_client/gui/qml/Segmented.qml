import QtQuick
import "."

// A SMALL SWITCH BETWEEN VIEWS OF THE SAME THING. Not navigation and not a filter: the data does not
// change, only how you are looking at it. Two or three words per segment, never more.
Item {
    id: root
    property var options: []              // [{value, label}]
    property var value: null
    signal picked(var value)

    implicitWidth: strip.implicitWidth + 4
    implicitHeight: Theme.control

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.fillStrong

        Row {
            id: strip
            anchors.centerIn: parent
            spacing: 0

            Repeater {
                model: root.options
                delegate: Rectangle {
                    required property var modelData
                    readonly property bool on: modelData.value === root.value

                    width: label.implicitWidth + 2 * Theme.s4
                    height: Theme.control - 4
                    radius: Theme.radiusSm
                    color: on ? Theme.surface : hover.hovered ? Qt.rgba(0, 0, 0, 0.04) : "transparent"
                    Behavior on color { ColorAnimation { duration: Theme.durFast } }

                    Txt {
                        id: label
                        anchors.centerIn: parent
                        text: modelData.label
                        tone: parent.on ? "ink" : "mid"
                        strong: parent.on
                        font.pixelSize: Theme.fSmall
                    }
                    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: { root.value = modelData.value; root.picked(modelData.value) } }
                }
            }
        }
    }
}
