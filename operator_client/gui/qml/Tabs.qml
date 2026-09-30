import QtQuick
import "."

// TWO OR THREE KINDS OF THING ABOUT ONE SUBJECT. Not navigation: everything behind these tabs is the
// same row you opened. If a tab would need its own address, it is a page.
Item {
    id: root
    property var tabs: []                 // [{key, label, count}]
    property string current: ""
    signal picked(string key)

    implicitHeight: 36

    Row {
        id: strip
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        spacing: Theme.s4

        Repeater {
            model: root.tabs
            delegate: Item {
                required property var modelData
                readonly property bool on: modelData.key === root.current
                width: label.implicitWidth + (badge.visible ? badge.width + Theme.s1 : 0)
                height: 35

                Txt {
                    id: label
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label
                    tone: parent.on ? "accent" : th.containsMouse ? "ink" : "mid"
                    strong: parent.on
                    font.pixelSize: Theme.fBody
                }
                Count {
                    id: badge
                    anchors.left: label.right
                    anchors.leftMargin: Theme.s1
                    anchors.verticalCenter: parent.verticalCenter
                    value: modelData.count || 0
                    tone: "danger"
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 2
                    color: Theme.primary
                    visible: parent.on
                }
                MouseArea {
                    id: th
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: { root.current = modelData.key; root.picked(modelData.key) }
                }
            }
        }
    }
    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.split
        z: -1
    }
}
