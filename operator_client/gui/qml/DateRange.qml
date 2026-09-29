import QtQuick
import QtQuick.Controls.Basic
import "."

// THE DATE RANGE (docs/UI-COMPONENTS.md, P0). Ant Design hands you one; Qt has none, so this is the
// one component that is real work rather than styling. A field that opens two months and a column of
// the ranges anybody actually asks for.
Item {
    id: root
    property var from: null
    property var to: null
    property string placeholder: "Any date"
    signal changed(var from, var to)

    implicitWidth: 240
    implicitHeight: Theme.control

    function fmt(d) {
        if (!d) return ""
        var m = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return d.getDate() + " " + m[d.getMonth()]
    }
    function midnight(d) { return new Date(d.getFullYear(), d.getMonth(), d.getDate()) }
    function setRange(f, t) { from = f; to = t; changed(f, t); if (f && t) pop.close() }
    function preset(days) {
        var end = midnight(new Date())
        var start = new Date(end)
        start.setDate(start.getDate() - (days - 1))
        setRange(start, end)
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: pop.opened ? Theme.primary : hover.hovered ? Theme.primaryHover : Theme.border
        Behavior on border.color { ColorAnimation { duration: Theme.durFast } }

        Icon {
            id: cal
            name: "calendar"
            size: 15
            color: Theme.quiet
            anchors.left: parent.left
            anchors.leftMargin: Theme.s3
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            anchors.left: cal.right
            anchors.leftMargin: Theme.s2
            anchors.right: clear.left
            anchors.verticalCenter: parent.verticalCenter
            text: root.from ? (root.fmt(root.from) + " \u2192 " + (root.to ? root.fmt(root.to) : "\u2026"))
                            : root.placeholder
            tone: root.from ? "ink" : "quiet"
            font.pixelSize: Theme.fBody
        }
        Icon {
            id: clear
            name: "close"
            size: 13
            visible: root.from !== null
            color: Theme.quiet
            anchors.right: parent.right
            anchors.rightMargin: Theme.s3
            anchors.verticalCenter: parent.verticalCenter
            TapHandler { onTapped: root.setRange(null, null) }
        }
        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: pop.opened ? pop.close() : pop.open() }
    }

    Popup {
        id: pop
        y: root.height + 6
        width: left.width + right.width + presets.width + 4 * Theme.s4
        height: 300
        padding: 0
        background: Rectangle {
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split
        }

        property date shown: new Date()

        Row {
            anchors.fill: parent
            anchors.margins: Theme.s4
            spacing: Theme.s4

            Column {
                id: presets
                width: 116
                spacing: 2
                Txt { text: "QUICK"; tone: "quiet"; font.pixelSize: 10; bottomPadding: Theme.s1 }
                Repeater {
                    model: [["Today", 1], ["Last 7 days", 7], ["Last 30 days", 30], ["Last 90 days", 90]]
                    delegate: Rectangle {
                        required property var modelData
                        width: parent.width
                        height: 28
                        radius: Theme.radiusSm
                        color: ph.hovered ? Theme.hover : "transparent"
                        Txt {
                            anchors.left: parent.left
                            anchors.leftMargin: Theme.s2
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData[0]
                            font.pixelSize: Theme.fSmall
                        }
                        HoverHandler { id: ph; cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: root.preset(modelData[1]) }
                    }
                }
                Item { width: 1; height: Theme.s2 }
                Txt {
                    width: parent.width
                    text: "A range is inclusive of both days."
                    tone: "quiet"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    elide: Text.ElideNone
                }
            }

            Column {
                id: left
                width: 7 * 34
                spacing: Theme.s2
                Item {
                    width: parent.width
                    height: 24
                    Btn {
                        kind: "text"; small: true; iconName: "chevl"
                        anchors.left: parent.left
                        onClicked: pop.shown = new Date(pop.shown.getFullYear(), pop.shown.getMonth() - 1, 1)
                    }
                    Txt {
                        anchors.centerIn: parent
                        text: Qt.formatDate(pop.shown, "MMMM yyyy")
                        strong: true
                        font.pixelSize: Theme.fSmall
                    }
                }
                MonthGrid {
                    month: pop.shown
                    from: root.from
                    to: root.to
                    onPicked: function (d) { root.from && !root.to && d >= root.from ? root.setRange(root.from, d)
                                                                                     : root.setRange(d, null) }
                }
            }

            Column {
                id: right
                width: 7 * 34
                spacing: Theme.s2
                Item {
                    width: parent.width
                    height: 24
                    Txt {
                        anchors.centerIn: parent
                        text: Qt.formatDate(new Date(pop.shown.getFullYear(), pop.shown.getMonth() + 1, 1), "MMMM yyyy")
                        strong: true
                        font.pixelSize: Theme.fSmall
                    }
                    Btn {
                        kind: "text"; small: true; iconName: "chevr"
                        anchors.right: parent.right
                        onClicked: pop.shown = new Date(pop.shown.getFullYear(), pop.shown.getMonth() + 1, 1)
                    }
                }
                MonthGrid {
                    month: new Date(pop.shown.getFullYear(), pop.shown.getMonth() + 1, 1)
                    from: root.from
                    to: root.to
                    onPicked: function (d) { root.from && !root.to && d >= root.from ? root.setRange(root.from, d)
                                                                                     : root.setRange(d, null) }
                }
            }
        }
    }
}
