import QtQuick
import "."

// A ROW THAT PAGES, NEVER SHRINKS (design/PATTERNS.md section 3; supersedes DP10's shrink ladder).
//
// The items keep their full size. As many as fit are shown, centred. The container's far right edge is the pager:
// clicking it slides the next `step` items in (4, or 2 where the row is narrow); the far left edge goes back.
// No scrollbar. The edge says it can move -- a soft fade, a chevron, "8 more" -- and NAMES any hidden item that needs
// someone ("OPS-12 needs you"), so paging never hides an exception. Left/Right arrows page when focused. The order is
// the caller's stable one; paging never re-sorts.
//
//   model      array of plain objects
//   delegate   Component; each instance gets `modelData` and `index`
//   itemWidth  the width of one item (all items are the same width)
//   attention  function(item) -> "" or a short label for an item that needs someone
Item {
    id: root

    property var model: []
    property Component delegate
    property int itemWidth: 92
    property int spacing: 14
    property int edgeWidth: 104
    property int step: width < 600 ? 2 : 4
    property var attention: function (item) { return "" }
    property int first: 0

    readonly property int count: model ? model.length : 0
    readonly property int pitch: itemWidth + spacing
    // room for items: the whole width if everything fits, otherwise leave the edges their room
    readonly property bool fitsAll: count * pitch - spacing <= width
    // an edge takes room only when it shows: no back edge on the first page
    readonly property int capacity: fitsAll ? count
                                   : Math.max(1, Math.floor((width - (first > 0 ? 2 : 1) * edgeWidth + spacing) / pitch))
    readonly property int shown: Math.min(capacity, Math.max(0, count - first))
    readonly property bool canBack: first > 0
    readonly property bool canForward: first + shown < count
    readonly property int hiddenAfter: Math.max(0, count - first - shown)
    readonly property int hiddenBefore: first

    function hiddenNeeds(from, to) {
        var names = []
        for (var i = from; i < to; i++) {
            var a = root.attention(root.model[i])
            if (a) names.push(a)
        }
        return names.length === 0 ? "" : names.length === 1 ? names[0] + " needs you" : names.length + " need you"
    }
    readonly property string needsAfter: hiddenNeeds(first + shown, count)
    readonly property string needsBefore: hiddenNeeds(0, first)

    function forward() { if (canForward) first = Math.min(first + step, count - shown) }
    function back() { if (canBack) first = Math.max(0, first - step) }
    onCountChanged: if (first > Math.max(0, count - 1)) first = 0

    implicitHeight: strip.implicitHeight
    activeFocusOnTab: true
    Keys.onRightPressed: forward()
    Keys.onLeftPressed: back()
    clip: true

    // the items, centred in the room between the edges
    Item {
        id: room
        anchors.fill: parent
        anchors.leftMargin: root.canBack ? root.edgeWidth : 0
        anchors.rightMargin: root.canForward ? root.edgeWidth : 0
        clip: true

        Row {
            id: strip
            spacing: root.spacing
            x: (room.width - (root.shown * root.pitch - root.spacing)) / 2 - root.first * root.pitch
            Behavior on x { NumberAnimation { duration: Theme.durBase; easing.type: Easing.OutCubic } }
            Repeater {
                model: root.model
                delegate: Loader {
                    required property var modelData
                    required property int index
                    width: root.itemWidth
                    sourceComponent: root.delegate
                    // hide what is off the page, so a half-visible item is never drawn
                    opacity: index >= root.first && index < root.first + root.shown ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.durFast } }
                    onLoaded: { item.modelData = modelData; if (item.hasOwnProperty("index")) item.index = index }
                }
            }
        }
    }

    component Edge: Rectangle {
        id: edge
        property bool leading: false
        property int hidden: 0
        property string needs: ""
        signal pressed()
        width: root.edgeWidth
        height: parent.height
        radius: 12
        visible: hidden > 0
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: edge.leading ? Qt.rgba(1, 1, 1, area.containsMouse ? 0.09 : 0.05) : "transparent" }
            GradientStop { position: 1.0; color: edge.leading ? "transparent" : Qt.rgba(1, 1, 1, area.containsMouse ? 0.09 : 0.05) }
        }
        Column {
            anchors.centerIn: parent
            spacing: 4
            width: parent.width - 12
            Icon { name: edge.leading ? "back" : "chev"; color: Theme.dim; size: 16; anchors.horizontalCenter: parent.horizontalCenter }
            Txt {
                width: parent.width; horizontalAlignment: Text.AlignHCenter
                text: edge.hidden + " more"; color: Theme.dim; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold
            }
            Txt {
                width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
                visible: edge.needs !== ""; text: edge.needs; color: Theme.warn; font.pixelSize: Theme.fMeta - 1; font.weight: Font.DemiBold
            }
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: edge.pressed()
        }
    }

    Edge {
        objectName: "pagerBack"
        anchors.left: parent.left
        leading: true
        hidden: root.hiddenBefore
        needs: root.needsBefore
        onPressed: root.back()
    }
    Edge {
        objectName: "pagerForward"
        anchors.right: parent.right
        hidden: root.hiddenAfter
        needs: root.needsAfter
        onPressed: root.forward()
    }
}
