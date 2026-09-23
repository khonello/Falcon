import QtQuick
import "."

// Neutral, always. A person is never a colour, and never wears a state dot.
Rectangle {
    id: root
    property string initials: ""
    property int size: 34

    implicitWidth: size
    implicitHeight: size
    radius: Math.round(size * 0.27)
    color: Theme.line2

    Txt {
        anchors.centerIn: parent
        text: root.initials
        color: Theme.ink
        font.pixelSize: Math.max(10, Math.round(root.size / 2) - 3)
        font.weight: Font.DemiBold
    }
}
