import QtQuick
import "."

// SOMETHING IS IN FLIGHT, in the place it is happening -- inside a button, in a pane. Never over a
// whole page: a page that is loading shows a Skeleton, which says what is coming.
Item {
    id: root
    property int size: 16
    property string tone: "accent"

    implicitWidth: size
    implicitHeight: size

    Repeater {
        model: 8
        delegate: Rectangle {
            required property int index
            width: Math.max(1.5, root.size / 10)
            height: Math.max(3, root.size / 3.4)
            radius: width / 2
            color: Theme.tone(root.tone)
            opacity: 0.15 + 0.85 * ((index + spin.step) % 8) / 8
            x: root.size / 2 - width / 2
            y: 0
            transform: Rotation {
                origin.x: Math.max(1.5, root.size / 10) / 2
                origin.y: root.size / 2
                angle: index * 45
            }
        }
    }
    QtObject { id: spin; property int step: 0 }
    Timer {
        interval: 100
        running: root.visible
        repeat: true
        onTriggered: spin.step = (spin.step + 1) % 8
    }
}
