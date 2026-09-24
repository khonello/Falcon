import QtQuick
import "."

// Report routing, treatment A from board C07: a line per category, with who it reaches as chips.
// The default, because the word "always" does the job the diagram was doing, and nobody has to
// learn a geometry to read it. The flow lines and the sankey are the alternatives.
Column {
    id: root

    property var categories: []             // [{ label, departments: [{name, tint}] }]
    spacing: 0

    Repeater {
        model: root.categories
        delegate: Item {
            required property var modelData
            width: root.width
            height: 36

            Txt {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                width: 150
                text: modelData.label
                color: Theme.ink
                font.pixelSize: Theme.fBody
                elide: Text.ElideRight
            }
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                Chip { text: "You"; tone: "accent" }
                Repeater {
                    model: modelData.departments
                    delegate: Chip {
                        required property var modelData
                        text: modelData.name
                        tone: "neutral"
                    }
                }
            }
        }
    }
}
