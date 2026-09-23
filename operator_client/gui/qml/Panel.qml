import QtQuick
import "."

// A chart's container: a title, a quiet note beside it, what is drawn, and at the foot the legend
// that says what the colours mean. Every chart on a dashboard sits in one of these, so a panel is
// the only surface a chart ever lands on.
Rectangle {
    id: root

    property string title: ""
    property string note: ""
    property alias foot: footColumn.data
    default property alias content: column.data

    radius: Theme.radiusLg
    color: Theme.chartBg
    implicitHeight: 50 + column.implicitHeight + (footColumn.children.length > 0 ? footColumn.implicitHeight + 14 : 0) + 16

    Row {
        id: head
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 18
        anchors.topMargin: 16
        height: 20
        spacing: 10

        Txt {
            text: root.title
            font.pixelSize: Theme.fRow
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            text: root.note
            color: Theme.faint
            font.pixelSize: Theme.fMeta
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    Column {
        id: column
        anchors.top: head.bottom
        anchors.topMargin: 14
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 18
        anchors.rightMargin: 18
        spacing: 12
    }

    Column {
        id: footColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 18
        anchors.rightMargin: 18
        anchors.bottomMargin: 16
        spacing: 8
    }
}
