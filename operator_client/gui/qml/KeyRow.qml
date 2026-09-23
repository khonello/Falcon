import QtQuick
import "."

// A label and its value, inside the detail card.
Rectangle {
    id: root

    property string label: ""
    property string value: ""
    property string tone: ""
    property bool monospace: false

    width: parent ? parent.width : 0
    height: 46
    radius: Theme.radiusMd
    color: Theme.ground

    Txt {
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        text: root.label
        font.pixelSize: Theme.fBody
        font.weight: Font.Medium
    }
    Txt {
        anchors.right: parent.right
        anchors.rightMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        text: root.value
        monospace: root.monospace
        color: root.tone === "" ? Theme.dim : Theme.tone(root.tone)
        font.pixelSize: Theme.fBody
    }
}
