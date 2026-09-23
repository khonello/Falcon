import QtQuick
import "."

// A section heading inside the sidebar.
Item {
    id: root

    property string title: ""
    property string count: ""
    property bool open: true

    width: parent ? parent.width : 0
    height: 30

    Row {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 14
        spacing: 7

        Icon {
            name: root.open ? "chevd" : "chev"
            color: Theme.faint
            size: 13
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            width: parent.width - 46
            text: root.title
            color: Theme.dim
            font.pixelSize: Theme.fMeta
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            text: root.count
            color: Theme.faint
            font.pixelSize: Theme.fSmall
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
