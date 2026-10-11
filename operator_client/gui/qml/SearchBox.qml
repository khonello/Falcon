import QtQuick
import QtQuick.Controls.Basic
import "."

// A small filter box: a magnifier in front, a clear cross once something is typed.
TextField {
    id: root
    property bool small: true
    property bool prefixIcon: true

    implicitWidth: 190
    implicitHeight: small ? Theme.controlSm : Theme.control
    leftPadding: prefixIcon ? 26 : 8
    rightPadding: text !== "" ? 24 : 8
    topPadding: 0
    bottomPadding: 0
    verticalAlignment: TextInput.AlignVCenter
    font.family: Theme.sans
    font.pixelSize: small ? Theme.fSmall : Theme.fBody
    color: Theme.text
    placeholderTextColor: Theme.text4
    selectByMouse: true
    selectionColor: Theme.alpha(Theme.accent, 0.3)

    background: Rectangle {
        radius: Theme.radiusSm
        color: Theme.surface
        border.width: 1
        border.color: root.activeFocus ? Theme.accent : root.hovered ? Theme.accent : Theme.borderStrong
    }
    Icon {
        visible: root.prefixIcon
        name: "search"
        size: 13
        color: Theme.text3
        x: 8
        anchors.verticalCenter: parent.verticalCenter
    }
    Rectangle {
        visible: root.text !== ""
        width: 14; height: 14; radius: 7
        color: Theme.text4
        anchors.right: parent.right
        anchors.rightMargin: 6
        anchors.verticalCenter: parent.verticalCenter
        Icon { anchors.centerIn: parent; name: "close"; size: 9; weight: 2.4; color: Theme.surface }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.clear() }
    }
}
