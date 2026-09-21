import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// One value, its label, an optional unit, a tint strip on the left edge. A strip of these answers
// "what state is this in?" from across the room. Mono value so a changing number never twitches.
Rectangle {
    id: root
    property string label: ""
    property string value: "--"
    property string unit: ""
    property color tint: Theme.accent
    property int valueSize: Theme.fontHuge

    implicitWidth: Math.max(116, content.implicitWidth + Theme.space3 + Theme.space2 + 4)
    implicitHeight: 56
    radius: Theme.radius
    color: Theme.surface
    border.width: 1
    border.color: Theme.border

    Rectangle {
        anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
        anchors.margins: 1
        width: 2; radius: 1
        color: root.tint
    }
    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.leftMargin: Theme.space3; anchors.rightMargin: Theme.space2
        anchors.topMargin: Theme.space2; anchors.bottomMargin: Theme.space2
        spacing: 2
        Eyebrow { label: root.label }
        RowLayout {
            spacing: 4
            Label {
                text: root.value
                color: Theme.text
                font.pixelSize: root.valueSize
                font.family: Theme.mono
                elide: Text.ElideRight
            }
            Label {
                visible: root.unit !== ""
                text: root.unit
                color: Theme.textFaint
                font.pixelSize: Theme.fontSmall
                Layout.alignment: Qt.AlignBottom
                Layout.bottomMargin: 3
            }
        }
    }
}
