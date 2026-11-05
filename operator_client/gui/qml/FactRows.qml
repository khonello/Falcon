import QtQuick
import "."

// tk-facts at the full width: 120px labels, what was set beside them, a hairline between, for an editor's last step.
Column {
    id: root
    property var rows: []                       // [[label, value, mono?], ...]
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
            Txt { id: fv; x: 132; y: 5; width: parent.width - 132; text: modelData[1]; mono: !!modelData[2]; font.pixelSize: 13; wrapMode: Text.Wrap; elide: Text.ElideNone }
            Rectangle { visible: index < root.rows.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
        }
    }
}
