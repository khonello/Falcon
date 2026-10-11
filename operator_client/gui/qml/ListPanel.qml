import QtQuick
import "."

// THE STANDARD LIST (decided 6 Oct 2026). One framed panel with a title and a short subtitle; a search
// box and the one primary action on the right of the header; six rows a page at a fixed height.
// Columns: the item (icon, name, one small grey mono line under it), up to three plain columns in
// quiet grey (a bar column has a grey bar and its figure), then "Now": a dot and a few words, green
// when fine, red when someone has to act, grey when waiting. A row selects; there is no per-row button.
//
//   cols: [{title, width, text: fn(r)} | {title, width, bar: fn(r) -> {v, max, text}}
//          | {title, width, check: fn(r) -> bool, toggle: fn(r, on), locked: fn(r) -> bool}]
//   now:  fn(r) -> [words, "good" | "bad" | "wait" | a colour]
Rectangle {
    id: root
    property string title: ""
    property string sub: ""
    property string subLink: ""             // "every task": a link after the subtitle that clears a filter
    signal subLinkClicked()

    property string placeholder: ""         // a search box shows when this is set
    property alias query: search.text
    property string actionLabel: ""
    property string actionIcon: "plus"
    property bool actionPlain: false
    property bool actionDisabled: false
    signal action()

    property var rows: []
    property string rowKey: "id"
    property var pick: null
    signal picked(var key)

    property var icon: ""                   // a name, or fn(r) -> name
    property string nameTitle: "Name"
    property var nameText: function (r) { return "" }
    property var nameLine: null
    property bool nameMono: false
    property var cols: []
    property var now: null
    property string nowTitle: "Now"
    property int nowWidth: 190
    property int more: 0                    // extra rows a page (Messages lists two more)

    // the empty state takes the body when there is nothing at all (not when a filter hides all)
    property bool showEmpty: false
    property string emptyIcon: "inbox"
    property string emptyTitle: ""
    property string emptyText: ""
    property string emptyAct: ""
    signal emptyAction()
    property alias tools: toolsRow.data

    readonly property int perPage: Theme.listRows + more
    readonly property int rowH: 54
    property int page: 1
    readonly property int pages: Math.max(1, Math.ceil(rows.length / perPage))
    readonly property var pageRows: rows.slice((Math.min(page, pages) - 1) * perPage, Math.min(page, pages) * perPage)
    onPagesChanged: if (page > pages) page = pages
    onRowsChanged: if (page > pages) page = pages

    color: Theme.surface
    radius: Theme.radius
    border.width: 1
    border.color: Theme.border
    implicitHeight: Theme.listHeight + 56 * more
    clip: true

    function iconOf(r) { return typeof icon === "function" ? icon(r) : icon }
    function fixedWidth() {
        var w = nowWidth
        for (var i = 0; i < cols.length; i++) w += (cols[i].width || 170)
        return w
    }

    // --- header ----------------------------------------------------------------------------------
    Item {
        id: head
        x: 1; y: 1
        width: parent.width - 2
        height: 40
        Row {
            anchors.left: parent.left
            anchors.leftMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            width: Math.max(0, parent.width - 28 - rightSide.width - 10)
            clip: true
            Txt { id: tt; text: root.title; font.weight: Font.DemiBold; width: Math.min(implicitWidth, parent.width) }
            Txt {
                id: st
                visible: root.sub !== ""
                text: root.sub
                color: Theme.text3
                font.pixelSize: Theme.fSmall
                anchors.baseline: tt.baseline
                width: Math.max(0, Math.min(implicitWidth, parent.width - tt.width - 8 - (lk.visible ? lk.implicitWidth + 12 : 0)))
            }
            Txt {
                id: lk
                visible: root.subLink !== ""
                text: "· " + root.subLink
                color: Theme.accent
                font.pixelSize: Theme.fSmall
                anchors.baseline: tt.baseline
                elide: Text.ElideNone
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.subLinkClicked() }
            }
        }
        Row {
            id: rightSide
            anchors.right: parent.right
            anchors.rightMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
            Row { id: toolsRow; spacing: 8; anchors.verticalCenter: parent.verticalCenter }
            SearchBox {
                id: search
                visible: root.placeholder !== ""
                placeholderText: root.placeholder
                anchors.verticalCenter: parent.verticalCenter
                onTextChanged: root.page = 1
            }
            Btn {
                visible: root.actionLabel !== ""
                small: true
                kind: root.actionPlain ? "default" : "primary"
                iconName: root.actionIcon
                text: root.actionLabel
                enabled: !root.actionDisabled
                anchors.verticalCenter: parent.verticalCenter
                onClicked: root.action()
            }
        }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
    }

    // --- the table ---------------------------------------------------------------------------------
    Item {
        id: table
        visible: !root.showEmpty
        x: 1
        anchors.top: head.bottom
        anchors.bottom: foot.top
        width: parent.width - 2
        readonly property real nameW: Math.max(160, width - root.fixedWidth())

        Rectangle {
            id: th
            width: parent.width
            height: 36
            color: Theme.surface2
            Row {
                anchors.fill: parent
                Txt { width: table.nameW; leftPadding: 12; text: root.nameTitle; color: Theme.text3; font.pixelSize: Theme.fSmall; font.weight: Font.Medium; anchors.verticalCenter: parent.verticalCenter }
                Repeater {
                    model: root.cols
                    Txt {
                        required property var modelData
                        width: modelData.width || 170
                        leftPadding: 8
                        text: modelData.title
                        color: Theme.text3; font.pixelSize: Theme.fSmall; font.weight: Font.Medium
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                Txt { width: root.nowWidth; leftPadding: 8; text: root.nowTitle; color: Theme.text3; font.pixelSize: Theme.fSmall; font.weight: Font.Medium; anchors.verticalCenter: parent.verticalCenter }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
        }

        Column {
            anchors.top: th.bottom
            width: parent.width
            Repeater {
                model: root.pageRows
                delegate: Rectangle {
                    id: row
                    required property var modelData
                    readonly property bool sel: root.pick !== null && modelData[root.rowKey] === root.pick
                    width: parent.width
                    height: root.rowH
                    color: sel ? Theme.accentSoft : rowArea.containsMouse ? Theme.surface2 : "transparent"

                    MouseArea {
                        id: rowArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.picked(row.modelData[root.rowKey])
                    }
                    Row {
                        anchors.fill: parent
                        // the item
                        Item {
                            width: table.nameW
                            height: parent.height
                            Icon {
                                x: 12; y: (parent.height - (lineTxt.visible ? 38 : 20)) / 2 + 3
                                name: root.iconOf(row.modelData)
                                size: 14
                                color: Theme.text3
                            }
                            Column {
                                x: 36
                                width: parent.width - 44
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 1
                                Txt {
                                    width: Math.min(implicitWidth, Math.min(360, parent.width))
                                    text: root.nameText(row.modelData)
                                    font.weight: Font.Medium
                                    mono: root.nameMono
                                }
                                Txt {
                                    id: lineTxt
                                    visible: root.nameLine !== null && text !== ""
                                    width: Math.min(implicitWidth, Math.min(360, parent.width))
                                    text: root.nameLine ? root.nameLine(row.modelData) : ""
                                    mono: true
                                    color: Theme.text3
                                    font.pixelSize: 11
                                }
                            }
                        }
                        // the quiet columns
                        Repeater {
                            model: root.cols
                            delegate: Item {
                                id: cell
                                required property var modelData
                                width: modelData.width || 170
                                height: row.height
                                Txt {
                                    visible: !!cell.modelData.text
                                    x: 8
                                    width: parent.width - 20
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: cell.modelData.text ? cell.modelData.text(row.modelData) : ""
                                    color: Theme.text2
                                }
                                Row {
                                    visible: !!cell.modelData.bar
                                    x: 8
                                    spacing: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                    readonly property var b: cell.modelData.bar ? cell.modelData.bar(row.modelData) : ({ v: 0, max: 1, text: "" })
                                    Bar { width: 60; v: parent.b.v; max: parent.b.max; c: Theme.ser6; anchors.verticalCenter: parent.verticalCenter }
                                    Txt { text: parent.b.text; color: Theme.text2; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                                }
                                Check {
                                    visible: !!cell.modelData.check
                                    x: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                    controlled: true
                                    checked: cell.modelData.check ? cell.modelData.check(row.modelData) : false
                                    enabled: !(cell.modelData.locked && cell.modelData.locked(row.modelData))
                                    onToggled: function (on) { if (cell.modelData.toggle) cell.modelData.toggle(row.modelData, on) }
                                }
                            }
                        }
                        // now
                        Item {
                            width: root.nowWidth
                            height: row.height
                            St {
                                x: 8
                                anchors.verticalCenter: parent.verticalCenter
                                readonly property var n: root.now ? root.now(row.modelData) : ["", "wait"]
                                text: n[0]
                                c: (n[1] === "good" || n[1] === "bad" || n[1] === "wait") ? Theme.nowColor(n[1]) : n[1]
                            }
                        }
                    }
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                }
            }
            Item {
                visible: root.rows.length === 0
                width: parent.width
                height: 80
                Txt { anchors.centerIn: parent; text: "Nothing matches."; color: Theme.text3; font.pixelSize: 12 }
            }
        }
    }

    Empty {
        visible: root.showEmpty
        anchors.top: head.bottom
        anchors.bottom: parent.bottom
        width: parent.width
        icon: root.emptyIcon
        title: root.emptyTitle
        text: root.emptyText
        act: root.emptyAct
        h: 200
        onActed: root.emptyAction()
    }

    // --- foot: where you are, and the pages ----------------------------------------------------
    Item {
        id: foot
        visible: !root.showEmpty
        x: 1
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 1
        width: parent.width - 2
        height: root.showEmpty ? 0 : 40
        Rectangle { width: parent.width; height: 1; color: Theme.border }
        Txt {
            x: 14
            anchors.verticalCenter: parent.verticalCenter
            mono: true
            color: Theme.text3
            font.pixelSize: Theme.fSmall
            text: root.rows.length
                  ? Theme.fmt((Math.min(root.page, root.pages) - 1) * root.perPage + 1) + "–"
                    + Theme.fmt(Math.min(Math.min(root.page, root.pages) * root.perPage, root.rows.length))
                    + " of " + Theme.fmt(root.rows.length)
                  : "0 of 0"
        }
        Pager {
            anchors.right: parent.right
            anchors.rightMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            current: Math.min(root.page, root.pages)
            pages: root.pages
            onGo: function (p) { root.page = p }
        }
    }
}
