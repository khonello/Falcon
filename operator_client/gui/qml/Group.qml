import QtQuick
import "."

// A GROUP OF CARDS (the concept's iq-grp): its heading (lay-grp: 13 semibold in text-2, 6px above, the quiet line after
// it) and the cards 6px apart. `late` puts the group on a red wash that reaches 13px past the box's padding either side
// (tk-late), its heading red.
Item {
    id: root
    property string title: ""
    property string sub: ""
    property bool late: false
    property int cardGap: 6
    property bool spaced: false                 // a group after another stands 16px further off (iq-grp + iq-grp)
    default property alias cards: list.data
    readonly property real cardW: late ? width + 26 - 24 : width

    readonly property real lead: spaced ? 16 : 0
    implicitHeight: lead + (late ? col.implicitHeight + 22 : col.implicitHeight)
    height: implicitHeight

    Rectangle {
        visible: root.late
        x: -13; y: root.lead; width: root.width + 26
        height: parent.height - root.lead
        radius: 10
        color: Theme.alpha(Theme.crit, 0.07)
        border.width: 1
        border.color: Theme.alpha(Theme.crit, 0.22)
    }
    Column {
        id: col
        x: root.late ? -1 : 0
        y: root.lead + (root.late ? 10 : 0)
        width: root.cardW
        spacing: 6
        Item {
            width: parent.width
            height: h.height + 6
            Txt { id: h; y: 6; text: root.title; font.pixelSize: 12; font.weight: Font.DemiBold; color: root.late ? Theme.crit : Theme.text2; elide: Text.ElideNone }
            Txt { visible: root.sub !== ""; x: h.implicitWidth + 8; y: h.y + h.baselineOffset - baselineOffset; width: parent.width - x; text: root.sub; color: Theme.text3; font.pixelSize: 12 }
        }
        Column {
            id: list
            width: parent.width
            spacing: root.cardGap
        }
    }
}
