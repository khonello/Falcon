import QtQuick
import "."

// Pages. Two shapes, as the concept has them:
//   numbers (default): ‹ 1 2 3 … 9 › -- the foot of a list
//   compact: "1–5 of 23 ‹ ›"          -- a chart or a row of cards that pages in place
Row {
    id: root
    property int current: 1
    property int pages: 1
    property bool compact: false
    property int total: 0
    property int size: 0
    property string what: ""
    signal go(int page)

    spacing: 4
    visible: compact ? pages > 1 : true

    readonly property var nums: {
        var out = [], n = pages, c = current
        if (n <= 7) { for (var i = 1; i <= n; i++) out.push(i); return out }
        // the concept's (antd's): five pages around the current one, then the first and the last; "1 2 3 4 5 … 16"
        var left = Math.max(1, c - 2), right = Math.min(n, c + 2)
        if (c - 1 <= 2) right = 5
        if (n - c <= 2) left = n - 4
        if (left > 1) out.push(1)
        if (left > 2) out.push(-1)
        for (var k = left; k <= right; k++) out.push(k)
        if (right < n - 1) out.push(-2)
        if (right < n) out.push(n)
        return out
    }

    Txt {
        visible: root.compact
        anchors.verticalCenter: parent.verticalCenter
        mono: true
        font.pixelSize: Theme.fSmall
        elide: Text.ElideNone
        text: {
            var a = (root.current - 1) * root.size + 1, b = Math.min(root.total, a + root.size - 1)
            return Theme.fmt(a) + "–" + Theme.fmt(b)
        }
    }
    Txt {
        visible: root.compact
        anchors.verticalCenter: parent.verticalCenter
        color: Theme.text3
        font.pixelSize: Theme.fSmall
        elide: Text.ElideNone
        rightPadding: 4
        text: " of " + Theme.fmt(root.total) + (root.what ? " " + root.what : "")
    }

    component Cell: Rectangle {
        id: cell
        property string label: ""
        property string glyph: ""
        property bool on: false
        property bool dis: false
        signal hit()
        width: root.compact ? 22 : Math.max(24, t.implicitWidth + 10)
        height: root.compact ? 22 : 24
        radius: Theme.radiusSm
        color: root.compact ? Theme.surface : "transparent"
        border.width: root.compact || on ? 1 : 0
        border.color: on ? Theme.accent : Theme.border
        opacity: dis ? 0.4 : 1
        Txt {
            id: t
            visible: cell.glyph === ""
            anchors.centerIn: parent
            text: cell.label
            font.pixelSize: Theme.fSmall
            color: cell.on ? Theme.accent : Theme.text2
            elide: Text.ElideNone
        }
        Icon { visible: cell.glyph !== ""; anchors.centerIn: parent; name: cell.glyph; size: 12; color: Theme.text2 }
        MouseArea {
            anchors.fill: parent
            enabled: !cell.dis && cell.label !== "…"
            cursorShape: Qt.PointingHandCursor
            onClicked: cell.hit()
        }
    }

    Cell { glyph: "chevl"; dis: root.current <= 1; onHit: root.go(root.current - 1); anchors.verticalCenter: parent.verticalCenter }
    Repeater {
        model: root.compact ? [] : root.nums
        Cell {
            required property var modelData
            label: modelData < 0 ? "…" : String(modelData)
            on: modelData === root.current
            anchors.verticalCenter: parent.verticalCenter
            onHit: root.go(modelData)
        }
    }
    Cell { glyph: "chevr"; dis: root.current >= root.pages; onHit: root.go(root.current + 1); anchors.verticalCenter: parent.verticalCenter }
}
