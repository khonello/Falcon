import QtQuick
import "."

// ONE LINE, THREE KINDS (docs/UI.md rule 7a): a note, something that will need someone, something
// that needs someone now. No stripe down the left edge -- rule 11, and it is a hard one.
Rectangle {
    id: root
    property string kind: "note"            // note | warn | danger
    property string text: ""
    property string iconName: ""

    readonly property string glyph: iconName !== "" ? iconName : kind === "note" ? "info" : "warn"

    implicitWidth: 15 + Theme.s2 + label.implicitWidth + 2 * Theme.s3
    implicitHeight: Math.max(34, label.contentHeight + 2 * Theme.s2)
    radius: Theme.radius
    color: Theme.toneSoft(root.kind === "note" ? "" : root.kind)
    border.width: 1
    border.color: root.kind === "danger" ? "#ffccc7" : root.kind === "warn" ? "#ffe58f" : Theme.split

    Icon {
        id: ic
        name: root.glyph
        size: 15
        color: Theme.tone(root.kind === "note" ? "mid" : root.kind)
        anchors.left: parent.left
        anchors.leftMargin: Theme.s3
        anchors.verticalCenter: parent.verticalCenter
    }
    Txt {
        id: label
        anchors.left: ic.right
        anchors.leftMargin: Theme.s2
        anchors.right: parent.right
        anchors.rightMargin: Theme.s3
        anchors.verticalCenter: parent.verticalCenter
        text: root.text
        tone: root.kind === "note" ? "ink" : root.kind
        font.pixelSize: Theme.fSmall
        wrapMode: Text.WordWrap
        elide: Text.ElideNone
    }
}
