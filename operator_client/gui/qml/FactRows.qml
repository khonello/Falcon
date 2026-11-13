import QtQuick
import "."

// tk-facts at the full width: 120px labels, what was set beside them, a hairline between, for an editor's last step.
Column {
    id: root
    property var rows: []                       // [[label, value, mono?, dot colour?, what the dot says?], ...]
    width: parent ? parent.width : 0
    topPadding: 2
    Repeater {
        model: root.rows
        delegate: Item {
            required property var modelData
            required property int index
            width: root.width
            height: fv.height + 10
            Txt { y: 5; width: 120; text: modelData[0]; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
            Txt { id: fv; x: 132; y: 5; width: parent.width - 132; text: Theme.paths(modelData[1], 3); mono: !!modelData[2]; font.pixelSize: 13; wrapMode: Text.Wrap; elide: Text.ElideNone
                  Tip { over: fv; text: fv.text !== String(modelData[1]) ? String(modelData[1]) : "" } }
            // where a value came from, just after it (nt-dot)
            Rectangle { visible: !!modelData[3]; x: fv.x + fv.contentWidth + 7; y: 5 + (fv.font.pixelSize * fv.lh - 7) / 2; width: 7; height: 7; radius: 3.5; color: modelData[3] || "transparent"
                        Tip { text: modelData[4] || "" } }
            Rectangle { visible: index < root.rows.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
        }
    }
}
