import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Live feed of Engine pushes and command results, newest at the bottom.
Rectangle {
    id: feed
    color: "#17181b"
    border.color: "#333"

    function add(text, alert) {
        var now = new Date()
        lines.append({ at: Qt.formatTime(now, "HH:mm:ss"), text: text, alert: !!alert })
        if (lines.count > 300) lines.remove(0)
        list.positionViewAtEnd()
    }

    ListModel { id: lines }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 2
        Label { text: "Live"; color: "#888"; font.pixelSize: 11 }
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: lines
            delegate: Row {
                required property string at
                required property string text
                required property bool alert
                spacing: 8
                Label { text: at; color: "#666"; font.family: "Consolas" }
                Label { text: parent.text; color: alert ? "#ff8a80" : "#a8c7fa"; font.family: "Consolas"; wrapMode: Text.NoWrap }
            }
            ScrollBar.vertical: ScrollBar { }
        }
    }
}
