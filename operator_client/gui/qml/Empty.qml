import QtQuick
import "."

// Zero is a state, not an absence. Where a list or a chart has nothing, it keeps its place and size
// and says what will appear there and, when there is one, the first step towards it.
Item {
    id: root
    property string icon: "inbox"
    property string title: "Nothing here yet"
    property string text: ""
    property string act: ""
    property int h: 120
    signal acted()

    implicitWidth: 320
    implicitHeight: h

    Row {
        anchors.verticalCenter: parent.verticalCenter
        x: 20
        width: parent.width - 40
        spacing: 14
        Rectangle {
            width: 34; height: 34; radius: 6
            color: Theme.alpha(Theme.text3, 0.12)
            anchors.verticalCenter: parent.verticalCenter
            Icon { anchors.centerIn: parent; name: root.icon; size: 16; color: Theme.text3 }
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - 48 - (btn.visible ? btn.width + 14 : 0)
            spacing: 3
            Txt { text: root.title; font.weight: Font.DemiBold; width: parent.width; elide: Text.ElideRight }
            Txt {
                visible: root.text !== ""
                text: root.text
                color: Theme.text3
                font.pixelSize: 12
                width: parent.width
                wrapMode: Text.WordWrap
                elide: Text.ElideNone
            }
        }
        Btn {
            id: btn
            visible: root.act !== ""
            small: true
            text: root.act
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.acted()
        }
    }
}
