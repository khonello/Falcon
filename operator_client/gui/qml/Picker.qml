import QtQuick
import QtQuick.Controls
import "."

// The console combo box, matched to Field.
ComboBox {
    id: root
    implicitHeight: Theme.controlHeight
    font.pixelSize: Theme.fontBody
    contentItem: Label {
        leftPadding: Theme.space2; rightPadding: Theme.space4
        text: root.displayText
        color: Theme.text
        font: root.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: Label {
        anchors.right: parent.right; anchors.rightMargin: Theme.space2; anchors.verticalCenter: parent.verticalCenter
        text: "▾"; color: Theme.textDim; font.pixelSize: Theme.fontBody
    }
    background: Rectangle {
        radius: Theme.radius
        color: Theme.canvas
        border.width: 1
        border.color: root.activeFocus || root.down ? Theme.accent : Theme.border
    }
    delegate: ItemDelegate {
        id: item
        required property var modelData
        required property int index
        width: root.width
        highlighted: root.highlightedIndex === index
        contentItem: Label { text: item.modelData; color: Theme.text; font.pixelSize: Theme.fontBody; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { color: item.highlighted ? Theme.surfaceHigh : Theme.overlay }
    }
    popup.background: Rectangle { color: Theme.overlay; border.width: 1; border.color: Theme.borderStrong; radius: Theme.radius }
}
