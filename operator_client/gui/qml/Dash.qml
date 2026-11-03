import QtQuick
import "."

// A DASHED HAIRLINE (CSS's 1px dashed border): 3px dashes 3px apart.
Row {
    id: root
    property color c: Theme.borderStrong
    width: parent ? parent.width : 100
    height: 1
    spacing: 3
    clip: true
    Repeater { model: Math.ceil(root.width / 6); Rectangle { width: 3; height: 1; color: root.c } }
}
