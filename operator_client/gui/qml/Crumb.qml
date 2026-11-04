import QtQuick
import "."

// The path: the page, or the page and the thing open in it (Machines / OPS-03, Tasks / New task).
// The parent is a link back; the last part is bold. The level's own pages that open an item in place
// keep just their title: the item is beside the list, not under it.
Row {
    id: root
    spacing: 6

    // [label, page to go back to, mono]
    readonly property var parts: {
        var p = Nav.page, s = Nav.sub, t = Nav.title(p)
        if (s === null || s === undefined || s === "") return [[t, ""]]
        if (s === "new" || s === "mark" || String(s).indexOf("edit-") === 0) return [[t, ""]]      // an editor is a drawer over the page
        return [[t, ""]]
    }

    Repeater {
        model: root.parts
        delegate: Row {
            required property var modelData
            required property int index
            spacing: 6
            Txt {
                visible: index > 0
                text: "/"
                color: Theme.text3
                anchors.verticalCenter: parent.verticalCenter
            }
            Txt {
                readonly property bool last: index === root.parts.length - 1
                text: modelData[0]
                mono: !!modelData[2]
                color: last ? Theme.text : Theme.accent
                font.weight: last ? Font.DemiBold : Font.Normal
                font.pixelSize: last ? 14 : Theme.fBody
                anchors.verticalCenter: parent.verticalCenter
                elide: Text.ElideNone
                MouseArea {
                    anchors.fill: parent
                    enabled: modelData[1] !== ""
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: Nav.go(modelData[1])
                }
            }
        }
    }
}
