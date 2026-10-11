import QtQuick
import "."

// Where a `Msg` lands: bottom centre, one dark line at a time, gone on its own. It never asks for a
// click, so it never carries an act -- anything that needs answering is a Modal, not this.
Item {
    id: root
    property int life: 2400
    property string text: ""
    property string kind: "note"

    Connections {
        target: Msg
        function onPosted(text, kind) { root.say(text, kind) }
        function onArrived(title, text, kind) { root.say(title === "" ? text : title + " · " + text, kind) }
    }
    function say(t, k) { root.text = t; root.kind = k; pill.opacity = 1; hide.restart() }
    Timer { id: hide; interval: root.life; onTriggered: pill.opacity = 0 }

    Rectangle {
        id: pill
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 20
        width: Math.min(line.implicitWidth + 28, root.width - 40)
        height: 34
        radius: 5
        color: root.kind === "danger" ? Theme.crit : Theme.text
        opacity: 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: Theme.durBase } }
        Txt {
            id: line
            anchors.centerIn: parent
            width: parent.width - 28
            horizontalAlignment: Text.AlignHCenter
            text: root.text
            color: root.kind === "danger" ? Theme.inverse : Theme.surface
            font.pixelSize: 12
        }
    }
}
