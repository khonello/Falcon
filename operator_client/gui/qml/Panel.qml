import QtQuick
import "."

// A chart's container: a title, a quiet note beside it, what is drawn, and at the foot the legend
// that says what the colours mean. Every chart on a dashboard sits in one of these, so a panel is
// the only surface a chart ever lands on.
Rectangle {
    id: root

    property string title: ""
    property string note: ""
    // How much of this panel is picture and how much is words (board P01). A page declares its
    // panels in reading order and the density must never decrease along it: shape at the top left,
    // sentences at the bottom right. `tests/test_operator_gui.py` holds every page to that.
    //   1 Figure  a number and a word      2 Chart        a shape and its legend
    //   3 Chart, told  a shape and its one sentence       4 Reading  the words
    property int density: 0
    // A panel is never blank. When there is nothing to draw the chart keeps its own structure --
    // its rows, its lanes, its track -- quietened, and the notice is laid OVER it, never in place
    // of it. A zero is not this case: a zero is a result and is drawn normally.
    property string notice: ""
    property string noticeSub: ""
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
        opacity: root.notice === "" ? 1 : 0.28
    }

    Column {
        visible: root.notice !== ""
        anchors.centerIn: column
        width: column.width - 24
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
            text: root.noticeSub
            visible: text !== ""
            color: Theme.faint
            font.pixelSize: Theme.fMeta
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
        }
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
