import QtQuick
import "."

// THE HIERARCHY WHERE IT IS A LIST. Department, its Admins, their machines -- indented, foldable, and
// no picture. A picture of a tree is only worth drawing when the shape itself is the point.
Column {
    id: root
    property var nodes: []                // [{key, label, sub, depth, kids, tone}]
    property var open: ({})               // key -> bool
    property string current: ""
    signal picked(string key)

    spacing: 0

    function toggle(key) {
        var copy = {}
        for (var k in open) copy[k] = open[k]
        copy[key] = !copy[key]
        open = copy
    }
    // only what its parents let through
    readonly property var shown: {
        var out = []
        var hideBelow = -1
        for (var i = 0; i < nodes.length; i++) {
            var n = nodes[i]
            if (hideBelow >= 0 && n.depth > hideBelow) continue
            hideBelow = -1
            out.push(n)
            if (n.kids && !open[n.key]) hideBelow = n.depth
        }
        return out
    }

    Repeater {
        model: root.shown
        delegate: Rectangle {
            required property var modelData
            width: root.width
            height: 30
            radius: Theme.radiusSm
            color: modelData.key === root.current ? Theme.primarySoft
                   : nh.containsMouse ? Theme.hover : "transparent"

            Icon {
                id: caret
                x: Theme.s3 + modelData.depth * Theme.s4
                anchors.verticalCenter: parent.verticalCenter
                visible: !!modelData.kids
                name: root.open[modelData.key] ? "chevd" : "chevr"
                size: 12
                color: Theme.quiet
            }
            Txt {
                id: what
                anchors.left: parent.left
                anchors.leftMargin: Theme.s3 + modelData.depth * Theme.s4 + 18
                anchors.verticalCenter: parent.verticalCenter
                text: modelData.label
                tone: modelData.tone || "ink"
                strong: modelData.key === root.current
                font.pixelSize: Theme.fSmall
            }
            Txt {
                anchors.left: what.right
                anchors.leftMargin: Theme.s2
                anchors.right: parent.right
                anchors.rightMargin: Theme.s3
                anchors.verticalCenter: parent.verticalCenter
                text: modelData.sub || ""
                tone: "quiet"
                font.pixelSize: 11
            }
            MouseArea {
                id: nh
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (modelData.kids) root.toggle(modelData.key)
                    root.current = modelData.key
                    root.picked(modelData.key)
                }
            }
        }
    }
}
