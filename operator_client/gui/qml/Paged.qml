import QtQuick
import "."

// A LIST THAT PAGES IN PLACE (the user, 11 Nov 2026: a long list "looks weird"): `items` cut into pages of `per`, `shown` is the page
// on screen. `keep` is the index of the item picked (-1 when none on this list): its page is the one shown, so a card picked from
// elsewhere is never on a page you cannot see. A StepPager given it as `of` draws "1 to 5 of 18 ‹ 1 of 4 ›" and steps it.
QtObject {
    property var items: []
    property int per: 5                         // for the design's 900-high window; `size` is what a page holds on this screen
    readonly property int size: Math.max(2, Math.round(per * Theme.viewScale))
    property int pg: 0
    property int keep: -1
    onKeepChanged: if (keep >= 0) pg = Math.floor(keep / size)
    readonly property int total: items ? items.length : 0
    readonly property int pages: Math.max(1, Math.ceil(total / size))
    readonly property int pi: Math.min(pg, pages - 1)
    readonly property var shown: (items || []).slice(pi * size, pi * size + size)
    readonly property int from: total ? pi * size + 1 : 0
    readonly property int to: Math.min(total, pi * size + size)
    readonly property bool more: total > size
}
