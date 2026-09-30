import QtQuick
import "."

// A COUNT ON A THING. Only ever for something that needs a person: a badge on a quiet number is
// decoration, and this console does not decorate.
Rectangle {
    id: root
    property int value: 0
    property string tone: "danger"

    visible: value > 0
    implicitWidth: Math.max(16, label.implicitWidth + 8)
    implicitHeight: 16
    radius: 8
    color: Theme.tone(root.tone)

    Txt {
        id: label
        anchors.centerIn: parent
        text: root.value > 99 ? "99+" : String(root.value)
        color: Theme.onDark
        font.pixelSize: 10
        strong: true
    }
}
