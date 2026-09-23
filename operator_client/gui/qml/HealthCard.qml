import QtQuick
import "."

// One department's work, in the two bars every department gets. Identity is the swatch; the bars
// keep the reserved state colours, and the panel's legend says what they mean.
Rectangle {
    id: root

    property string name: ""
    property color tint: Theme.accent
    property var tasks: []
    property var flows: []

    radius: Theme.radiusMd
    color: Theme.pane
    implicitHeight: column.implicitHeight + 26

    Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 14
        anchors.topMargin: 13
        spacing: 11

        Row {
            spacing: 7
            Rectangle {
                width: 10; height: 10; radius: 5
                color: root.tint
                anchors.verticalCenter: parent.verticalCenter
            }
            Txt {
                text: root.name
                font.pixelSize: Theme.fBody
                font.weight: Font.DemiBold
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Repeater {
            model: [{ label: "Tasks", parts: root.tasks }, { label: "Flows", parts: root.flows }]
            delegate: Column {
                required property var modelData
                width: column.width
                spacing: 5

                Item {
                    width: parent.width
                    height: 15
                    Txt {
                        anchors.left: parent.left
                        text: modelData.label
                        color: Theme.dim
                        font.pixelSize: Theme.fMeta
                    }
                    Txt {
                        anchors.right: parent.right
                        text: {
                            var t = 0
                            for (var i = 0; i < modelData.parts.length; i++) t += modelData.parts[i].value
                            return String(t)
                        }
                        color: Theme.faint
                        monospace: true
                        font.pixelSize: Theme.fMeta
                    }
                }
                MiniBar { width: parent.width; parts: modelData.parts }
            }
        }
    }
}
