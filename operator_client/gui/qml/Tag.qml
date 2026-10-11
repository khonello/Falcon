import QtQuick
import "."

// A short label on a tint of its own colour. `c` is the colour; no colour is quiet grey. `tone` is the
// older spelling (warn | danger | accent | ok) and still works.
Rectangle {
    id: root
    property string text: ""
    property string tone: ""
    property color c: tone !== "" ? Theme.tone(tone) : Theme.text3
    property string iconName: ""
    property bool mono: false

    implicitWidth: row.implicitWidth + 12
    implicitHeight: 20
    radius: 3
    color: Theme.alpha(c, 0.12)

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 4
        Icon { visible: root.iconName !== ""; name: root.iconName; size: 12; color: root.c; anchors.verticalCenter: parent.verticalCenter }
        Txt {
            text: root.text
            color: root.tone === "" && root.c === Theme.text3 ? Theme.text2 : root.c
            font.pixelSize: 11
            font.weight: Font.Medium
            mono: root.mono
            elide: Text.ElideNone
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
