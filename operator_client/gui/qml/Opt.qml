import QtQuick
import "."

// ONE CHOICE OF SEVERAL (the concept's iq-opt): a radio, the choice in bold (" · recommended" after it when it is), and
// what it does under it; padded 9 12, radius 8, a hairline that turns accent, on an accent wash, when it is the one.
Rectangle {
    id: root
    property string title: ""
    property string desc: ""
    property bool recommended: false
    property bool on: false
    signal clicked()
    width: parent ? parent.width : 300
    height: oc.height + 18
    radius: Theme.radiusLg
    color: on ? Theme.accentSoft : "transparent"
    border.width: 1
    border.color: on ? Theme.accent : oa.containsMouse ? Theme.borderStrong : Theme.border
    MouseArea { id: oa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
    Rectangle {
        x: 12; y: 9 + 2 + 2
        width: 14; height: 14; radius: 7
        color: "transparent"
        border.width: 1.5
        border.color: root.on ? Theme.accent : Theme.text4
        Rectangle { visible: root.on; anchors.centerIn: parent; width: 6; height: 6; radius: 3; color: Theme.accent }
    }
    Column {
        id: oc
        x: 36; y: 9
        width: parent.width - 36 - 12
        spacing: 2
        Txt { width: parent.width; font.pixelSize: 13; textFormat: Text.StyledText; wrapMode: Text.WordWrap; elide: Text.ElideNone
              text: "<b>" + root.title + "</b>" + (root.recommended ? "<font color='" + Theme.text3 + "'> · recommended</font>" : "") }
        Txt { visible: root.desc !== ""; width: parent.width; text: root.desc; color: Theme.text3; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
    }
}
