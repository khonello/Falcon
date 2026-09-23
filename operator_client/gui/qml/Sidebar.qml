import QtQuick
import QtQuick.Controls
import "."

// The sidebar: a heading, then accordion sections of rows. It says what the body is a list of, and
// keeps a stable order -- it never resorts itself by state, so positions stay learnable.
Rectangle {
    id: root

    property string title: ""
    property bool plus: true
    default property alias content: column.data
    signal plusClicked()

    color: Theme.side

    Item {
        id: head
        width: parent.width
        height: 48
        anchors.top: parent.top

        Txt {
            anchors.left: parent.left
            anchors.leftMargin: Theme.s4
            anchors.verticalCenter: parent.verticalCenter
            text: root.title
            font.pixelSize: Theme.fSection
            font.weight: Font.Bold
        }
        IconBtn {
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            iconName: "plus"
            size: 26
            visible: root.plus
            onClicked: root.plusClicked()
        }
    }

    ScrollView {
        anchors.top: head.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: legend.top
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        Column {
            id: column
            width: root.width
            spacing: 2
        }
    }

    // the one legend for the session vocabulary
    Column {
        id: legend
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Theme.s3
        spacing: 6

        Rectangle { width: parent.width; height: 1; color: Theme.line }
        Flow {
            width: parent.width
            spacing: 10
            Repeater {
                model: ["free", "native", "traversed", "assisted", "su"]
                delegate: Row {
                    required property string modelData
                    spacing: 5
                    Icon {
                        name: Theme.sessionIcon(modelData)
                        color: Theme.sessionColor(modelData)
                        size: 13
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Txt {
                        text: Theme.sessionWord(modelData)
                        color: Theme.faint
                        font.pixelSize: Theme.fSmall
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }
    }

    Rectangle {
        anchors.right: parent.right
        width: 1
        height: parent.height
        color: Theme.line
    }
}
