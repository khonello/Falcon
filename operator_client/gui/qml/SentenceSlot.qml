import QtQuick
import "."

// A BLANK IN A SENTENCE (design/PATTERNS.md section 7): a soft fill of its tone, a small chevron -- it looks pressable
// and reads as a word. Clicking it asks the page to open its choices (a picker, a list); the slot only shows the choice.
// A `dashed` slot is the "+ then…" that adds a step.
Rectangle {
    id: root

    property string text: ""
    property string tone: "accent"
    property bool dashed: false
    property int fontSize: Theme.fRow
    signal clicked()

    implicitWidth: row.implicitWidth + 16
    implicitHeight: fontSize + 12
    radius: 7
    color: dashed ? "transparent" : (area.containsMouse ? Qt.rgba(Theme.tone(tone).r, Theme.tone(tone).g, Theme.tone(tone).b, 0.24)
                                                         : Theme.toneSoft(tone))
    border.width: dashed ? 1.5 : 0
    border.color: Theme.line2

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 4
        Txt {
            text: root.text
            color: root.dashed ? Theme.faint : Theme.tone(root.tone)
            font.pixelSize: root.fontSize
            font.weight: root.dashed ? Font.Normal : Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
        Icon {
            visible: !root.dashed
            name: "chevd"
            size: Math.round(root.fontSize * 0.7)
            color: Theme.tone(root.tone)
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
