import QtQuick
import QtQuick.Controls.Basic
import "."

// A text box that grows with what is written, between `minRows` and `maxRows` lines. `edited` gives
// the text on every change; `submitted` fires on Enter (Shift+Enter adds a line) when `enterSends`.
Item {
    id: root
    property string text: ""
    property string placeholder: ""
    property int minRows: 2
    property int maxRows: 5
    property bool borderless: false
    property bool enterSends: false
    property int maxLength: 0
    signal edited(string text)
    signal submitted()
    function focusIt() { area.forceActiveFocus() }

    readonly property real lineH: 20
    implicitHeight: Math.max(minRows, Math.min(maxRows, area.lineCount)) * lineH + 14
    implicitWidth: 240

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusSm
        color: root.borderless ? "transparent" : Theme.surface
        border.width: root.borderless ? 0 : 1
        border.color: area.activeFocus ? Theme.accent : Theme.borderStrong
    }
    Flickable {
        id: fl
        anchors.fill: parent
        contentHeight: area.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        TextArea.flickable: TextArea {
            id: area
            text: root.text
            placeholderText: root.placeholder
            placeholderTextColor: Theme.text4
            wrapMode: TextEdit.Wrap
            font.family: Theme.sans
            font.pixelSize: Theme.fBody
            color: Theme.text
            selectByMouse: true
            selectionColor: Theme.alpha(Theme.accent, 0.3)
            leftPadding: 10; rightPadding: 10; topPadding: 6; bottomPadding: 6
            background: null
            onTextChanged: {
                if (root.maxLength > 0 && text.length > root.maxLength) { text = text.slice(0, root.maxLength); return }
                if (text !== root.text) root.edited(text)
            }
            Keys.onReturnPressed: function (e) {
                if (root.enterSends && !(e.modifiers & Qt.ShiftModifier)) { e.accepted = true; root.submitted() }
                else e.accepted = false
            }
        }
    }
    Txt {
        visible: root.maxLength > 0
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 6
        text: area.text.length + " / " + root.maxLength
        color: Theme.text4
        font.pixelSize: 11
    }
}
