import QtQuick
import "."

// TODAY AS A STRIP OF HOURS (the concept's DayStrip, ds / ovh-day): seven two-hour columns with Now kept in the middle,
// each at least 120px tall, padded 8 8 4 with a hairline between them; what is past fades to half. A column shows two
// things and "+N more". Now is a thin accent line with its time at its foot. At the foot: what is earlier and still
// open, how many are in these hours, and what is later. Items are calendar.board's: {at, title, line, overdue, to}.
Column {
    id: root
    property var items: []
    property string empty: "nothing due in these hours"
    readonly property real now: Time.now
    readonly property real c0: { var s = new Date(now); s.setHours(2 * Math.floor(s.getHours() / 2) - 6, 0, 0, 0); return s.getTime() }
    readonly property real end: c0 + 14 * 3600000
    readonly property var inW: items.filter(function (e) { var t = Time.ms(e.at); return t >= c0 && t < end })
    readonly property var before: items.filter(function (e) { return Time.ms(e.at) < c0 && e.overdue })
    readonly property var after: items.filter(function (e) { return Time.ms(e.at) >= end })
    function label(h, k) {
        var d = new Date(h), dn = new Date(now), prev = k > 0 ? new Date(h - 2 * 3600000) : null
        var other = d.toDateString() !== dn.toDateString() && (k === 0 || d.getDate() !== prev.getDate())
        return (other ? ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.getDay()] + " " : "") + Time.hhmm(h)
    }
    width: parent ? parent.width : 600
    spacing: 8

    Item {
        id: day
        width: parent.width
        height: 4 + 1 + cols.height
        Rectangle { y: 4; width: parent.width; height: 1; color: Theme.border }
        Row {
            id: cols
            y: 5
            width: parent.width
            height: { var m = 120; for (var i = 0; i < rep.count; i++) if (rep.itemAt(i)) m = Math.max(m, rep.itemAt(i).need); return m }
            Repeater {
                id: rep
                model: 7
                delegate: Rectangle {
                    id: col
                    required property int index
                    readonly property real h0: root.c0 + index * 2 * 3600000
                    readonly property bool isNow: root.now >= h0 && root.now < h0 + 2 * 3600000
                    readonly property bool past: h0 + 2 * 3600000 <= root.now
                    readonly property var es: root.inW.filter(function (e) { var t = Time.ms(e.at); return t >= col.h0 && t < col.h0 + 2 * 3600000 })
                    readonly property real need: inner.implicitHeight + 12
                    width: cols.width / 7
                    height: cols.height
                    color: isNow ? Theme.alpha(Theme.accent, 0.04) : "transparent"
                    Rectangle { visible: index > 0; width: 1; height: parent.height; color: Theme.grid }
                    Column {
                        id: inner
                        x: index === 0 ? 0 : 8; y: 8
                        width: parent.width - x - 8
                        spacing: 6
                        opacity: col.past ? 0.5 : 1
                        Txt { text: root.label(col.h0, index); font.pixelSize: 11; color: col.isNow ? Theme.accent : Theme.text4; elide: Text.ElideNone }
                        Repeater {
                            model: col.es.slice(0, 2)
                            delegate: Rectangle {
                                id: ev
                                required property var modelData
                                width: parent.width
                                height: evc.implicitHeight + 16
                                radius: Theme.radiusLg
                                color: Theme.surface2
                                border.width: 1
                                border.color: modelData.overdue ? Theme.alpha(Theme.crit, 0.45) : Theme.border
                                Column {
                                    id: evc
                                    x: 10; y: 8
                                    width: parent.width - 20
                                    spacing: 1
                                    Txt { text: ev.modelData.title; font.weight: Font.DemiBold; font.pixelSize: 13; width: parent.width
                                          color: ev.modelData.overdue ? Theme.crit : evA.containsMouse ? Theme.accent : Theme.text }
                                    Txt { text: Time.hhmm(ev.modelData.at) + ", " + ev.modelData.line + (ev.modelData.overdue ? ", past its time" : ""); font.pixelSize: 12; width: parent.width; color: Theme.text3 }
                                }
                                MouseArea { id: evA; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                            onClicked: if (ev.modelData.to) Nav.goAsk(ev.modelData.to[0], null, "This opens " + Nav.title(ev.modelData.to[0]) + ".", ev.modelData.to[1] || null) }
                            }
                        }
                        Txt { visible: col.es.length > 2; leftPadding: 2; text: "+" + Theme.fmt(col.es.length - 2) + " more"; font.pixelSize: 12; color: Theme.text3
                              MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: Nav.go("calendar") } }
                    }
                }
            }
        }
        // Now: a thin line through the hours, its time at its foot
        Rectangle {
            x: (root.now - root.c0) / (14 * 3600000) * cols.width
            y: 5
            width: 1.5; height: cols.height
            color: Theme.accent
            Txt { x: 6; anchors.bottom: parent.bottom; anchors.bottomMargin: 2; text: "Now " + Time.hhmm(root.now); color: Theme.accent; font.pixelSize: 11; font.weight: Font.DemiBold; elide: Text.ElideNone }
        }
    }
    Item {
        width: parent.width
        height: mid.height
        Txt { visible: root.before.length > 0; text: "‹ " + Theme.fmt(root.before.length) + " earlier, still open"; color: Theme.accent; font.pixelSize: 12; elide: Text.ElideNone
              MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: Nav.go("calendar") } }
        Txt { id: mid; anchors.horizontalCenter: parent.horizontalCenter; text: root.inW.length ? Theme.fmt(root.inW.length) + " in these 14 hours; it moves on as the day does" : root.empty; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
        Txt { anchors.right: parent.right; visible: root.after.length > 0; text: Theme.fmt(root.after.length) + " later ›"; color: Theme.accent; font.pixelSize: 12; elide: Text.ElideNone
              MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: Nav.go("calendar") } }
    }
}
