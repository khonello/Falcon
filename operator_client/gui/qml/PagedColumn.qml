import QtQuick
import "."

// A STACK OF CARDS THAT PAGES DOWN (design/PATTERNS.md section 3, vertical).
//
// For a fixed-height cell holding cards: as many as fit are shown whole; the cell's bottom edge is the pager --
// a soft fade, a down chevron, "3 more", and the name of any hidden card that needs someone. The top edge pages back.
// Cards slide, they never scroll by the pixel. A continuous record read top to bottom (the trail, a channel) is NOT
// this: it scrolls.
//
//   model       array of plain objects
//   delegate    Component; each instance gets `modelData` and `index`
//   itemHeight  one card's height (all the same)
//   attention   function(item) -> "" or a short label
Item {
    id: root

    property var model: []
    property Component delegate
    property int itemHeight: 58
    property int spacing: 9
    property int edgeHeight: 32
    property int step: 2
    property var attention: function (item) { return "" }
    property int first: 0

    readonly property int count: model ? model.length : 0
    readonly property int pitch: itemHeight + spacing
    readonly property bool fitsAll: count * pitch - spacing <= height
    // an edge takes room only when it shows: no top edge on the first page
    readonly property int capacity: fitsAll ? count
                                   : Math.max(1, Math.floor((height - (first > 0 ? 2 : 1) * edgeHeight + spacing) / pitch))
    readonly property int shown: Math.min(capacity, Math.max(0, count - first))
    readonly property int hiddenAfter: Math.max(0, count - first - shown)
    readonly property int hiddenBefore: first

    function hiddenNeeds(from, to) {
        var names = []
        for (var i = from; i < to; i++) {
            var a = root.attention(root.model[i])
            if (a) names.push(a)
        }
        return names.length === 0 ? "" : names.length === 1 ? names[0] : names.length + " need you"
    }
    readonly property string needsAfter: hiddenNeeds(first + shown, count)
    readonly property string needsBefore: hiddenNeeds(0, first)

    function forward() { if (hiddenAfter > 0) first = Math.min(first + step, count - shown) }
    function back() { if (first > 0) first = Math.max(0, first - step) }
    onCountChanged: if (first > Math.max(0, count - 1)) first = 0

    activeFocusOnTab: true
    Keys.onDownPressed: forward()
    Keys.onUpPressed: back()
    clip: true

    Item {
        id: room
        anchors.fill: parent
        anchors.topMargin: root.hiddenBefore > 0 ? root.edgeHeight : 0
        anchors.bottomMargin: root.hiddenAfter > 0 ? root.edgeHeight : 0
        clip: true

        Column {
            spacing: root.spacing
            width: parent.width
            y: -root.first * root.pitch
            Behavior on y { NumberAnimation { duration: Theme.durBase; easing.type: Easing.OutCubic } }
            Repeater {
                model: root.model
                delegate: Loader {
                    required property var modelData
                    required property int index
                    width: room.width
                    height: root.itemHeight
                    sourceComponent: root.delegate
                    opacity: index >= root.first && index < root.first + root.shown ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.durFast } }
                    onLoaded: { item.modelData = modelData; if (item.hasOwnProperty("index")) item.index = index }
                }
            }
        }
    }

    component Edge: Rectangle {
        id: edge
        property bool atTop: false
        property int hidden: 0
        property string needs: ""
        signal pressed()
        width: parent.width
        height: root.edgeHeight
        radius: 12
        visible: hidden > 0
        gradient: Gradient {
            GradientStop { position: 0.0; color: edge.atTop ? Qt.rgba(1, 1, 1, area.containsMouse ? 0.09 : 0.05) : "transparent" }
            GradientStop { position: 1.0; color: edge.atTop ? "transparent" : Qt.rgba(1, 1, 1, area.containsMouse ? 0.09 : 0.05) }
        }
        Row {
            anchors.centerIn: parent
            spacing: 8
            Icon { name: edge.atTop ? "chevu" : "chevd"; color: Theme.dim; size: 14; anchors.verticalCenter: parent.verticalCenter }
            Txt { text: edge.hidden + " more"; color: Theme.dim; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold
                  anchors.verticalCenter: parent.verticalCenter }
            Txt { visible: edge.needs !== ""; text: edge.needs; color: Theme.warn; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold
                  anchors.verticalCenter: parent.verticalCenter }
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
        objectName: "pagerUp"
        anchors.top: parent.top
        atTop: true
        hidden: root.hiddenBefore
        needs: root.needsBefore
        onPressed: root.back()
    }
    Edge {
        objectName: "pagerDown"
        anchors.bottom: parent.bottom
        hidden: root.hiddenAfter
        needs: root.needsAfter
        onPressed: root.forward()
    }
}
