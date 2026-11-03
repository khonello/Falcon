import QtQuick
import "."

// THREE STEPS AND ONE BUTTON (the concept's tk-give): what a careful job takes, numbered in accent circles, three columns
// 14px apart, and the button that starts it 18px to their right. `steps`: [[title, line], ...].
Item {
    id: root
    property var steps: []
    property string act: ""
    signal go()
    width: parent ? parent.width : 600
    height: Math.max(row.height, b.height)
    Row {
        id: row
        width: parent.width - b.width - 18
        anchors.verticalCenter: parent.verticalCenter
        spacing: 14
        Repeater {
            model: root.steps
            delegate: Item {
                required property var modelData
                required property int index
                width: (row.width - 28) / 3                // tk-steps: always three columns
                height: sc.height
                Rectangle { width: 22; height: 22; radius: 11; color: Theme.accentSoft
                            Txt { anchors.centerIn: parent; text: index + 1; color: Theme.accent; font.pixelSize: 12; font.weight: Font.DemiBold; elide: Text.ElideNone } }
                Column {
                    id: sc
                    x: 30
                    width: parent.width - 30
                    spacing: 2
                    Txt { width: parent.width; text: modelData[0]; font.weight: Font.DemiBold }
                    Txt { width: parent.width; text: modelData[1]; color: Theme.text3; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                }
            }
        }
    }
    Btn { id: b; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; kind: "primary"; text: root.act; onClicked: root.go() }
}
