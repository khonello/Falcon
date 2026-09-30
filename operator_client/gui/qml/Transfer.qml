import QtQuick
import "."

// TWO LISTS AND A DIRECTION: which machines an automation watches, who listens on a channel. Worth
// its width only when the chosen set matters as much as the unchosen one -- otherwise it is a Select.
Item {
    id: root
    property var all: []                  // [{key, label}]
    property var chosen: []               // [key]
    property string leftTitle: "Not chosen"
    property string rightTitle: "Chosen"
    signal changed(var chosen)

    implicitHeight: 220

    function has(k) { return chosen.indexOf(k) >= 0 }
    function move(k, into) {
        var out = chosen.filter(function (c) { return c !== k })
        if (into) out.push(k)
        chosen = out
        changed(out)
    }

    Row {
        anchors.fill: parent
        spacing: Theme.s3

        Repeater {
            model: [false, true]
            delegate: Rectangle {
                id: side
                required property var modelData
                width: (root.width - Theme.s3) / 2
                height: root.height
                radius: Theme.radius
                color: Theme.surface
                border.width: 1
                border.color: Theme.split

                readonly property var rows: root.all.filter(function (o) {
                    return root.has(o.key) === modelData
                })

                Item {
                    id: head
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 30
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1
                                color: Theme.split }
                    Txt {
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.s3
                        anchors.verticalCenter: parent.verticalCenter
                        text: (modelData ? root.rightTitle : root.leftTitle)
                              + "  " + side.rows.length
                        tone: "mid"
                        font.pixelSize: 11
                    }
                }
                Flickable {
                    anchors.top: head.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: Theme.s1
                    contentHeight: col.implicitHeight
                    clip: true

                    Column {
                        id: col
                        width: parent.width

                        Repeater {
                            model: side.rows
                            delegate: Rectangle {
                                required property var modelData
                                width: col.width
                                height: 28
                                radius: Theme.radiusSm
                                color: rh.containsMouse ? Theme.hover : "transparent"

                                Txt {
                                    anchors.left: parent.left
                                    anchors.leftMargin: Theme.s2
                                    anchors.right: arrow.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.label
                                    font.pixelSize: Theme.fSmall
                                }
                                Icon {
                                    id: arrow
                                    anchors.right: parent.right
                                    anchors.rightMargin: Theme.s2
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: rh.containsMouse
                                    name: root.has(modelData.key) ? "chevl" : "chevr"
                                    size: 12
                                    color: Theme.primary
                                }
                                MouseArea {
                                    id: rh
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.move(modelData.key, !root.has(modelData.key))
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
