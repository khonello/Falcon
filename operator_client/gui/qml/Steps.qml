import QtQuick
import "."

// WHERE YOU ARE IN SOMETHING THAT HAS AN ORDER: a numbered circle per step with its title and one
// line under it, a line between them. A done step shows a tick; one left with a problem is red. A click
// goes to that step. steps: [{title, desc, error?}] or strings.
Item {
    id: root
    property var steps: []
    property int current: 0
    property bool clickable: true
    signal picked(int index)
    readonly property var items: steps.map(function (s) { return typeof s === "object" ? s : { title: s, desc: "" } })
    implicitHeight: 46

    Row {
        anchors.fill: parent
        Repeater {
            model: root.items
            delegate: Item {
                id: st
                required property var modelData
                required property int index
                readonly property bool done: index < root.current
                readonly property bool here: index === root.current
                readonly property bool err: !!modelData.error
                width: root.width / root.items.length
                height: root.height
                Rectangle {
                    id: pip
                    width: 26; height: 26; radius: 13
                    color: st.here ? Theme.accent : st.err ? Theme.surface : st.done ? Theme.surface : Theme.surface3
                    border.width: st.done || st.err ? 1 : 0
                    border.color: st.err ? Theme.crit : Theme.accent
                    Txt { anchors.centerIn: parent; visible: !st.done || st.err; text: st.err ? "!" : String(index + 1); elide: Text.ElideNone
                          color: st.here ? Theme.inverse : st.err ? Theme.crit : Theme.text3; font.pixelSize: 12; font.weight: Font.Medium }
                    Icon { anchors.centerIn: parent; visible: st.done && !st.err; name: "check"; size: 13; color: Theme.accent }
                }
                Column {
                    x: 34
                    width: parent.width - 34
                    spacing: 1
                    Row {
                        width: parent.width
                        spacing: 8
                        Txt { id: tt; text: st.modelData.title; elide: Text.ElideNone; font.weight: st.here ? Font.Medium : Font.Normal
                              color: st.err ? Theme.crit : st.here || st.done ? Theme.text : Theme.text3; topPadding: 3 }
                        Rectangle { visible: index < root.items.length - 1; width: Math.max(0, parent.width - tt.width - 16); height: 1; y: 13; color: st.done ? Theme.accent : Theme.border }
                    }
                    Txt { text: st.modelData.desc || ""; visible: text !== ""; color: Theme.text3; font.pixelSize: 12; width: parent.width - 10 }
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: root.clickable
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.picked(index)
                }
            }
        }
    }
}
