import QtQuick
import "."

// ONE DEPARTMENT AS A CARD, for the pages where the Super User looks at the organisation rather than works in it (Tasks, Flows): its name, who looks after it,
// a bar of how its things stand, then a few of them as one line each. A card is always one height, so a row of them lines up. A click on a line opens it.
//   segs: [{ n, c }]     the bar        default content: the lines
Rectangle {
    id: root
    property string title: ""
    property string sub: ""
    property bool noAdmin: false
    property var segs: []
    property string total: ""
    default property alias lines: body.data
    height: 252
    radius: Theme.radius
    color: Theme.surface
    border.width: 1
    border.color: Theme.border
    clip: true

    readonly property real sum: segs.reduce(function (a, s) { return a + s.n }, 0)
    Column {
        x: 16; y: 14
        width: parent.width - 32
        spacing: 4
        Row {
            width: parent.width
            spacing: 8
            Txt { text: root.title; font.weight: Font.DemiBold; font.pixelSize: Theme.fTitle; width: Math.min(implicitWidth, parent.width - totalTxt.width - 8) }
            Txt { id: totalTxt; text: root.total; color: Theme.text3; anchors.baseline: parent.children[0].baseline; elide: Text.ElideNone }
        }
        Txt { width: parent.width; text: root.noAdmin ? "No Admin" : root.sub; color: root.noAdmin ? Theme.crit : Theme.text3; font.pixelSize: 12 }
        Item { width: 1; height: 6 }
        Rectangle {
            width: parent.width; height: 8; radius: 4; color: Theme.surface3; clip: true
            Row {
                anchors.fill: parent
                Repeater {
                    model: root.segs
                    Rectangle { required property var modelData; width: root.sum > 0 ? parent.width * modelData.n / root.sum : 0; height: parent.height; color: modelData.c }
                }
            }
        }
        Item { width: 1; height: 6 }
        Column { id: body; width: parent.width; spacing: 0 }
    }
}
