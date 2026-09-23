import QtQuick
import "."

// The small multiple's one bar: a track, and the parts that fill it. Same shape every time.
Item {
    id: root

    property var parts: []                 // [{ tone, value }]
    property int barHeight: 9

    readonly property real total: {
        var t = 0
        for (var i = 0; i < parts.length; i++) t += parts[i].value
        return Math.max(1, t)
    }
    implicitHeight: barHeight

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: Theme.line
        opacity: 0.55
    }
    Row {
        height: parent.height
        spacing: 2
        Repeater {
            model: root.parts
            delegate: Rectangle {
                required property var modelData
                visible: modelData.value > 0
                width: visible ? Math.max(4, (modelData.value / root.total) * root.width - 2) : 0
                height: root.barHeight
                radius: height / 2
                color: Theme.tone(modelData.tone)
            }
        }
    }
}
