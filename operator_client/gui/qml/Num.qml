import QtQuick
import QtQuick.Controls.Basic
import "."

// A NUMBER, with its unit attached and its own steppers. A timeout is not free text: it has a floor,
// a ceiling and a unit, and the control should say all three.
Item {
    id: root
    property int value: 0
    property int from: 0
    property int to: 999999
    property int step: 1
    property string unit: ""
    signal changed(int value)

    implicitWidth: 160
    implicitHeight: Theme.control

    function set(v) {
        var n = Math.max(from, Math.min(to, v))
        if (n !== value) { value = n; changed(n) }
        field.text = String(n)
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: field.activeFocus ? Theme.primary : hov.containsMouse ? Theme.primaryHover : Theme.border
        Behavior on border.color { ColorAnimation { duration: Theme.durFast } }

        MouseArea { id: hov; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }

        TextInput {
            id: field
            anchors.left: parent.left
            anchors.leftMargin: Theme.s3
            anchors.right: unitLabel.left
            anchors.verticalCenter: parent.verticalCenter
            text: String(root.value)
            color: Theme.ink
            font.family: Theme.sans
            font.pixelSize: Theme.fBody
            selectByMouse: true
            validator: IntValidator { bottom: root.from; top: root.to }
            onEditingFinished: root.set(parseInt(text) || root.from)
        }
        Txt {
            id: unitLabel
            anchors.right: steps.left
            anchors.rightMargin: Theme.s2
            anchors.verticalCenter: parent.verticalCenter
            text: root.unit
            tone: "quiet"
            font.pixelSize: Theme.fSmall
        }
        Column {
            id: steps
            anchors.right: parent.right
            anchors.rightMargin: 1
            anchors.verticalCenter: parent.verticalCenter
            spacing: 0

            Repeater {
                model: ["caretu", "caretd"]
                delegate: Rectangle {
                    required property var modelData
                    width: 22
                    height: (Theme.control - 2) / 2
                    color: sh.containsMouse ? Theme.hover : "transparent"
                    Icon {
                        anchors.centerIn: parent
                        name: modelData
                        size: 12
                        color: Theme.quiet
                    }
                    MouseArea {
                        id: sh
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.set(root.value + (modelData === "caretu" ? root.step : -root.step))
                    }
                }
            }
        }
    }
}
