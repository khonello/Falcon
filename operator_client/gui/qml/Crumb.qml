import QtQuick
import "."

// Falcon / Record / OPS-03 -- the only thing that says how deep you are.
Row {
    id: root
    property var path: []                    // ["Falcon", "Record"]
    signal picked(int index)
    spacing: Theme.s2

    Repeater {
        model: root.path
        delegate: Row {
            required property var modelData
            required property int index
            spacing: Theme.s2
            Txt {
                text: modelData
                tone: index === root.path.length - 1 ? "ink" : "mid"
                strong: index === root.path.length - 1
                font.pixelSize: Theme.fSmall
                anchors.verticalCenter: parent.verticalCenter
                TapHandler { enabled: index < root.path.length - 1; onTapped: root.picked(index) }
            }
            Icon {
                visible: index < root.path.length - 1
                name: "chevr"
                size: 11
                color: Theme.quiet
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
