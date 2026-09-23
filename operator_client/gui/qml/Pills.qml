import QtQuick
import "."

// The body's filter: pills with counts. The sidebar says what the body is a list of; these filter
// that list on a different axis, never repeating it.
Flow {
    id: root
    property var model: []                  // [{label, count}]
    property int current: 0
    signal picked(int index)

    spacing: 7

    Repeater {
        model: root.model
        delegate: Rectangle {
            required property var modelData
            required property int index
            readonly property bool on: index === root.current

            height: 30
            width: inner.implicitWidth + 26
            radius: Theme.pill
            color: on ? Theme.select : Theme.ground

            Row {
                id: inner
                anchors.centerIn: parent
                spacing: 7

                Txt {
                    text: modelData.label
                    color: on ? "#ffffff" : Theme.dim
                    font.pixelSize: Theme.fBody
                    font.weight: Font.DemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
                Rectangle {
                    visible: modelData.count !== undefined && String(modelData.count) !== ""
                    height: 17
                    width: count.implicitWidth + 12
                    radius: Theme.pill
                    color: on ? Qt.rgba(1, 1, 1, 0.22) : Theme.line
                    anchors.verticalCenter: parent.verticalCenter
                    Txt {
                        id: count
                        anchors.centerIn: parent
                        text: modelData.count === undefined ? "" : String(modelData.count)
                        color: on ? "#ffffff" : Theme.dim
                        font.pixelSize: Theme.fSmall
                        font.weight: Font.DemiBold
                    }
                }
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.picked(index)
            }
        }
    }
}
