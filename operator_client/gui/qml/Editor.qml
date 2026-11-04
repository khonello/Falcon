import QtQuick
import "."

// ONE STEPPED EDITOR, as the concept's drawers are (nf-steps-wrap): on top what it is so far (rn-top: the step, the name, and what
// the editor adds), then the step's body filling the height (nf-body), then the foot (nt-next): what is missing, Cancel, Back, and
// the next step by name or the last word. Each step's content is a child with `visible: step === n`.
Column {
    id: root
    property string drawerTitle: ""
    property string drawerNote: ""
    property var names: []
    property int step: 0
    property string nameNow: ""                 // the name so far
    property string prob: ""                    // what stops the next step
    property string confirmText: ""
    property bool confirmDisabled: false
    property bool showName: true
    property bool showTop: true                 // Restrict something has no rn-top
    property real minHeight: 0
    default property alias body: bodyCol.data
    property alias head: topCol.data
    readonly property Item topSlot: slot        // an editor's own top box (Make a flow's drawing) goes here
    signal closed()
    signal confirmed()
    width: parent ? parent.width : 0
    spacing: 14

    readonly property bool last: step === names.length - 1
    Column { id: slot; width: parent.width }
    Box {
        id: topBox
        visible: root.showTop
        width: parent.width
        gap: 10
        Txt { text: root.names[root.step] + " · step " + (root.step + 1) + " of " + root.names.length; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
        Txt { visible: root.showName; width: parent.width; text: root.nameNow.trim() || "Not named yet"; font.pixelSize: 15; lh: 1.5
              font.weight: root.nameNow.trim() ? Font.DemiBold : Font.Normal; color: root.nameNow.trim() ? Theme.text : Theme.text4 }
        Column { id: topCol; width: parent.width; spacing: 6 }
    }
    Box {
        id: bodyBox
        width: parent.width
        height: Math.max(implicitHeight, root.minHeight - (root.showTop ? topBox.height + 14 : 0) - (slot.height > 0 ? slot.height + 14 : 0) - foot.height - 14)
        Column { id: bodyCol; width: parent.width; spacing: 12 }
    }
    Item {
        id: foot
        width: parent.width
        height: 40
        Txt { x: 2; anchors.verticalCenter: parent.verticalCenter; width: parent.width - btns.width - 16; text: root.prob; color: root.prob ? Theme.med : Theme.text3; font.pixelSize: 13 }
        Row {
            id: btns
            anchors.right: parent.right; anchors.rightMargin: 2; anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            Btn { text: "Cancel"; onClicked: root.closed() }
            Btn { visible: root.step > 0; iconName: "left"; text: "Back"; onClicked: root.step -= 1 }
            Btn { kind: "primary"; objectName: "editorNext"; iconRight: !root.last; iconName: root.last ? "" : "right"
                  enabled: root.prob === "" && !(root.last && root.confirmDisabled)
                  text: root.last ? root.confirmText : root.names[root.step + 1] || ""
                  onClicked: root.last ? root.confirmed() : root.step += 1 }
        }
    }
}
