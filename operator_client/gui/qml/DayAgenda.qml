import QtQuick
import "."

// TODAY AS AN AGENDA AROUND NOW (the concept's DayAgenda, ag; the user, 10 Nov 2026, in place of the seven two-hour columns): one line
// per thing in time order, the last three of the past seven hours above Now, faded, and the next six below it however far off; each line its time, its whole title
// and where it is, red when it is past its time. At the foot what is earlier and still open, and what is later. Items are
// calendar.board's: {at, title, line, overdue, to}.
Column {
    id: root
    property var items: []
    property string empty: "nothing due in these hours"
    readonly property real now: Math.floor(Time.now / 60000) * 60000          // to the minute: the rows are rebuilt only when that moves
    readonly property var past: items.filter(function (e) { var t = Time.ms(e.at); return t >= root.now - 7 * 3600000 && t < root.now }).slice(-3)
    readonly property var next: items.filter(function (e) { return Time.ms(e.at) >= root.now }).slice(0, 6)
    readonly property int before: items.filter(function (e) { return Time.ms(e.at) < root.now && e.overdue }).length - past.filter(function (e) { return e.overdue }).length
    readonly property int after: items.filter(function (e) { return Time.ms(e.at) >= root.now }).length - next.length
    function when(x) {
        var d = new Date(Time.ms(x)), n = new Date(now)
        return (d.toDateString() !== n.toDateString() ? ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.getDay()] + " " : "") + Time.hhmm(x)
    }
    width: parent ? parent.width : 600
    spacing: 8

    Column {
        objectName: "agenda"
        width: parent.width
        Rectangle { width: parent.width; height: 1; color: Theme.border }
        Repeater { model: root.past; delegate: Line { gone: true } }
        // Now, between what has passed and what comes next
        Item {
            objectName: "agendaNow"
            width: parent.width; height: 30
            Txt { id: nowT; anchors.verticalCenter: parent.verticalCenter; text: "Now " + Time.hhmm(root.now); color: Theme.accent; font.pixelSize: 11; font.weight: Font.DemiBold; elide: Text.ElideNone }
            Rectangle { x: nowT.width + 8; anchors.verticalCenter: parent.verticalCenter; width: parent.width - x; height: 1.5; color: Theme.accent }
        }
        Repeater { model: root.next; delegate: Line { gone: false } }
        Txt { visible: root.past.length === 0 && root.next.length === 0; topPadding: 8; text: root.empty; color: Theme.text3; font.pixelSize: 13 }
    }
    Item {
        width: parent.width; height: 18
        Link { visible: root.before > 0; text: "‹ " + root.before + " earlier, still open"; font.pixelSize: 12; onClicked: Nav.go("calendar") }
        Link { visible: root.after > 0; anchors.right: parent.right; text: root.after + " later ›"; font.pixelSize: 12; onClicked: Nav.go("calendar") }
    }

    component Line: Item {
        id: ln
        required property var modelData
        property bool gone: false
        width: root.width
        height: 36
        opacity: gone ? 0.5 : 1
        Txt { anchors.verticalCenter: parent.verticalCenter; width: 78; text: root.when(ln.modelData.at); mono: true; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
        Txt { x: 90; anchors.verticalCenter: parent.verticalCenter; width: (parent.width - 90) * 0.62 - 12; text: ln.modelData.title; font.pixelSize: 13; font.weight: Font.Medium
              color: ln.modelData.overdue ? Theme.crit : lnA.containsMouse ? Theme.accent : Theme.text }
        Txt { x: 90 + (parent.width - 90) * 0.62; anchors.verticalCenter: parent.verticalCenter; width: (parent.width - 90) * 0.38; font.pixelSize: 13; color: Theme.text3
              text: ln.modelData.line + (ln.modelData.overdue ? " · past its time" : "") }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
        MouseArea { id: lnA; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: if (ln.modelData.to) Nav.goAsk(ln.modelData.to[0], null, "This opens " + Nav.title(ln.modelData.to[0]) + ".", ln.modelData.to[1] || null) }
        Tip { text: ln.modelData.title }
    }
}
