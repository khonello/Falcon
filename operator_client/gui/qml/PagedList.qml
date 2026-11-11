import QtQuick
import "."

// A LIST, PAGED IN PLACE: the console's one way to draw a list of things that can grow (the user, 11 Nov 2026: paging is native to
// anything list-like). Give it `items` and a `delegate` (it sees `modelData` and `index`, the index on the page); it draws `per` of
// them and, under them, "1 to 5 of 18 ‹ 1 of 4 ›" when there are more. `keep` is the index of the item picked (-1 when none of
// these): its page is the one shown. `shown` is the page on screen. A group of cards under a heading is a Group, which pages the same.
Column {
    id: root
    property alias items: pg.items
    property alias per: pg.per
    property alias keep: pg.keep
    property alias pageNo: pg.pg
    readonly property alias shown: pg.shown
    readonly property alias paging: pg
    property Component delegate: null
    width: parent ? parent.width : 0

    Paged { id: pg }
    Repeater { model: pg.shown; delegate: root.delegate }
    StepPager { width: root.width; of: pg }
}
