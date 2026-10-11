import QtQuick
import "."

// Tabs: a row of labels with the current one underlined in the accent, and a hairline under the row.
// tabs: [{key, label}] or strings. The page shows whatever matches `current`.
Item {
    id: root
    property var tabs: []
    property var current: null
    signal picked(var key)
    readonly property var items: tabs.map(function (t) { return typeof t === "object" ? t : { key: t, label: t } })
    implicitHeight: 38
    implicitWidth: row.implicitWidth

    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
    Row {
        id: row
        height: parent.height
        spacing: 24
        Repeater {
            model: root.items
            delegate: Item {
                required property var modelData
                readonly property bool on: root.current === modelData.key
                width: lbl.implicitWidth
                height: row.height
                Txt {
                    id: lbl
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label
                    color: on ? Theme.accent : area.containsMouse ? Theme.accent : Theme.text
                    font.weight: on ? Font.Medium : Font.Normal
                    elide: Text.ElideNone
                }
                Rectangle { visible: on; anchors.bottom: parent.bottom; width: parent.width; height: 2; color: Theme.accent }
                MouseArea {
                    id: area
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: { root.current = modelData.key; root.picked(modelData.key) }
                }
            }
        }
    }
}
