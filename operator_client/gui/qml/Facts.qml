import QtQuick
import "."

// FACTS, ONE A ROW (the concept's al-f): a quiet label in a 76px column, then the value (13, semibold) over a quiet line
// (11.5); each row padded 8 0 with a hairline under it but the last. `rows`: [[label, value, line], ...]; `labelW` widens
// the label column where a page's labels are longer.
Column {
    id: root
    property var rows: []
    property real labelW: 76
    property bool mono: false                    // values in mono (hosts, paths)
    width: parent ? parent.width : 300
    Repeater {
        model: root.rows
        Item {
            required property var modelData
            required property int index
            width: root.width
            height: v.implicitHeight + 16 + (index < root.rows.length - 1 ? 1 : 0)
            Txt { y: 8 + v.children[0].baselineOffset - baselineOffset; width: root.labelW; text: modelData[0]; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone; wrapMode: Text.WordWrap }
            Column {
                id: v
                x: root.labelW + 12; y: 8
                width: root.width - x
                spacing: 1
                Txt { width: parent.width; text: modelData[1] === undefined || modelData[1] === null ? "" : String(modelData[1]); font.weight: Font.DemiBold; mono: root.mono }
                Txt { visible: !!modelData[2]; width: parent.width; lh: 1.4375; text: modelData[2] || ""; color: modelData[3] ? Theme.crit : Theme.text3; font.pixelSize: 12 }
            }
            Rectangle { visible: index < root.rows.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
        }
    }
}
