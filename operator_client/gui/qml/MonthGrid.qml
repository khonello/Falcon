import QtQuick
import "."

// One month, as a grid. Qt Quick Controls has no date picker at all, so this is ours: the smallest
// piece of it, and the one everything else composes.
Item {
    id: root
    property date month: new Date()          // any day in the month to draw
    property var from: null                  // Date or null -- the range being picked
    property var to: null
    property var hoverDate: null
    signal picked(date day)

    readonly property int year: month.getFullYear()
    readonly property int mon: month.getMonth()
    readonly property var first: new Date(year, mon, 1)
    readonly property int lead: (first.getDay() + 6) % 7          // weeks start on Monday
    readonly property int days: new Date(year, mon + 1, 0).getDate()
    readonly property int rows: Math.ceil((lead + days) / 7)

    function sameDay(a, b) {
        return a && b && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth()
               && a.getDate() === b.getDate()
    }
    function within(d) {
        var end = to || hoverDate
        return from && end && d > from && d < end
    }

    implicitWidth: 7 * 34
    implicitHeight: 22 + rows * 30

    Row {
        id: heads
        width: parent.width
        Repeater {
            model: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
            delegate: Txt {
                required property string modelData
                width: 34
                height: 22
                text: modelData
                tone: "quiet"
                font.pixelSize: Theme.fSmall
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    Grid {
        anchors.top: heads.bottom
        columns: 7
        Repeater {
            model: root.rows * 7
            delegate: Item {
                required property int index
                readonly property int dayNum: index - root.lead + 1
                readonly property bool real: dayNum >= 1 && dayNum <= root.days
                readonly property var day: real ? new Date(root.year, root.mon, dayNum) : null
                readonly property bool isFrom: root.sameDay(day, root.from)
                readonly property bool isTo: root.sameDay(day, root.to)
                readonly property bool isMid: real && root.within(day)
                width: 34
                height: 30

                Rectangle {                       // the run between the two ends
                    visible: parent.isMid || parent.isFrom || parent.isTo
                    anchors.fill: parent
                    anchors.topMargin: 2
                    anchors.bottomMargin: 2
                    color: Theme.primarySoft
                    radius: parent.isFrom && parent.isTo ? Theme.radius : 0
                    Rectangle {                   // square off the inside edge of an end
                        visible: parent.parent.isFrom !== parent.parent.isTo
                        width: parent.width / 2
                        height: parent.height
                        color: parent.color
                        anchors.right: parent.parent.isFrom ? parent.right : undefined
                        anchors.left: parent.parent.isTo ? parent.left : undefined
                    }
                }
                Rectangle {
                    visible: parent.isFrom || parent.isTo
                    anchors.centerIn: parent
                    width: 28
                    height: 26
                    radius: Theme.radius
                    color: Theme.primary
                }
                Txt {
                    anchors.centerIn: parent
                    visible: parent.real
                    text: parent.real ? String(parent.dayNum) : ""
                    color: (parent.isFrom || parent.isTo) ? Theme.onDark : Theme.ink
                    font.pixelSize: Theme.fSmall
                }
                HoverHandler {
                    enabled: parent.real
                    cursorShape: Qt.PointingHandCursor
                    onHoveredChanged: if (hovered && root.from && !root.to) root.hoverDate = parent.day
                }
                TapHandler { enabled: parent.real; onTapped: root.picked(parent.day) }
            }
        }
    }
}
