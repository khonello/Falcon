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
        Txt {
            anchors.right: parent.right
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
        color: Theme.chartBg
        clip: true

        Item {
            id: bodyWrap
            anchors.fill: parent
            anchors.margins: 22
            opacity: root.notice === "" ? 1 : 0.28

            Column {
                id: body
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: implicitHeight < parent.height ? parent.verticalCenter : undefined
                anchors.top: implicitHeight < parent.height ? undefined : parent.top
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
