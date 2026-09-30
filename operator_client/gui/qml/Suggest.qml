import QtQuick
import QtQuick.Controls.Basic
import "."

// TYPING, WITH WHAT IS ALREADY KNOWN OFFERED UNDERNEATH. For the things a Select cannot hold -- a
// file name out of an index of thousands, a hostname. Not a Select: what you type is allowed to be
// something the list does not have.
Item {
    id: root
    property var options: []              // [string]
    property alias text: field.text
    property string placeholder: ""
    property int most: 6
    signal chose(string value)

    implicitWidth: 260
    implicitHeight: Theme.control

    readonly property var matches: {
        if (field.text === "") return []
        var q = field.text.toLowerCase()
        return options.filter(function (o) { return String(o).toLowerCase().indexOf(q) >= 0 })
                      .slice(0, root.most)
    }

    Field {
        id: field
        anchors.fill: parent
        placeholderText: root.placeholder
        onTextChanged: if (root.matches.length > 0) pop.open(); else pop.close()
    }

    Popup {
        id: pop
        y: root.height + 4
        width: root.width
        padding: Theme.s1
        height: Math.min(root.matches.length * 30 + 2 * Theme.s1, 200)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

        background: Rectangle {
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.split
            MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true }
        }

        Column {
            width: parent.width

            Repeater {
                model: root.matches
                delegate: Rectangle {
                    required property var modelData
                    width: parent.width
                    height: 30
                    radius: Theme.radiusSm
                    color: sh.containsMouse ? Theme.hover : "transparent"

                    Txt {
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.s2
                        anchors.right: parent.right
                        anchors.rightMargin: Theme.s2
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData
                        font.pixelSize: Theme.fSmall
                    }
                    MouseArea {
                        id: sh
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { field.text = modelData; pop.close(); root.chose(String(modelData)) }
                    }
                }
            }
        }
    }
}
