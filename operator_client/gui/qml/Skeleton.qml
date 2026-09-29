import QtQuick
import "."

// While the first reply is outstanding the page keeps its shape, quietened. Never a spinner over blank space.
Column {
    property int rows: 4
    spacing: Theme.s3
    Repeater {
        model: parent.rows
        delegate: Rectangle {
            required property int index
            width: parent.width * (index === 0 ? 0.35 : index % 3 === 0 ? 0.7 : 1)
            height: 12
            radius: Theme.radiusSm
            color: Theme.fillStrong
            SequentialAnimation on opacity {
                loops: Animation.Infinite
                NumberAnimation { to: 0.55; duration: 700 }
                NumberAnimation { to: 1; duration: 700 }
            }
        }
    }
}
