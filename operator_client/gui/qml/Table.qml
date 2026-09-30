import QtQuick
import QtQuick.Controls.Basic
import "."

// THE BACKBONE (docs/UI-COMPONENTS.md). Sort by clicking a heading, filter from its funnel, page at
// the foot, and an Empty state that says what would be here.
//
//   columns: [{ title, key, width, mono, align, tag, avatar, tone(row), text(row), tip(row),
//              menu(row) -> [{key,label,danger,divided}], toggle(row) -> bool, filters: [] }]
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

    // ROW SELECTION. Off by default: a checkbox column on a table nobody acts on in bulk is a column
    // of noise. On, it is how a department-wide act is aimed -- the Engine takes many PCs at once.
    property bool selectable: false
    property string idKey: ""                 // which field identifies a row; "" means use the first column's
    property var selected: []                 // the ids, not the rows: rows are refetched, ids are not
    signal rowActivated(var row)
    signal selectionChanged(var selected)
    signal rowAction(string key, var row)
    signal rowToggled(var row, bool on)

    // what the page offers to do with the rows that are chosen; shown only while some are
    property alias bulk: bulkRow.data

    function idOf(row) { return String(row[idKey !== "" ? idKey : (columns[0] ? columns[0].key : "")]) }
    function isPicked(row) { return selected.indexOf(idOf(row)) >= 0 }
    function pick(row, on) {
        var id = idOf(row)
        var out = selected.filter(function (s) { return s !== id })
        if (on) out.push(id)
        selected = out
        selectionChanged(out)
    }
    function pickAll(on) {
        var out = []
        if (on) for (var i = 0; i < pageRows.length; i++) out.push(idOf(pageRows[i]))
        selected = out
        selectionChanged(out)
    }
    readonly property int pickedHere: pageRows.filter(function (r) { return root.isPicked(r) }).length

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
        var gutter = 2 * Theme.s3 + (selectable ? 16 + Theme.s3 : 0)
        return c.width ? c.width : Math.max(140, (width - fixedWidth - gutter) / flexCount)
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

        Check {
            visible: root.selectable
            anchors.left: parent.left
            anchors.leftMargin: Theme.s3
            anchors.verticalCenter: parent.verticalCenter
            checked: root.pickedHere > 0 && root.pickedHere === root.pageRows.length
            partial: root.pickedHere > 0 && root.pickedHere < root.pageRows.length
            onToggled: function (on) { root.pickAll(on) }
        }
        Row {
            anchors.fill: parent
            anchors.leftMargin: Theme.s3 + (root.selectable ? 16 + Theme.s3 : 0)
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

    // WHAT YOU CHOSE, AND WHAT YOU CAN DO WITH IT. It sits over the heading rather than above the
    // table, because the heading is what it replaces: while a set is chosen, sorting it is not the
    // question -- what to do with it is. The Engine already takes many machines at once.
    Rectangle {
        anchors.fill: head
        visible: root.selectable && root.selected.length > 0
        z: 3
        color: Theme.primarySoft
        radius: Theme.radius

        Check {
            id: allPicked
            anchors.left: parent.left
            anchors.leftMargin: Theme.s3
            anchors.verticalCenter: parent.verticalCenter
            checked: true
            partial: root.pickedHere < root.pageRows.length
            onToggled: root.pickAll(false)
        }
        Txt {
            anchors.left: allPicked.right
            anchors.leftMargin: Theme.s3
            anchors.verticalCenter: parent.verticalCenter
            text: Theme.many(root.selected.length, "chosen", "chosen")
            strong: true
            font.pixelSize: Theme.fSmall
        }
        Row {
            id: bulkRow
            anchors.right: drop.left
            anchors.rightMargin: Theme.s2
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.s2
        }
        Btn {
            id: drop
            kind: "text"
            small: true
            text: "Clear"
            anchors.right: parent.right
            anchors.rightMargin: Theme.s2
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.pickAll(false)
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
            color: hover.containsMouse ? Theme.hover : "transparent"

            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.split }

            // MouseArea, not TapHandler. A TapHandler reacts to any press over its item, even one
            // that landed on a dialog sitting on top of it -- so opening a dropdown in a modal could
            // also open this row's drawer behind it. A MouseArea only hears the press when it is the
            // topmost thing under the cursor, which is the rule a row actually wants.
            MouseArea {
                id: hover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.rowActivated(rowItem.modelData)
            }

            Check {
                visible: root.selectable
                anchors.left: parent.left
                anchors.leftMargin: Theme.s3
                anchors.verticalCenter: parent.verticalCenter
                checked: root.isPicked(rowItem.modelData)
                onToggled: function (on) { root.pick(rowItem.modelData, on) }
            }
            Row {
                anchors.fill: parent
                anchors.leftMargin: Theme.s3 + (root.selectable ? 16 + Theme.s3 : 0)
                anchors.rightMargin: Theme.s3
                Repeater {
                    model: root.columns
                    delegate: Item {
                        id: cell
                        required property var modelData          // the COLUMN
                        width: root.colWidth(cell.modelData)
                        height: rowItem.height

                        Txt {
                            visible: !cell.modelData.tag && !cell.modelData.menu && !cell.modelData.toggle
                            anchors.left: cell.modelData.avatar ? face.right : parent.left
                            anchors.leftMargin: cell.modelData.avatar ? Theme.s2 : 0
                            anchors.verticalCenter: parent.verticalCenter
                            width: Math.max(20, parent.width - Theme.s3
                                            - (cell.modelData.avatar ? 22 + Theme.s2 : 0))
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
                        // a person is a face and a name, because a column of names all looks alike
                        Avatar {
                            id: face
                            visible: !!cell.modelData.avatar
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            size: 22
                            name: root.cellText(cell.modelData, rowItem.modelData)
                            muted: cell.modelData.muted ? !!cell.modelData.muted(rowItem.modelData) : false
                        }
                        // the acts on this row, without opening it
                        RowMenu {
                            visible: !!cell.modelData.menu
                            anchors.right: parent.right
                            anchors.rightMargin: Theme.s2
                            anchors.verticalCenter: parent.verticalCenter
                            items: cell.modelData.menu ? cell.modelData.menu(rowItem.modelData) : []
                            onChose: function (key) { root.rowAction(key, rowItem.modelData) }
                        }
                        // on or off, in the row, because that is where the thing being switched is
                        Toggle {
                            visible: !!cell.modelData.toggle
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            on: cell.modelData.toggle ? !!cell.modelData.toggle(rowItem.modelData) : false
                            onToggled: function (v) { root.rowToggled(rowItem.modelData, v) }
                        }
                        // the full value of something the column had to cut short
                        Tip {
                            text: cell.modelData.tip ? cell.modelData.tip(rowItem.modelData) : ""
                            over: cell
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
