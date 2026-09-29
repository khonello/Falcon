import QtQuick
import "."

// RULE 4: anything destructive or costly names the cost before the verb. The verb is the button;
// the cost is the sentence above it, and it is written in what actually happens to a person.
Modal {
    id: root
    property string cost: ""
    property string verb: "Yes"
    property bool destructive: false
    signal accepted()

    width: 440

    Txt {
        width: parent.width
        text: root.cost
        tone: "mid"
        wrapMode: Text.WordWrap
        elide: Text.ElideNone
    }

    footer: [
        Btn {
            text: "Cancel"
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: yes.left
            anchors.rightMargin: Theme.s2
            onClicked: root.close()
        },
        Btn {
            id: yes
            objectName: "confirmYes"
            kind: "primary"
            danger: root.destructive
            text: root.verb
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: Theme.s5
            onClicked: { root.close(); root.accepted() }
        }
    ]
}
