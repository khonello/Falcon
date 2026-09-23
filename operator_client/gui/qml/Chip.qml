import QtQuick
import "."

// A soft chip: a tinted pill that says one word. Never a border, never a new hue.
Rectangle {
    id: root
    property string text: ""
    property string tone: "neutral"          // neutral | accent | ok | warn | danger
    property bool dot: false

    readonly property color fg: tone === "neutral" ? Theme.dim : Theme.tone(tone)
    implicitWidth: row.implicitWidth + Theme.s3
    implicitHeight: 22
    radius: Theme.pill
    color: tone === "neutral" ? Theme.ground : Theme.toneSoft(tone)

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        Rectangle {
            width: 6; height: 6; radius: 3
            color: root.fg
            visible: root.dot
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            text: root.text
            color: root.fg
            font.pixelSize: Theme.fSmall
            font.weight: Font.Medium
        }
    }
}
