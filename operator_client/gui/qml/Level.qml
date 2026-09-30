import QtQuick
import "."

// A THRESHOLD, DRAWN AGAINST WHAT IS NORMAL. "The processor above 85%" means nothing until you can
// see that these machines sit at 20 to 40 all day -- so the band of ordinary readings is behind the
// handle, and the line you are setting is read against it.
Item {
    id: root
    property real value: 0.85
    property real normalFrom: 0.2         // where these machines usually sit
    property real normalTo: 0.45
    property string unit: "%"
    signal moved(real value)

    implicitWidth: 320
    implicitHeight: 40

    Rectangle {
        id: track
        anchors.left: parent.left
        anchors.right: figure.left
        anchors.rightMargin: Theme.s3
        anchors.verticalCenter: parent.verticalCenter
        height: 6
        radius: 3
        color: Theme.fillStrong

        // what a normal day looks like on these machines
        Rectangle {
            x: parent.width * root.normalFrom
            width: parent.width * (root.normalTo - root.normalFrom)
            height: parent.height
            radius: parent.radius
            color: Theme.border
        }
        Rectangle {
            id: knob
            x: parent.width * root.value - width / 2
            y: -6
            width: 18
            height: 18
            radius: 9
            color: Theme.surface
            border.width: 2
            border.color: drag.drag.active || kh.containsMouse ? Theme.primaryPress : Theme.primary

            MouseArea {
                id: drag
                anchors.fill: parent
                anchors.margins: -6
                cursorShape: Qt.SizeHorCursor
                drag.target: knob
                drag.axis: Drag.XAxis
                drag.minimumX: -knob.width / 2
                drag.maximumX: track.width - knob.width / 2
                onPositionChanged: if (drag.drag.active) {
                    root.value = Math.max(0, Math.min(1, (knob.x + knob.width / 2) / track.width))
                    root.moved(root.value)
                }
            }
        }
        MouseArea {
            id: kh
            anchors.fill: parent
            anchors.margins: -8
            hoverEnabled: true
            acceptedButtons: Qt.NoButton
        }
    }
    Txt {
        id: figure
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        text: Math.round(root.value * 100) + root.unit
        mono: true
        strong: true
        font.pixelSize: Theme.fSmall
    }
    Txt {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        text: "these machines usually sit at " + Math.round(root.normalFrom * 100)
              + "\u2013" + Math.round(root.normalTo * 100) + root.unit
        tone: "quiet"
        font.pixelSize: 11
    }
}
