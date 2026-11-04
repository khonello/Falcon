import QtQuick
import "."

// antd's Slider: a 4px rail, the part up to the value in the accent, a ring for the handle, and two marks under the ends.
Item {
    id: root
    property real from: 0
    property real to: 100
    property real stepSize: 1
    property real value: 0
    property var marks: []                      // [the word at the start, the word at the end]
    signal moved(real value)
    implicitWidth: 200
    implicitHeight: marks.length ? 38 : 22
    readonly property real at: to > from ? Math.max(0, Math.min(1, (value - from) / (to - from))) : 0
    Rectangle { x: 5; y: 9; width: parent.width - 10; height: 4; radius: 2; color: Theme.fillHover }
    Rectangle { x: 5; y: 9; width: (parent.width - 10) * root.at; height: 4; radius: 2; color: Theme.alpha(Theme.accent, ma.containsMouse ? 1 : 0.75) }
    Rectangle { x: (parent.width - 10) * root.at - 1; y: 5; width: 12; height: 12; radius: 6; color: Theme.surface; border.width: 2; border.color: Theme.accent }
    Txt { visible: root.marks.length > 0; y: 22; text: root.marks[0] || ""; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
    Txt { visible: root.marks.length > 1; anchors.right: parent.right; y: 22; text: root.marks[1] || ""; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
    MouseArea {
        id: ma
        width: parent.width; height: 22
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        function put(x) {
            var v = root.from + Math.max(0, Math.min(1, (x - 5) / (root.width - 10))) * (root.to - root.from)
            root.moved(Math.max(root.from, Math.min(root.to, Math.round((v - root.from) / root.stepSize) * root.stepSize + root.from)))
        }
        onPressed: function (e) { put(e.x) }
        onPositionChanged: function (e) { if (pressed) put(e.x) }
    }
}
