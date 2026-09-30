import QtQuick
import QtQuick.Controls.Basic
import "."

// NOTHING TYPED THAT CAN BE PICKED (docs/UI-COMPONENTS.md). `options` are {value, label} pairs, so
// the console shows the word and sends the id.
Item {
    id: root
    property var options: []
    property var value: null
    property string placeholder: "Select"
    property bool invalid: false
    signal picked(var value)

    implicitWidth: 240
    implicitHeight: Theme.control

    function labelFor(v) {
        for (var i = 0; i < options.length; i++)
            if (options[i].value === v) return options[i].label
        return ""
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: root.invalid ? Theme.danger
                      : pop.opened ? Theme.primary
                      : hover.hovered ? Theme.primaryHover : Theme.border
        Behavior on border.color { ColorAnimation { duration: Theme.durFast } }

        Txt {
            anchors.left: parent.left
            anchors.leftMargin: Theme.s3
            anchors.right: chev.left
            anchors.rightMargin: Theme.s2
            anchors.verticalCenter: parent.verticalCenter
            text: root.value === null ? root.placeholder : root.labelFor(root.value)
            tone: root.value === null ? "quiet" : "ink"
        }
        Icon {
            id: chev
            name: "chevd"
            size: 14
            color: Theme.quiet
            anchors.right: parent.right
            anchors.rightMargin: Theme.s3
            anchors.verticalCenter: parent.verticalCenter
        }
        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: pop.opened ? pop.close() : pop.open() }
    }

    Popup {
        id: pop
        y: root.height + 4
        width: root.width
        padding: Theme.s1
        height: Math.min(list.contentHeight + 2 * Theme.s1, 224)
        background: Rectangle {
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.split
            // A popup that floats over the page is not modal, so anything it does not swallow is
            // delivered to whatever is underneath -- which on a table is a row, and a row opens a
            // drawer. This takes every press in the popup that no option took.
            MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true }
        }

        ListView {
            id: list
            anchors.fill: parent
            clip: true
            model: root.options
            delegate: Rectangle {
                required property var modelData
                width: list.width
                height: 30
                radius: Theme.radiusSm
                color: modelData.value === root.value ? Theme.primarySoft
                       : oh.containsMouse ? Theme.hover : "transparent"
                Txt {
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.s2
                    anchors.right: parent.right
                    anchors.rightMargin: Theme.s2
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label
                    strong: modelData.value === root.value
                }
                // MouseArea, not TapHandler: a TapHandler reacts to a press without consuming it,
                // so the row under the popup would react as well
                MouseArea {
                    id: oh
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.value = modelData.value
                        root.picked(modelData.value)
                        pop.close()
                    }
                }
            }
        }
    }
}
