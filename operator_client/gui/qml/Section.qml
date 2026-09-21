import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// A titled panel: hairline border, small radius, a quiet uppercase title, optional one-line hint,
// and an optional 2px strip along the top for a section that carries a consequence.
// The title is quiet and the content is loud -- the operator is looking for a value, not for the
// name of the box it lives in.
Rectangle {
    id: root
    property string title: ""
    property string hint: ""
    property color accent: "transparent"
    property alias spacing: body.spacing
    default property alias content: body.data

    color: Theme.surface
    radius: Theme.radius
    border.width: 1
    border.color: Theme.border
    implicitHeight: layout.implicitHeight + Theme.space3 * 2
    implicitWidth: layout.implicitWidth + Theme.space3 * 2

    Rectangle {
        visible: root.accent !== "transparent"
        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
        anchors.margins: 1
        height: 2; radius: 1
        color: root.accent
    }

    ColumnLayout {
        id: layout
        anchors.fill: parent
        anchors.margins: Theme.space3
        spacing: Theme.space2

        Eyebrow { visible: root.title !== ""; label: root.title }
        Label {
            visible: root.hint !== ""
            text: root.hint
            color: Theme.textFaint
            font.pixelSize: Theme.fontSmall
            wrapMode: Text.Wrap
            Layout.fillWidth: true
            Layout.bottomMargin: Theme.space1
        }
        ColumnLayout {
            id: body
            spacing: Theme.space2
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
