import QtQuick
import QtQuick.Controls
import "."

// A tab row inside a page, drawn the one way TABS.md allows: PLAIN TEXT. The current tab differs by
// colour and weight only -- no track, no box, no fill, no underline (the user, 26 Sep 2026: "current
// tab doesn't need a line under"). Set out like a header row, spaced, reading as words.
// segments: [{ text: "Pending", count: 3 }, { text: "Force", tint: Theme.danger }]
Item {
    id: root
    property var segments: []
    property int currentIndex: 0
    property color tint: Theme.ink

    function tintOf(index) {
        var s = root.segments[index]
        return (s && s.tint !== undefined) ? s.tint : root.tint
    }

    implicitHeight: 28
    implicitWidth: row.implicitWidth

    Row {
        id: row
        anchors.verticalCenter: parent.verticalCenter
        spacing: 22

        Repeater {
            model: root.segments
            delegate: Item {
                required property int index
                required property var modelData
                readonly property bool active: root.currentIndex === index

                objectName: "tab_" + modelData.text
                width: label.implicitWidth
                height: root.height

                Row {
                    id: label
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 5
                    Label {
                        text: modelData.text
                        color: active ? root.tintOf(index) : hover.hovered ? Theme.textDim : Theme.textFaint
                        font.pixelSize: Theme.fontMedium
                        font.weight: active ? Font.DemiBold : Font.Normal
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    // a count is a word too: faint, beside the name, never a badge
                    Label {
                        visible: modelData.count !== undefined
                        text: modelData.count !== undefined ? String(modelData.count) : ""
                        color: Theme.textFaint
                        font.pixelSize: Theme.fontBody
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.currentIndex = index }
            }
        }
    }
}
