import QtQuick
import "."

// Every table carries one. Page size is a choice; the position is always said in words.
Row {
    id: root
    property int total: 0
    property int pageSize: 20
    property int page: 0                      // zero-based
    readonly property int pages: Math.max(1, Math.ceil(total / Math.max(1, pageSize)))
    readonly property int from: total === 0 ? 0 : page * pageSize + 1
    readonly property int to: Math.min(total, (page + 1) * pageSize)

    spacing: Theme.s2
    onTotalChanged: if (page > pages - 1) page = 0

    Txt {
        anchors.verticalCenter: parent.verticalCenter
        text: root.total === 0 ? "" : root.from + "\u2013" + root.to + " of " + root.total
        tone: "mid"
        font.pixelSize: Theme.fSmall
        rightPadding: Theme.s2
    }
    Btn {
        small: true
        kind: "text"
        iconName: "chevl"
        enabled: root.page > 0
        onClicked: root.page = Math.max(0, root.page - 1)
    }
    Txt {
        anchors.verticalCenter: parent.verticalCenter
        text: (root.page + 1) + " / " + root.pages
        tone: "mid"
        font.pixelSize: Theme.fSmall
    }
    Btn {
        small: true
        kind: "text"
        iconName: "chevr"
        enabled: root.page < root.pages - 1
        onClicked: root.page = Math.min(root.pages - 1, root.page + 1)
    }
}
