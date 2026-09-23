import QtQuick
import "."

// Every body has the same shape: a breadcrumb, one large title with its glyph, the pills, then the
// content beside the lane. The body column is a fixed width, so nothing reflows when the detail
// card's contents change.
Item {
    id: root

    property var crumbs: []                 // ["Operations", "Ama"] -- the last one is where you are
    property string title: ""
    property string sub: ""
    property string glyph: ""
    property string glyphTone: ""
    property string initials: ""
    property alias trailing: trailLoader.sourceComponent
    property alias actions: actionLoader.sourceComponent
    property var pills: []
    property int pill: 0
    signal pillPicked(int index)

    default property alias content: content.data
    property alias lane: laneColumn.data
    property alias strip: stripColumn.data      // spans the whole body, above the pills

    Column {
        anchors.fill: parent
        anchors.leftMargin: Theme.s6
        anchors.rightMargin: Theme.s6
        anchors.topMargin: Theme.s5
        spacing: 0

        // the breadcrumb drill: one level at a time, the last one is you
        Row {
            spacing: 6
            height: crumbs.length > 0 ? 22 : 0
            visible: crumbs.length > 0

            Repeater {
                model: root.crumbs
                delegate: Row {
                    required property string modelData
                    required property int index
                    spacing: 6
                    Icon {
                        name: "chev"
                        color: Theme.faint
                        size: 12
                        visible: index > 0
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Txt {
                        text: modelData
                        color: index === root.crumbs.length - 1 ? Theme.ink : Theme.faint
                        font.pixelSize: Theme.fBody
                        font.weight: index === root.crumbs.length - 1 ? Font.DemiBold : Font.Normal
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }

        Item { width: 1; height: 10; visible: root.crumbs.length > 0 }

        // the title, with an avatar or a glyph
        Item {
            width: parent.width
            height: 48

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 14

                Avatar {
                    initials: root.initials
                    size: 40
                    visible: root.initials !== ""
                    anchors.verticalCenter: parent.verticalCenter
                }
                Rectangle {
                    width: 40
                    height: 40
                    radius: Theme.radiusMd
                    color: root.glyphTone === "" ? Theme.ground : Theme.toneSoft(root.glyphTone)
                    visible: root.glyph !== "" && root.initials === ""
                    anchors.verticalCenter: parent.verticalCenter
                    Icon {
                        anchors.centerIn: parent
                        name: root.glyph
                        color: root.glyphTone === "" ? Theme.dim : Theme.tone(root.glyphTone)
                        size: 20
                    }
                }
                Column {
                    spacing: 3
                    anchors.verticalCenter: parent.verticalCenter
                    Row {
                        spacing: 10
                        Txt {
                            text: root.title
                            font.pixelSize: Theme.fTitle
                            font.weight: Font.DemiBold
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Loader { id: trailLoader; anchors.verticalCenter: parent.verticalCenter }
                    }
                    Txt {
                        text: root.sub
                        visible: root.sub !== ""
                        color: Theme.faint
                        font.pixelSize: Theme.fBody
                    }
                }
            }
            Loader {
                id: actionLoader
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Item { width: 1; height: 16 }

        // the entity strip runs the full width: it belongs to the level, not to one column
        Column {
            id: stripColumn
            width: parent.width
            spacing: 0
        }

        Item { width: 1; height: stripColumn.children.length > 0 ? 18 : 0 }

        Pills {
            width: parent.width
            model: root.pills
            current: root.pill
            visible: root.pills.length > 0
            onPicked: function (i) { root.pillPicked(i) }
        }

        Item { width: 1; height: root.pills.length > 0 ? 14 : 0 }

        // the body and its lane: the lane is always there, so the body never reflows
        Row {
            width: parent.width
            spacing: 22

            Column {
                id: content
                width: Theme.bodyWidth
                spacing: 8
            }
            Column {
                id: laneColumn
                width: Theme.laneWidth
                spacing: 12
            }
        }
    }
}
