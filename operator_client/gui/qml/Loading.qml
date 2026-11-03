import QtQuick
import "."

// LOADING IN PLACE. A section that asks the Engine for something when an item is picked keeps its size and says so for a
// moment, as Machines does; a section built from what the list already holds never does (the user, 1 Nov 2026). Laid over
// the section's body under its heading (`under`), it hides what is behind it while `on`.
Rectangle {
    id: root
    property bool on: false
    property real under: 44
    property string text: "Loading"
    anchors.fill: parent
    anchors.topMargin: under
    color: Theme.surface
    radius: Theme.radius
    visible: on
    z: 40
    Row {
        anchors.centerIn: parent
        spacing: 8
        Icon {
            name: "loading"; size: 14; color: Theme.text3
            anchors.verticalCenter: parent.verticalCenter
            RotationAnimation on rotation { running: root.on; loops: Animation.Infinite; from: 0; to: 360; duration: 900 }
        }
        Txt { text: root.text; color: Theme.text3; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
    }
}
