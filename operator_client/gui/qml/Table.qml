import QtQuick
import QtQuick.Controls.Basic
import "."

// THE BACKBONE (docs/UI-COMPONENTS.md). Sort by clicking a heading, filter from its funnel, page at
// the foot, and an Empty state that says what would be here.
//
//   columns: [{ title, key, width, mono, align, tag, tone(row)->string, text(row)->string, filters: [] }]
//   width 0 (or absent) means "share what is left"
Item {
    id: root

    property var columns: []
    property var rows: []
    property int pageSize: 20
    property bool loading: false
    property string emptyText: "Nothing here yet"
    property string emptyHint: ""
    property int sortColumn: -1
    property bool sortDescending: false
    property var activeFilters: ({})
    signal rowActivated(var row)

    readonly property var filtered: {
        var out = []
        for (var i = 0; i < rows.length; i++) {
            var keep = true
            for (var k in activeFilters)
                if (activeFilters[k] !== "" && String(rows[i][k]) !== String(activeFilters[k])) keep = false
            if (keep) out.push(rows[i])
        }
        if (sortColumn >= 0 && sortColumn < columns.length) {
            var key = columns[sortColumn].key
            out = out.slice().sort(function (a, b) {
                var x = a[key], y = b[key]
                var c = (x === y) ? 0 : (x > y ? 1 : -1)
                return sortDescending ? -c : c
            })
        }
        return out
    }
    readonly property var pageRows: filtered.slice(pager.page * pageSize, pager.page * pageSize + pageSize)
    readonly property int fixedWidth: {
        var w = 0
        for (var i = 0; i < columns.length; i++) w += (columns[i].width || 0)
        return w
    }
    readonly property int flexCount: {
        var n = 0
        for (var i = 0; i < columns.length; i++) if (!columns[i].width) n++
        return Math.max(1, n)
    }
    function colWidth(c) {
        return c.width ? c.width : Math.max(140, (width - fixedWidth - 2 * Theme.s3) / flexCount)
    }
    function cellText(c, row) {
        if (!row) return ""
        return c.text ? c.text(row) : (row[c.key] === undefined ? "" : String(row[c.key]))
    }
    function cellTone(c, row) { return (c.tone && row) ? c.tone(row) : "ink" }
    function sortBy(i) {
        if (sortColumn === i) sortDescending = !sortDescending
        else { sortColumn = i; sortDescending = false }
    }
    function setFilter(key, value) {
        var f = {}
        for (var k in activeFilters) f[k] = activeFilters[k]
        if (value === "") delete f[key]
        else f[key] = value
        activeFilters = f
        pager.page = 0
    }

    implicitHeight: 38 + 40 * Math.max(3, pageRows.length) + 44

    // --- the heading ------------------------------------------------------------------------------
    Rectangle {
        id: head
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 38
        color: Theme.fill
        radius: Theme.radius
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.split }

        Row {
            anchors.fill: parent
            anchors.leftMargin: Theme.s3
            anchors.rightMargin: Theme.s3
            Repeater {
                model: root.columns
                delegate: Item {
                    id: headCell
                    required property var modelData
                    required property int index
                    width: root.colWidth(modelData)
                    height: head.height

                    MouseArea {
                        anchors.fill: parent
                        anchors.rightMargin: modelData.filters ? 24 : 0
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.sortBy(headCell.index)
                    }
                    Row {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 4
                        Txt {
                            text: headCell.modelData.title
                            strong: true
                            font.pixelSize: Theme.fSmall
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Icon {
                            visible: root.sortColumn === headCell.index
                            name: root.sortDescending ? "caretd" : "caretu"
                            size: 12
                            color: Theme.primary
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    Icon {
                        id: funnel
                        visible: !!headCell.modelData.filters
                        name: "filter"
                        size: 12
                        color: root.activeFilters[headCell.modelData.key] !== undefined ? Theme.primary : Theme.quiet
                        anchors.right: parent.right
                        anchors.rightMargin: Theme.s3
                        anchors.verticalCenter: parent.verticalCenter
                        MouseArea {
                            anchors.fill: parent
                            anchors.margins: -5
                            cursorShape: Qt.PointingHandCursor
                            onClicked: filterMenu.open()
                        }
                        Menu {
                            id: filterMenu
                            y: funnel.height + 8
                            MenuItem { text: "All"; onTriggered: root.setFilter(headCell.modelData.key, "") }
                            Repeater {
                                model: headCell.modelData.filters || []
                                delegate: MenuItem {
                                    required property var modelData
                                    text: String(modelData)
                                    onTriggered: root.setFilter(headCell.modelData.key, String(modelData))
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // --- the rows ----------------------------------------------------------------------------------
    ListView {
        id: body
        anchors.top: head.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: foot.top
        clip: true
        interactive: false
        model: root.loading ? [] : root.pageRows

        delegate: Rectangle {
            id: rowItem
            required property var modelData
            width: body.width
            height: 40
            color: hover.hovered ? Theme.hover : "transparent"

            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.split }
            HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.rowActivated(rowItem.modelData) }

            Row {
                anchors.fill: parent
                anchors.leftMargin: Theme.s3
                anchors.rightMargin: Theme.s3
                Repeater {
                    model: root.columns
                    delegate: Item {
                        id: cell
                        required property var modelData          // the COLUMN
                        width: root.colWidth(cell.modelData)
                        height: rowItem.height

                        Txt {
                            visible: !cell.modelData.tag
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            width: Math.max(20, parent.width - Theme.s3)
                            horizontalAlignment: cell.modelData.align === "right" ? Text.AlignRight : Text.AlignLeft
                            text: root.cellText(cell.modelData, rowItem.modelData)
                            mono: !!cell.modelData.mono
                            tone: root.cellTone(cell.modelData, rowItem.modelData)
                            font.pixelSize: cell.modelData.mono ? Theme.fSmall : Theme.fBody
                        }
                        Tag {
                            visible: !!cell.modelData.tag
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.cellText(cell.modelData, rowItem.modelData)
                            tone: root.cellTone(cell.modelData, rowItem.modelData)
                        }
                    }
                }
            }
        }
    }

    Skeleton {
        visible: root.loading
        anchors.top: head.bottom
        anchors.topMargin: Theme.s4
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Theme.s3
        anchors.rightMargin: Theme.s3
        rows: 6
    }

    Empty {
        visible: !root.loading && root.filtered.length === 0
        anchors.top: head.bottom
        anchors.topMargin: Theme.s5
        anchors.horizontalCenter: parent.horizontalCenter
        width: 320
        text: root.emptyText
        hint: root.emptyHint
    }

    // --- the foot ------------------------------------------------------------------------------------
    Item {
        id: foot
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 44

        Pagination {
            id: pager
            anchors.right: parent.right
            anchors.rightMargin: Theme.s2
            anchors.verticalCenter: parent.verticalCenter
            visible: root.filtered.length > 0
            total: root.filtered.length
            pageSize: root.pageSize
        }
    }
}
