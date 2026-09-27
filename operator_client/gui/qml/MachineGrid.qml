import QtQuick
import "."

// ONE DEPARTMENT'S WHOLE FLEET, MAXIMISED (design/PATTERNS.md 3a; board RO06).
//
// Every machine at full size in a grid that pages DOWN by rows -- a page at a time, so 200 machines is seven pages, not
// fifty -- with plain-text filters ("All 48 · Behind 4") and a "1-32 of 48" position. The order is the caller's stable
// one (by hostname). The bottom edge names any hidden machine that needs someone.
//
//   machines  [{ label, status, name, line, lineTone }]   -- status: ok | free | warn | danger | entered
Item {
    id: root

    property var machines: []
    property int markSize: 58
    property int cellWidth: 92
    property int cellHeight: 88
    property int gap: 10
    property string filter: "all"           // all | behind
    property string filterLabel: "Behind"   // what the narrowed set is called here ("Needs you" on a department)
    property int page: 0

    readonly property var shownList: filter === "all" ? machines
                                     : machines.filter(function (m) { return m.status === "warn" || m.status === "danger" })
    readonly property int behindCount: machines.filter(function (m) { return m.status === "warn" || m.status === "danger" }).length
    readonly property int cols: Math.max(1, Math.floor((width + gap) / (cellWidth + gap)))
    readonly property int rows: Math.max(1, Math.floor((height - 40 - 34 + gap) / (cellHeight + gap)))
    readonly property int perPage: cols * rows
    readonly property int pages: Math.max(1, Math.ceil(shownList.length / perPage))
    readonly property int from: page * perPage
    readonly property int to: Math.min(shownList.length, from + perPage)
    readonly property string hiddenNeeds: {
        var names = []
        for (var i = to; i < shownList.length; i++)
            if (shownList[i].status === "warn" || shownList[i].status === "danger") names.push(shownList[i].name || shownList[i].label)
        return names.length === 0 ? "" : names.length === 1 ? names[0] + " behind" : names.length + " behind"
    }
    onFilterChanged: page = 0
    onShownListChanged: if (page >= pages) page = 0

    activeFocusOnTab: true
    Keys.onDownPressed: if (page < pages - 1) page++
    Keys.onUpPressed: if (page > 0) page--

    // the filters, plain text, and where you are
    Item {
        id: head
        width: parent.width
        height: 28
        Row {
            spacing: 20
            anchors.verticalCenter: parent.verticalCenter
            Repeater {
                model: [{ key: "all", text: "All " + root.machines.length }, { key: "behind", text: root.filterLabel + " " + root.behindCount }]
                delegate: Txt {
                    required property var modelData
                    text: modelData.text
                    color: root.filter === modelData.key ? Theme.ink : Theme.faint
                    font.pixelSize: Theme.fRow - 1
                    font.weight: root.filter === modelData.key ? Font.DemiBold : Font.Normal
                    MouseArea { anchors.fill: parent; anchors.margins: -4; cursorShape: Qt.PointingHandCursor
                                onClicked: root.filter = modelData.key }
                }
            }
        }
        Txt {
            objectName: "gridPosition"
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: root.shownList.length === 0 ? "none" : (root.from + 1) + "–" + root.to + " of " + root.shownList.length
            color: Theme.faint; monospace: true; font.pixelSize: Theme.fMeta
        }
    }

    Grid {
        id: grid
        anchors.top: head.bottom
        anchors.topMargin: 12
        anchors.horizontalCenter: parent.horizontalCenter
        columns: root.cols
        spacing: root.gap
        Repeater {
            model: root.shownList.slice(root.from, root.to)
            delegate: Item {
                required property var modelData
                width: root.cellWidth
                height: root.cellHeight
                MachineMark {
                    anchors.horizontalCenter: parent.horizontalCenter
                    size: root.markSize
                    label: modelData.label || ""
                    status: modelData.status || "ok"
                    name: modelData.name || ""
                    line: modelData.line || ""
                    lineTone: modelData.lineTone || ""
                }
            }
        }
    }

    // the bottom edge pages down; the top of the grid pages back when not on the first page
    Rectangle {
        objectName: "gridPagerDown"
        anchors.bottom: parent.bottom
        width: parent.width
        height: 32
        radius: 12
        visible: root.page < root.pages - 1
        gradient: Gradient {
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 1.0; color: Qt.rgba(1, 1, 1, downArea.containsMouse ? 0.09 : 0.05) }
        }
        Row {
            anchors.centerIn: parent
            spacing: 8
            Icon { name: "chevd"; size: 14; color: Theme.dim; anchors.verticalCenter: parent.verticalCenter }
            Txt { text: (root.shownList.length - root.to) + " more"; color: Theme.dim; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
            Txt { visible: root.hiddenNeeds !== ""; text: root.hiddenNeeds; color: Theme.warn; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
        }
        MouseArea { id: downArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.page++ }
    }
    Txt {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        visible: root.page > 0 && root.page === root.pages - 1
        text: "Back to the first page"
        color: Theme.accent; font.pixelSize: Theme.fMeta
        MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: root.page = 0 }
    }
}
