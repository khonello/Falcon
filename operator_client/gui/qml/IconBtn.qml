import QtQuick
import QtQuick.Controls
import "."

AbstractButton {
    id: root
    property string iconName: ""
    property color color: Theme.dim
    property int size: 28
    property int glyph: 16

    implicitWidth: size
    implicitHeight: size
    hoverEnabled: true

    background: Rectangle {
        radius: Theme.radiusSm
        color: root.pressed ? Theme.line : root.hovered ? Qt.rgba(1, 1, 1, 0.07) : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.durFast } }
    }
    contentItem: Icon {
        name: root.iconName
        color: root.color
        size: root.glyph
        anchors.centerIn: parent
    }
}
