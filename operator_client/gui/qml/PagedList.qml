import QtQuick
import "."

// A LIST, PAGED IN PLACE: the console's one way to draw a list of things that can grow (the user, 11 Nov 2026: paging is native to
// anything list-like, and a list has a set size rather than growing). Give it `items` and a `delegate` (it sees `modelData` and `index`,
// the index on the page); it draws `per` of them and, under them, "1 to 5 of 18 ‹ 1 of 4 ›" when there are more. `keep` is the index of
// the item picked (-1 when none of these): its page is the one shown. `shown` is the page on screen.
//
// Its size is set: once it has anything in it, it holds the room of a full page (`per` rows of `rowH`, or of its tallest row so far)
// with the pager's line under them, so a section keeps one height from one item to a full page and a new item never pushes the page
// down; more than a page is paged, never grown. `reserve: false` lets a list be as tall as what it holds (several short lists in one box).
// A group of cards under a heading is a Group, which pages the same.
Item {
    id: root
    property alias items: pg.items
    property alias per: pg.per
    property alias keep: pg.keep
    property alias pageNo: pg.pg
    readonly property alias shown: pg.shown
    readonly property alias paging: pg
    property Component delegate: null
    property real spacing: 0
    property real rowH: 0                       // a row's height; 0: the tallest row drawn so far
    property bool reserve: true
    property real tallest: 0
    readonly property real unit: rowH > 0 ? rowH : tallest
    readonly property real pagerH: 28
    readonly property real full: pg.size * unit + Math.max(0, pg.size - 1) * spacing + pagerH
    width: parent ? parent.width : 0
    implicitHeight: pg.total === 0 ? 0 : reserve && unit > 0 ? Math.max(full, rows.implicitHeight + pagerH) : rows.implicitHeight + (pg.more ? pagerH : 0)
    height: implicitHeight

    Paged { id: pg }
    Column {
        id: rows
        width: root.width
        spacing: root.spacing
        Repeater {
            model: pg.shown
            delegate: root.delegate
            onItemAdded: function (index, item) { if (item) root.tallest = Math.max(root.tallest, item.implicitHeight > 0 ? item.implicitHeight : item.height) }
        }
    }
    StepPager { y: root.height - root.pagerH; width: root.width; of: pg }
}
