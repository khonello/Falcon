import QtQuick
import "."

// A row of plain figures in one frame. When it filters, a click picks a figure and a second click
// clears it. items: [{key?, label, value, unit?, delta?, dc?}] -- an item with no key is only read.
Rectangle {
    id: root
    property var items: []
    property var on: null
    signal pick(var key)

    color: Theme.surface
    radius: Theme.radius
    border.width: 1
    border.color: Theme.border
    implicitHeight: 66
    clip: true

    Row {
        x: 1; y: 1
        width: parent.width - 2
        height: parent.height - 2
        Repeater {
            model: root.items
            delegate: Rectangle {
                id: cell
                required property var modelData
                required property int index
                readonly property bool act: modelData.key !== undefined && modelData.key !== null
                readonly property bool sel: act && root.on === modelData.key
                width: parent.width / Math.max(1, root.items.length)
                height: parent.height
                color: sel ? Theme.accentSoft : (act && area.containsMouse ? Theme.surface2 : "transparent")
                Behavior on color { ColorAnimation { duration: Theme.durFast } }
                Rectangle { visible: cell.index > 0; width: 1; height: parent.height; color: Theme.border }

                Column {
                    x: 16; y: 11
                    width: parent.width - 32
                    spacing: 2
                    Txt { text: cell.modelData.label; color: Theme.text3; font.pixelSize: Theme.fSmall; width: parent.width }
                    Row {
                        spacing: 8
                        width: parent.width
                        Txt {
                            id: fig
                            text: String(cell.modelData.value)
                            font.pixelSize: Theme.fPage
                            font.weight: Font.DemiBold
                            color: cell.sel ? Theme.accent : Theme.text
                            elide: Text.ElideNone
                        }
                        Txt {
                            visible: !!cell.modelData.unit
                            text: cell.modelData.unit || ""
                            color: Theme.text3
                            anchors.baseline: fig.baseline
                            elide: Text.ElideNone
                        }
                        Txt {
                            text: cell.modelData.delta || ""
                            color: cell.modelData.dc ? cell.modelData.dc : Theme.text3
                            font.pixelSize: Theme.fSmall
                            anchors.baseline: fig.baseline
                            width: Math.max(0, parent.width - fig.width - 16 - (cell.modelData.unit ? 40 : 0))
                        }
                    }
                }
                MouseArea {
                    id: area
                    anchors.fill: parent
                    enabled: cell.act
                    hoverEnabled: true
                    cursorShape: cell.act ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: root.pick(cell.sel ? null : cell.modelData.key)
                }
            }
        }
    }
}
