import QtQuick
import "."

// THE ONE SHELL FOR BUILDING SOMETHING BIG (a flow, a set of marks, a rule): what you set on the left,
// a live picture on the right, and Cancel and Save at the foot, always in reach. `problem` holds the
// save back and says why; `note` says what saving does.
Column {
    id: root
    property real ratio: 7 / 12               // the left's share
    property string problem: ""
    property string note: ""
    property string saveLabel: "Save"
    property alias leftPane: leftBox.data
    property alias rightPane: rightBox.data
    signal cancel()
    signal save()
    spacing: 14

    Row {
        width: parent.width
        spacing: 14
        Item { id: leftBox; width: (parent.width - 14) * root.ratio; height: childrenRect.height }
        Item { id: rightBox; width: (parent.width - 14) * (1 - root.ratio); height: childrenRect.height }
    }
    Rectangle {
        width: parent.width
        height: 50
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.borderStrong
        Txt {
            x: 16
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - btns.width - 40
            text: root.problem || root.note
            color: root.problem ? Theme.med : Theme.text3
            font.pixelSize: 12
        }
        Row {
            id: btns
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            Btn { text: "Cancel"; onClicked: root.cancel() }
            Btn { kind: "primary"; text: root.saveLabel; enabled: root.problem === ""; tip: root.problem; onClicked: root.save() }
        }
    }
}
