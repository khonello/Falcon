import QtQuick
import QtQuick.Controls.Basic
import "."

// PICKING SOMETHING OUT OF THE HIERARCHY. A folder in the file index, or a machine inside a
// department -- the same Select, but its list is a Tree, because a flat list of forty machines with
// no departments in it is not a list anybody can use.
//
// (This is also antd's Cascader case. One control, not two: a cascade is a tree drawn sideways, and
// the tree is the shape people already know from the sider.)
Item {
    id: root
    property var nodes: []                // Tree's shape: [{key, label, sub, depth, kids, pickable}]
    property var value: null
    property string placeholder: "Pick one"
    property bool invalid: false
    signal picked(var key)

    implicitWidth: 260
    implicitHeight: Theme.control

    function labelFor(k) {
        for (var i = 0; i < nodes.length; i++)
            if (nodes[i].key === k) return nodes[i].label
        return ""
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: root.invalid ? Theme.danger
                      : pop.opened ? Theme.primary
                      : hov.containsMouse ? Theme.primaryHover : Theme.border
        Behavior on border.color { ColorAnimation { duration: Theme.durFast } }

        Txt {
            anchors.left: parent.left
            anchors.leftMargin: Theme.s3
            anchors.right: chev.left
            anchors.rightMargin: Theme.s2
            anchors.verticalCenter: parent.verticalCenter
            text: root.value === null ? root.placeholder : root.labelFor(root.value)
            tone: root.value === null ? "quiet" : "ink"
        }
        Icon {
            id: chev
            name: "chevd"
            size: 14
            color: Theme.quiet
            anchors.right: parent.right
            anchors.rightMargin: Theme.s3
            anchors.verticalCenter: parent.verticalCenter
        }
        MouseArea {
            id: hov
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: pop.opened ? pop.close() : pop.open()
        }
    }

    Popup {
        id: pop
        y: root.height + 4
        width: Math.max(root.width, 280)
        padding: Theme.s1
        height: Math.min(tree.implicitHeight + 2 * Theme.s1, 260)

        background: Rectangle {
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.split
            MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true }
        }

        Flickable {
            anchors.fill: parent
            contentHeight: tree.implicitHeight
            clip: true

            Tree {
                id: tree
                width: parent.width
                nodes: root.nodes
                current: root.value === null ? "" : String(root.value)
                onPicked: function (key) {
                    for (var i = 0; i < root.nodes.length; i++)
                        if (String(root.nodes[i].key) === key && root.nodes[i].pickable !== false) {
                            root.value = root.nodes[i].key
                            root.picked(root.nodes[i].key)
                            pop.close()
                            return
                        }
                }
            }
        }
    }
}
