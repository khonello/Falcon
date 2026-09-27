import QtQuick
import "."

// A DEPARTMENT AS A CARD (board OV02, Authority): its identity stamp, name and machine count, its Admins as overlapping
// avatars -- or "nobody" and the one act, Assign an Admin -- and a state phrase on the right. Double click enters it.
Rectangle {
    id: root

    property var dept: ({})                 // { department_id, name, admins: [{name, session}], workers: [...] }
    property color stamp: Theme.accent
    property string stateWord: ""
    property string stateTone: ""
    property var modelData: null
    property int index: -1
    signal entered()
    signal assign()

    readonly property var admins: dept && dept.admins ? dept.admins : []
    readonly property int machines: dept && dept.workers ? dept.workers.length : 0

    implicitHeight: 58
    radius: 14
    color: area.containsMouse ? Qt.lighter(Theme.pane, 1.12) : Theme.pane

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onDoubleClicked: root.entered()
    }

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        Rectangle { width: 9; height: 9; radius: 3; color: root.stamp; anchors.verticalCenter: parent.verticalCenter }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1
            Txt { text: root.dept ? (root.dept.name || "") : ""; color: Theme.ink; font.pixelSize: Theme.fRow - 1; font.weight: Font.DemiBold }
            Txt { text: root.machines + (root.machines === 1 ? " machine" : " machines"); color: Theme.faint; font.pixelSize: Theme.fMeta }
        }
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4
            visible: root.admins.length > 0
            Repeater {
                model: root.admins.slice(0, 4)
                delegate: Avatar { required property var modelData; initials: Theme.initials(modelData.name || ""); size: 26 }
            }
        }
        Txt { visible: root.admins.length === 0; text: "nobody"; color: Theme.danger; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
              anchors.verticalCenter: parent.verticalCenter }
    }
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10
        Txt { visible: root.stateWord !== ""; text: root.stateWord; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold
              color: root.stateTone === "" ? Theme.faint : Theme.tone(root.stateTone); anchors.verticalCenter: parent.verticalCenter }
        GBtn { visible: root.admins.length === 0; text: "Assign an Admin"; small: true; onClicked: root.assign()
               anchors.verticalCenter: parent.verticalCenter }
    }
}
