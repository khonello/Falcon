import QtQuick
import "."

// ONE THING, AS A CARD: the concept's iq-card inside its tk-item. A grid of 34px | the rest | `midW` | `actW`, 12px apart,
// padded 10 12: a round icon; the title (13, semibold), a quiet line (12) and an optional second line; in the middle
// column a note (right-aligned, red and bold when hot) or the card's own drawing (`mid`); in the last its action or
// Expand, at the right. The accordion standard (the user, 1 Nov 2026): a click on the card PICKS it (surface-3); only
// Expand / Collapse OPENS it, and what it opens is the card's details (its children), indented to the text, 0 14 14 58.
Rectangle {
    id: root
    property string icon: "alert"
    property color dotColor: "transparent"     // a department's colour, as a small square, in place of the icon
    property bool hot: false                    // urg: the icon goes red
    property string title: ""
    property string tag: ""                     // a quiet word beside the title (a department)
    property color titleDot: "transparent"      // where the title came from (nt-dot), just after it
    property string titleDotTip: ""
    property string line: ""
    property bool lineHot: false
    property bool lineMono: false               // a path: iq-s mono
    property string line2: ""                   // iq-n: a second line, in text-2
    property string note: ""
    property bool noteHot: hot
    property string act: ""
    property string actKind: "default"
    property bool actDoes: false
    property bool compact: false                // a narrow column: no middle column, the action stays
    property bool picked: false
    property bool dim: false                    // done: no fill, a quiet border, quieter
    property bool tint: false                   // inside a late group: a red wash
    property bool expandable: false
    property bool expanded: false
    property real midW: factsWidth > 0 ? factsWidth : 210
    property real actW: 128                     // 0: no last column (Issues' cards)
    property real padV: 10
    readonly property real actSpace: actW > 0 ? actW + 12 : 0
    property real factsWidth: 0                 // older name for the middle column's width, with `facts`
    property alias mid: midBox.data
    property alias facts: midBox.data
    property alias actions: actRow.data         // more than one button in the last column
    default property alias details: det.data
    signal open()
    signal acted()
    signal toggle()

    readonly property bool hasMid: !compact && (note !== "" || midBox.children.length > 0)
    implicitHeight: head.height + (expanded ? det.childrenRect.height + 14 : 0)
    height: implicitHeight
    radius: Theme.radiusLg
    // tk-item is the card's ground; iq-card, its head, carries the pick and the hover, so an opened card's details stay on the ground
    color: dim ? "transparent" : tint ? Theme.mix(Theme.crit, Theme.surface2, 0.05) : Theme.surface2
    border.width: dim || expanded ? 1 : 0
    border.color: Theme.border
    opacity: dim ? 0.75 : 1

    Item {
        id: head
        width: parent.width
        height: 2 * root.padV + Math.max(34, main.implicitHeight)
        Rectangle {
            anchors.fill: parent
            radius: Theme.radiusLg
            color: root.dim ? "transparent" : root.picked ? Theme.surface3
                 : area.containsMouse ? Theme.mix(Theme.surface3, root.color, 0.5) : "transparent"
        }
        MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.open() }
        Rectangle {
            id: ic
            x: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 34; height: 34; radius: 17
            color: root.hot ? Theme.mix(Theme.crit, Theme.surface3, 0.16) : Theme.surface3
            Icon { visible: root.dotColor.a === 0; anchors.centerIn: parent; name: root.icon; size: 15; color: root.hot ? Theme.crit : Theme.text2 }
            Rectangle { visible: root.dotColor.a > 0; anchors.centerIn: parent; width: 12; height: 12; radius: 3; color: root.dotColor }
        }
        Column {
            id: main
            x: 58
            width: parent.width - 58 - 12 - (root.hasMid ? root.midW + 12 : 0) - root.actSpace
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1
            Item {
                width: parent.width
                height: tt.height
                Txt { id: tt; text: root.title; font.weight: Font.DemiBold; width: Math.min(implicitWidth, parent.width - (tg.visible ? tg.implicitWidth + 8 : 0) - (root.titleDot.a > 0 ? 15 : 0)) }
                Rectangle { visible: root.titleDot.a > 0; x: tt.width + 8; anchors.verticalCenter: tt.verticalCenter; width: 7; height: 7; radius: 3.5; color: root.titleDot
                            Tip { text: root.titleDotTip } }
                Txt { id: tg; visible: root.tag !== ""; x: tt.width + 8; text: root.tag; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone
                      y: tt.baselineOffset - baselineOffset }
            }
            // a path is cut in its middle to fit, its start and its file kept, the whole of it on hover (the user, 12 Nov 2026)
            Txt { id: ln; visible: root.line !== ""; mono: root.lineMono; color: root.lineHot ? Theme.crit : Theme.text3; font.pixelSize: Theme.fSmall; width: parent.width
                  readonly property bool isPath: root.lineMono && /^([A-Za-z]:[\\\/]|\\\\|\/)/.test(root.line)
                  text: isPath ? Theme.fitPath(root.line, lnm, width) : root.line
                  FontMetrics { id: lnm; font: ln.font }
                  Tip { over: ln; text: ln.isPath && ln.text !== root.line ? root.line : "" } }
            Txt { visible: root.line2 !== ""; text: root.line2; color: Theme.text2; font.pixelSize: Theme.fSmall; width: parent.width }
        }
        // the middle column: the card's own drawing, or its note
        Item {
            id: midBox
            visible: root.hasMid
            x: parent.width - 12 - root.actSpace - root.midW
            width: root.midW
            height: parent.height
        }
        Txt {
                visible: !root.compact && root.note !== "" && midBox.children.length === 0
                anchors.right: midBox.right
                anchors.verticalCenter: parent.verticalCenter
                width: Math.min(implicitWidth, root.midW)
                horizontalAlignment: Text.AlignRight
                text: root.note
                font.pixelSize: Theme.fSmall
                font.weight: root.noteHot ? Font.DemiBold : Font.Normal
                color: root.noteHot ? Theme.crit : Theme.text2
        }
        // the last column: the action, or Expand, at the right
        Row {
            id: actRow
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10
            layoutDirection: Qt.RightToLeft
            Btn {
                id: actB
                visible: root.act !== "" && !root.expandable
                small: true
                kind: root.actKind
                text: root.act
                onClicked: root.actDoes ? root.acted() : root.open()
            }
            Btn {
                id: expB
                objectName: "expand"
                visible: root.expandable
                small: true
                kind: "text"
                iconRight: true
                iconName: root.expanded ? "chevu" : "chevd"
                text: root.expanded ? "Collapse" : "Expand"
                onClicked: root.toggle()
            }
        }
    }
    Item {
        id: det
        visible: root.expanded
        x: 58
        y: head.height
        width: parent.width - 72
        height: childrenRect.height
    }
}
