import QtQuick
import "."

// THE SITUATION, in one sentence at the top of a page (the concept's SitBar): what needs the person, said plainly, and
// when it was read. Empty text draws nothing.
Rectangle {
    id: root
    property string text: ""
    property var at: null                       // when the page last read it; "as of HH:MM"
    visible: text !== ""
    width: parent ? parent.width : 600
    // the concept's ib-sit: padding 14 20 14 16, the accent fading out across the first 60%
    height: visible ? Math.max(32, line.implicitHeight) + 30 : 0
    radius: Theme.radiusLg
    border.width: 1
    border.color: Theme.mix(Theme.accent, Theme.border, 0.22)
    gradient: Gradient {
        orientation: Gradient.Horizontal
        GradientStop { position: 0; color: Theme.mix(Theme.accent, Theme.surface, 0.06) }
        GradientStop { position: 0.6; color: Theme.surface }
    }

    Rectangle {
        id: mark
        x: 16
        anchors.verticalCenter: parent.verticalCenter
        width: 32; height: 32; radius: 16
        color: Theme.accentSoft
        Icon { anchors.centerIn: parent; name: "aim"; size: 15; color: Theme.accent }
    }
    Txt {
        id: line
        anchors.left: mark.right
        anchors.leftMargin: 14
        anchors.right: when.left
        anchors.rightMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        text: root.text
        font.pixelSize: 16
        font.weight: Font.Medium
        font.letterSpacing: -0.08
        wrapMode: Text.WordWrap
        elide: Text.ElideNone
    }
    Txt {
        id: when
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        visible: root.at !== null
        text: root.at !== null ? "as of " + Time.hhmm(root.at) : ""
        color: Theme.text3
        font.pixelSize: Theme.fSmall
        elide: Text.ElideNone
    }
}
