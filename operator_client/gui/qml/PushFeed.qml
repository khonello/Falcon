import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// Live feed of Engine pushes and command results, newest at the bottom. Pinned under every page
// so what the system just did is never off-screen. Alerts are tinted; everything else is quiet.
Rectangle {
    id: feed
    color: Theme.surface
    Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.border }

    function add(text, alert) {
        var now = new Date()
        lines.append({ at: Qt.formatTime(now, "HH:mm:ss"), text: text, alert: !!alert })
        if (lines.count > 300) lines.remove(0)
        list.positionViewAtEnd()
    }

    ListModel { id: lines }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.space3; anchors.rightMargin: Theme.space3
        anchors.topMargin: Theme.space2; anchors.bottomMargin: Theme.space2
        spacing: Theme.space1
        RowLayout {
            Eyebrow { label: "Live" }
            Item { Layout.fillWidth: true }
            Label { text: lines.count + " entries"; color: Theme.textFaint; font.pixelSize: Theme.fontTiny }
            Label { text: "Clear"; color: clearHover.hovered ? Theme.text : Theme.textFaint; font.pixelSize: Theme.fontTiny
                    HoverHandler { id: clearHover } TapHandler { onTapped: lines.clear() } }
        }
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: lines
            spacing: 1
            delegate: Row {
                required property string at
                required property string text
                required property bool alert
                spacing: Theme.space2
                Label { text: at; color: Theme.textFaint; font.family: Theme.mono; font.pixelSize: Theme.fontSmall }
                Rectangle { width: 5; height: 5; radius: 3; anchors.verticalCenter: parent.verticalCenter; color: alert ? Theme.danger : Theme.accent; opacity: alert ? 1 : 0.5 }
                Label { text: parent.text; color: alert ? Theme.danger : Theme.textDim; font.family: Theme.mono; font.pixelSize: Theme.fontSmall; wrapMode: Text.NoWrap }
            }
            ScrollBar.vertical: ScrollBar { }
        }
    }
}
