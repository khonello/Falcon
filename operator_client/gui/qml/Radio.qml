import QtQuick
import "."

// MUTUALLY EXCLUSIVE, AND ALL OF IT ON SCREEN. A Select hides the options behind a click; a Radio
// group shows them. Use it when there are two or three and the choice matters (docs/UI-COMPONENTS).
Column {
    id: root
    property var options: []              // [{value, label, hint}]
    property var value: null
    signal picked(var value)

    spacing: Theme.s2

    Repeater {
        model: root.options
        delegate: Item {
            required property var modelData
            width: root.width
            height: Math.max(20, line.implicitHeight)

            Rectangle {
                id: ring
                width: 16
                height: 16
                radius: 8
                anchors.verticalCenter: parent.verticalCenter
                color: Theme.surface
                border.width: modelData.value === root.value ? 5 : 1
                border.color: modelData.value === root.value ? Theme.primary
                              : hov.containsMouse ? Theme.primary : Theme.border
                Behavior on border.width { NumberAnimation { duration: Theme.durFast } }
            }
            Column {
                id: line
                anchors.left: ring.right
                anchors.leftMargin: Theme.s2
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 0
                Txt { width: parent.width; text: modelData.label; font.pixelSize: Theme.fSmall }
                Txt {
                    width: parent.width
                    visible: !!modelData.hint
                    text: modelData.hint || ""
                    tone: "quiet"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    elide: Text.ElideNone
                }
            }
            MouseArea {
                id: hov
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: { root.value = modelData.value; root.picked(modelData.value) }
            }
        }
    }
}
