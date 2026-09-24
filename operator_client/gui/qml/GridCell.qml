import QtQuick
import "."

// One cell of the Overview's grid. Its title sits ABOVE the cell, on the frame, so the cell itself
// is a clean surface holding nothing but the drawing. The state phrase on the right is generated
// (core/narrate.py's `brief`) and is the only place colour appears outside a chart.
//
// A cell is never blank: with nothing to draw, the chart keeps its own structure and the notice is
// laid over it.
Item {
    id: root

    property string title: ""
    property var narration: ({})
    // A cell opens only when there is something to explain. "Out of place" with no violations has
    // nothing to say at length, so it stays shut rather than recomposing into panels of nothing.
    property bool openable: false
    property bool topAlign: false
    signal opened()
    default property alias content: body.data
    readonly property string brief: narration.brief || ""
    readonly property string tone: narration.tone || ""
    readonly property string notice: narration.state === "empty" ? (narration.note || "Nothing recorded yet")
                                     : narration.state === "thin" ? (narration.note || "Not enough to draw yet")
                                     : ""

    Item {
        id: head
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        height: 24

        Txt {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            text: root.title
            color: "#ffffff"
            font.pixelSize: Theme.fSection
            font.weight: Font.DemiBold
        }
        Icon {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            name: "chev"
            color: Qt.rgba(1, 1, 1, area.containsMouse ? 0.7 : 0.3)
            size: 14
            visible: root.openable
        }
        Txt {
            anchors.right: parent.right
            anchors.rightMargin: root.openable ? 20 : 0
            anchors.verticalCenter: parent.verticalCenter
            text: root.brief
            color: root.tone === "" ? Qt.rgba(1, 1, 1, 0.45) : Theme.tone(root.tone)
            font.pixelSize: Theme.fBody
            font.weight: root.tone === "" ? Font.Normal : Font.Medium
        }
    }

    Rectangle {
        anchors.top: head.bottom
        anchors.topMargin: 9
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        radius: Theme.radiusXl
        color: area.containsMouse && root.openable ? Theme.pane : Theme.chartBg
        clip: true
        Behavior on color { ColorAnimation { duration: Theme.durFast } }

        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: root.openable
            cursorShape: root.openable ? Qt.PointingHandCursor : Qt.ArrowCursor
            acceptedButtons: root.openable ? Qt.LeftButton : Qt.NoButton
            onClicked: root.opened()
        }

        Item {
            id: bodyWrap
            anchors.fill: parent
            anchors.margins: 22
            opacity: root.notice === "" ? 1 : 0.28

            Column {
                id: body
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: (!root.topAlign && implicitHeight < parent.height)
                                        ? parent.verticalCenter : undefined
                anchors.top: (root.topAlign || implicitHeight >= parent.height) ? parent.top : undefined
                spacing: 14
            }
        }

        Column {
            visible: root.notice !== ""
            anchors.centerIn: parent
            width: parent.width - 48
            spacing: 4

            Txt {
                width: parent.width
                text: root.notice
                color: Theme.dim
                font.pixelSize: Theme.fBody
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
            }
            Txt {
                width: parent.width
                text: root.narration.sentence || ""
                color: Theme.faint
                font.pixelSize: Theme.fMeta
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                elide: Text.ElideNone
            }
        }
    }
}
