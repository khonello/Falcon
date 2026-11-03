import QtQuick
import "."

// THE CONCEPT'S ib-box, which every version 1 page is built of: a bordered box (radius 8, padding 14 16 16) whose header
// is the title and a quiet line after it on the same baseline, with no rule under it; when the line does not fit beside
// the title it goes under it, as CSS's flex-wrap puts it. `extra` sits at the header's right. What the box holds is
// stacked 10px apart, the box's own gap. A box given a height lets its body fill the rest (`fill`).
Rectangle {
    id: root
    property string title: ""
    property string sub: ""
    property bool accentFoot: false            // og-change: the input at the foot of a page, a dot before its title
    property bool fill: false
    property color subDot: "transparent"      // the concept's "live": a dot with a halo before the line
    property int gap: 10
    default property alias content: body.data
    property alias extra: extraRow.data
    readonly property alias bodyItem: body
    readonly property real headerHeight: head.visible ? head.height + 12 + 14 : 14      // where the body starts
    readonly property real innerW: width - 32

    color: Theme.surface
    radius: Theme.radiusLg
    border.width: 1
    border.color: accentFoot ? Theme.mix(Theme.accent, Theme.border, 0.30) : Theme.border
    gradient: accentFoot ? footG : undefined
    Gradient {
        id: footG
        GradientStop { position: 0; color: Theme.mix(Theme.accent, Theme.surface, 0.045) }
        GradientStop { position: 0.7; color: Theme.surface }
    }
    implicitHeight: headerHeight + (fill ? 0 : body.implicitHeight) + 16

    // the header: the title, then the line on the same baseline, or under it when it does not fit
    Item {
        id: head
        visible: root.title !== "" || root.sub !== "" || extraRow.children.length > 0
        x: 16; y: 14
        width: root.innerW
        // CSS's flex-wrap over title, line, spacer, extra: all on one line when they fit; else the extra goes under at the
        // left; and when even the title and the line do not fit, the line goes under the title, wrapping
        readonly property real dotW: root.subDot.a > 0 ? 13 : 0
        readonly property real exW: extraRow.children.length ? extraRow.implicitWidth : 0
        readonly property real tsW: tt.implicitWidth + (st.visible ? 10 + dotW + st.implicitWidth : 0)
        readonly property bool extraDown: exW > 0 && tsW + 10 + exW > width
        readonly property real room: extraDown ? width : width - (exW > 0 ? exW + 10 : 0)
        readonly property bool oneLine: !st.visible || tsW <= room
        readonly property real line1: oneLine ? Math.max(tt.height, st.visible ? st.height : 0, extraDown ? 0 : extraRow.height) : tt.height + 10 + st.height
        height: line1 + (extraDown ? 10 + extraRow.height : 0)
        Rectangle {
            visible: root.accentFoot
            y: tt.height / 2 - 2.5
            width: 7; height: 7; radius: 3.5
            color: Theme.accent
        }
        Txt {
            id: tt
            leftPadding: root.accentFoot ? 15 : 0
            text: root.title
            font.pixelSize: 14
            font.weight: Font.DemiBold
            width: Math.min(implicitWidth, head.room)
            elide: Text.ElideRight
        }
        Txt {
            id: st
            visible: root.sub !== ""
            text: root.sub
            color: Theme.text3
            font.pixelSize: Theme.fSmall
            x: (head.oneLine ? tt.width + 10 : 0) + head.dotW
            y: head.oneLine ? tt.baselineOffset - baselineOffset : tt.height + 10
            width: head.oneLine ? implicitWidth : head.room
            wrapMode: head.oneLine ? Text.NoWrap : Text.WordWrap
            elide: Text.ElideNone
        }
        Rectangle {
            visible: head.dotW > 0
            x: st.x - head.dotW; y: st.y + st.height / 2 - 3.5
            width: 7; height: 7; radius: 3.5
            color: root.subDot
            Rectangle { anchors.centerIn: parent; width: 13; height: 13; radius: 6.5; color: Theme.alpha(root.subDot, 0.22); z: -1 }
        }
        Row {
            id: extraRow
            x: head.extraDown ? 0 : head.width - width
            // words sit on the title's baseline; buttons and pickers are centred on its line
            readonly property bool wordy: children.length > 0 && children[0].lh !== undefined
            y: head.extraDown ? head.line1 + 10 : wordy ? tt.baselineOffset - children[0].baselineOffset : (tt.height - height) / 2
            spacing: 8
        }
    }
    Column {
        id: body
        x: 16
        y: root.headerHeight
        width: root.innerW
        height: root.fill ? root.height - root.headerHeight - 16 : implicitHeight
        spacing: root.gap
    }
}
