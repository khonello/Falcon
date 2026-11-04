import QtQuick
import "."

// A TASK'S OWN TIME, AS A BAR (the concept's TaskBar, tb tk-bar): given at the left, the final deadline at the middle mark,
// overdue to the right in red; a thin amber tick for a soft deadline; "›" past the end. `took` greys the fill: handed in.
// Times are ms.
Item {
    id: root
    property real given: 0
    property real final_: 0
    property real soft: 0
    property real until: Time.now
    property bool took: false
    readonly property real at: 0.5                       // TK_AT: where the deadline sits
    readonly property real span: Math.max(60000, final_ - given)
    readonly property real r: (until - given) / span
    readonly property real pos: Math.max(0, Math.min(1, r * at))
    width: 104
    height: 8
    Rectangle { anchors.fill: parent; radius: 4; color: Theme.mix(Theme.surface3, Theme.text4, 0.70) }
    Rectangle { width: Math.min(root.pos, root.at) * root.width; height: parent.height; color: root.took ? Theme.text4 : Theme.text3
                topLeftRadius: 4; bottomLeftRadius: 4 }
    Rectangle { visible: root.pos > root.at; x: root.at * root.width; width: (root.pos - root.at) * root.width; height: parent.height; color: root.took ? Theme.text4 : Theme.crit
                topRightRadius: 4; bottomRightRadius: 4 }
    Rectangle { x: root.width / 2 - 1; y: -3; width: 2; height: parent.height + 6; radius: 1; color: Theme.text2 }
    Rectangle { visible: root.soft > root.given && root.soft < root.final_; x: (root.soft - root.given) / root.span * root.at * root.width; y: -2; width: 1; height: parent.height + 4; color: Theme.med }
    Txt { visible: root.r * root.at > 1; x: root.width - 2; y: -9; text: "›"; font.pixelSize: 13; font.weight: Font.DemiBold; color: Theme.crit; elide: Text.ElideNone }
}
