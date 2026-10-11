import QtQuick
import QtQuick.Controls.Basic
import "."

// A short menu under a button. items: [{key, label, disabled?, danger?} | {divider: true}].
// `openUnder(item)` places it under that item, right-aligned to it.
Popup {
    id: root
    property var items: []
    signal picked(var key)
    padding: 4
    width: 220
    height: col.height + 8
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    function openUnder(it) {
        var p = it.mapToItem(Overlay.overlay, it.width, it.height + 4)
        parent = Overlay.overlay
        x = Math.max(8, p.x - width)
        y = p.y
        open()
    }

    background: Rectangle {
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.borderStrong
        MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons }
    }
    Column {
        id: col
        width: parent.width
        Repeater {
            model: root.items
            delegate: Item {
                required property var modelData
                width: col.width
                height: modelData.divider ? 9 : 30
                Rectangle { visible: !!modelData.divider; anchors.centerIn: parent; width: parent.width - 8; height: 1; color: Theme.border }
                Rectangle {
                    visible: !modelData.divider
                    anchors.fill: parent
                    radius: Theme.radiusSm
                    color: area.containsMouse && !modelData.disabled ? Theme.surface3 : "transparent"
                    Txt {
                        x: 10
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 20
                        text: modelData.label || ""
                        color: modelData.disabled ? Theme.text4 : modelData.danger ? Theme.crit : Theme.text
                    }
                    MouseArea {
                        id: area
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: !modelData.disabled
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { root.close(); root.picked(modelData.key) }
                    }
                }
            }
        }
    }
}
