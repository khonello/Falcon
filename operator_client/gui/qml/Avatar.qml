import QtQuick
import "."

// A PERSON, as initials. No photographs: this console never has one, and a grey circle with a face
// icon in it says less than two letters do.
Rectangle {
    id: root
    property string name: ""
    property int size: 24
    property bool muted: false            // somebody who has been offboarded

    implicitWidth: size
    implicitHeight: size
    radius: size / 2
    color: muted ? Theme.fillStrong : Theme.primary

    Txt {
        anchors.centerIn: parent
        text: Theme.initials(root.name)
        color: root.muted ? Theme.mid : Theme.onDark
        font.pixelSize: Math.round(root.size * 0.42)
        strong: true
    }
}
