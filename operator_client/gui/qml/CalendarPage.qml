import QtQuick
import "."

// CALENDAR: what is coming, a month at a time, read-only. Task deadlines, the rules that run on a clock and the
// announcements waiting to go out, all from `calendar.board`; nothing is made here, an item opens the page that owns it.
// The month is a grid with a toolbar; the day picked is an agenda beside it, on a time rail, with a "Now" mark on today.
// The months run from this one to the last that has anything in it (at most twelve), whatever the filter says.
// A day that belongs to the last or next month is hatched, empty and not clickable: its items are on that month's page.
Page {
    id: page
    objectName: "calendarPage"

    property var items: []                         // calendar.board's items
    property int mi: 0                             // the month shown, counted from this one
    property string f: "all"                       // all | task | rule | announcement
    property real today: Time.startOfDay(Time.now)
    property real sel: today                       // the day picked, as its midnight in ms

    readonly property var kinds: ({
        task:         { label: "Tasks",         c: Theme.accent },
        todo:         { label: "Your to-dos",   c: Theme.ser3 },
        rule:         { label: "Automation",    c: Theme.ser2 }
    })
    // the version 1 concept: task deadlines, your to-dos and scheduled automation (announcements have their own page)
    readonly property var kindKeys: ["task", "todo", "rule"]
    function colour(x) { return (x.k === "task" || x.k === "todo") && x.overdue ? Theme.crit : kinds[x.k].c }

    // --- the data ------------------------------------------------------------------------------------
    readonly property var parsed: items.filter(function (i) { return page.kindKeys.indexOf(i.kind) >= 0 }).map(function (i) {
        var t = Time.ms(i.at)
        return { k: i.kind, at: t, day: Time.startOfDay(t), title: i.title, line: i.line, to: i.to, overdue: !!i.overdue }
    })
    function monthStart(m) { var d = new Date(page.today); return new Date(d.getFullYear(), d.getMonth() + m, 1) }
    readonly property int months: {
        var last = page.today
        for (var i = 0; i < parsed.length; i++) if (parsed[i].day > last) last = parsed[i].day
        var a = new Date(page.today), b = new Date(last)
        return Math.min(12, Math.max(1, (b.getFullYear() - a.getFullYear()) * 12 + b.getMonth() - a.getMonth() + 1))
    }
    readonly property var shown: parsed.filter(function (x) { return f === "all" || x.k === f })
    readonly property var byDay: {
        var m = {}
        shown.forEach(function (x) { (m[x.day] = m[x.day] || []).push(x) })
        for (var k in m) m[k].sort(function (a, b) { return a.at - b.at })
        return m
    }
    readonly property var first: monthStart(mi)
    readonly property var cells: {
        var fm = first, lead = (fm.getDay() + 6) % 7
        var days = new Date(fm.getFullYear(), fm.getMonth() + 1, 0).getDate(), n = Math.ceil((lead + days) / 7) * 7, out = []
        for (var i = 0; i < n; i++) {
            var d = new Date(fm.getFullYear(), fm.getMonth(), 1 - lead + i), inM = d.getMonth() === fm.getMonth()
            var xs = inM ? (byDay[d.getTime()] || []).slice() : []
            // a repeating rule sorts behind what is said once, so tasks and announcements get the visible slots
            xs.sort(function (a, b) { return (a.k === "rule") - (b.k === "rule") || a.at - b.at })
            out.push({ t: d.getTime(), date: d.getDate(), inM: inM, xs: xs })
        }
        return out
    }
    readonly property int weeks: cells.length / 7
    function count(k) {
        var m = first.getMonth(), y = first.getFullYear()
        return parsed.filter(function (x) { var d = new Date(x.at); return x.k === k && d.getMonth() === m && d.getFullYear() === y }).length
    }
    readonly property var dayItems: byDay[sel] || []
    readonly property var kindsHere: kindKeys
    readonly property var agenda: {
        var rows = dayItems.map(function (x) { return { x: x, at: x.at } })
        if (sel === today) rows.push({ now: true, at: Time.now })
        rows.sort(function (a, b) { return a.at - b.at })
        return rows
    }
    function rel() {
        var d = Math.round((sel - today) / 86400000)
        return d === 0 ? "today" : d < 0 ? "already gone by" : d === 1 ? "tomorrow" : "in " + d + " days"
    }
    function pickMonth(m) {
        mi = Math.max(0, Math.min(months - 1, m))
        sel = mi === 0 ? today : monthStart(mi).getTime()
    }

    // --- loading -------------------------------------------------------------------------------------
    function load() {
        if (!falcon.isConnected) return
        falcon.call("calendar.board", { days: 124 }, function (ok, r) { page.items = ok ? (r.items || []) : [] })
    }
    Component.onCompleted: load()
    Connections { target: falcon; function onConnected() { page.load() } }
    Timer { interval: 60000; running: true; repeat: true; onTriggered: { page.today = Time.startOfDay(Time.now); page.load() } }

    // --- the page: the month and the day, side by side at one height ------------------------------------
    Item {
        id: both
        width: page.w
        height: Theme.calendarH

        // ======================= the month =======================
        Rectangle {
            id: month
            objectName: "calendarMonth"
            width: (both.width - 14) * 7 / 12
            height: parent.height
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.border

            // the toolbar: the month, the arrows, Today, the months, the filter
            Item {
                id: bar
                x: 16; y: 14
                width: parent.width - 32
                height: 32
                Row {
                    id: leftBar
                    spacing: 10
                    anchors.verticalCenter: parent.verticalCenter
                    Row {
                        spacing: 8
                        anchors.verticalCenter: parent.verticalCenter
                        Txt { text: Qt.locale("en_GB").monthName(page.first.getMonth(), Locale.LongFormat); font.pixelSize: Theme.fMonth; font.weight: Font.DemiBold; anchors.baseline: yr.baseline; elide: Text.ElideNone }
                        Txt { id: yr; text: String(page.first.getFullYear()); font.pixelSize: 16; color: Theme.text3; elide: Text.ElideNone }
                    }
                    Btn { objectName: "calPrev"; small: true; iconName: "left"; enabled: page.mi > 0; onClicked: page.pickMonth(page.mi - 1); anchors.verticalCenter: parent.verticalCenter }
                    Btn { objectName: "calNext"; small: true; iconName: "right"; enabled: page.mi < page.months - 1; onClicked: page.pickMonth(page.mi + 1); anchors.verticalCenter: parent.verticalCenter }
                    Btn { objectName: "calToday"; small: true; text: "Today"; enabled: !(page.mi === 0 && page.sel === page.today); onClicked: page.pickMonth(0); anchors.verticalCenter: parent.verticalCenter }
                    Segmented {
                        visible: page.months > 1
                        anchors.verticalCenter: parent.verticalCenter
                        options: { var o = []; for (var i = 0; i < page.months; i++) o.push({ value: i, label: Qt.locale("en_GB").monthName(page.monthStart(i).getMonth(), Locale.ShortFormat) }); return o }
                        value: page.mi
                        onPicked: function (v) { page.pickMonth(v) }
                    }
                }
                Segmented {
                    objectName: "calFilter"
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    options: { var o = [{ value: "all", label: "All" }]; page.kindsHere.forEach(function (k) { o.push({ value: k, label: page.kinds[k].label }) }); return o }
                    value: page.f
                    onPicked: function (v) { page.f = v }
                }
            }

            // the weekday names; today's is the accent
            Row {
                id: heads
                x: 16; y: bar.y + bar.height + 8
                width: parent.width - 32
                Repeater {
                    model: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                    delegate: Txt {
                        required property string modelData
                        required property int index
                        width: heads.width / 7
                        leftPadding: 8
                        topPadding: 2
                        bottomPadding: 4
                        text: modelData
                        font.pixelSize: Theme.fSmall
                        font.weight: page.mi === 0 && index === (new Date(page.today).getDay() + 6) % 7 ? Font.DemiBold : Font.Normal
                        color: page.mi === 0 && index === (new Date(page.today).getDay() + 6) % 7 ? Theme.accent : Theme.text3
                    }
                }
            }

            // the days: each cell has its own right and bottom line, so no two read as one
            Item {
                id: gridBox
                x: 16; y: heads.y + heads.height
                width: parent.width - 32
                height: month.height - y - 46
                clip: true
                Rectangle { anchors.fill: parent; color: "transparent"; border.width: 1; border.color: Theme.borderStrong; radius: Theme.radius; z: 3 }
                Grid {
                    columns: 7
                    Repeater {
                        model: page.cells
                        delegate: Item {
                            id: cell
                            required property var modelData
                            readonly property bool on: modelData.inM && modelData.t === page.sel
                            readonly property bool isToday: modelData.inM && modelData.t === page.today
                            readonly property bool gone: modelData.t < page.today
                            width: gridBox.width / 7
                            height: gridBox.height / page.weeks

                            Rectangle { anchors.fill: parent; color: modelData.inM ? Theme.surface : "transparent"; visible: modelData.inM }
                            Hatch { anchors.fill: parent; visible: !modelData.inM }
                            Rectangle { anchors.fill: parent; color: Theme.accentSoft; visible: cell.on }
                            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.borderStrong; opacity: 0.8 }
                            Rectangle { anchors.bottom: parent.bottom; height: 1; width: parent.width; color: Theme.borderStrong; opacity: 0.8 }
                            Rectangle { anchors.fill: parent; color: "transparent"; border.width: cell.on ? 2 : hover.containsMouse && cell.modelData.inM ? 1 : 0; border.color: cell.on ? Theme.accent : Theme.borderStrong; z: 2 }

                            Rectangle {
                                x: 6; y: 5
                                width: Math.max(20, dn.implicitWidth + 10); height: 20; radius: 10
                                color: cell.isToday ? Theme.accent : "transparent"
                                Txt {
                                    id: dn
                                    anchors.centerIn: parent
                                    text: cell.modelData.date
                                    font.pixelSize: Theme.fSmall
                                    font.weight: cell.isToday ? Font.DemiBold : Font.Normal
                                    color: cell.isToday ? Theme.inverse : cell.modelData.inM && !cell.gone ? Theme.text : Theme.text4
                                    elide: Text.ElideNone
                                }
                            }
                            Column {
                                x: 6; y: 30
                                width: parent.width - 12
                                spacing: 3
                                opacity: cell.gone ? 0.62 : 1
                                Repeater {
                                    model: cell.modelData.xs.slice(0, 2)
                                    delegate: Rectangle {
                                        required property var modelData
                                        width: parent.width; height: 17; radius: 4
                                        color: Theme.alpha(page.colour(modelData), 0.18)
                                        Txt { x: 6; width: parent.width - 10; anchors.verticalCenter: parent.verticalCenter; text: modelData.title; font.pixelSize: 11 }
                                    }
                                }
                                Txt { visible: cell.modelData.xs.length > 2; text: "+" + (cell.modelData.xs.length - 2) + " more"; color: Theme.accent; font.pixelSize: Theme.fTiny; font.weight: Font.Medium }
                            }
                            MouseArea {
                                id: hover
                                anchors.fill: parent
                                enabled: cell.modelData.inM
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: page.sel = cell.modelData.t
                            }
                        }
                    }
                }
            }

            // what the colours are, with this month's counts
            Row {
                x: 16
                y: gridBox.y + gridBox.height + 14
                spacing: 16
                Repeater {
                    model: page.kindsHere
                    delegate: Row {
                        required property string modelData
                        spacing: 6
                        Rectangle { width: 10; height: 10; radius: 3; color: Theme.alpha(page.kinds[modelData].c, 0.55); anchors.verticalCenter: parent.verticalCenter }
                        Txt { text: page.kinds[modelData].label; color: Theme.text2; font.pixelSize: Theme.fSmall; elide: Text.ElideNone }
                        Txt { text: page.count(modelData); font.weight: Font.DemiBold; font.pixelSize: Theme.fSmall; elide: Text.ElideNone }
                    }
                }
                Row {
                    spacing: 6
                    Rectangle { width: 10; height: 10; radius: 3; color: Theme.alpha(Theme.crit, 0.55); anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: "A task past its date"; color: Theme.text2; font.pixelSize: Theme.fSmall; elide: Text.ElideNone }
                }
                Txt { text: "Hatched days belong to another month."; color: Theme.text3; font.pixelSize: Theme.fSmall; elide: Text.ElideNone }
            }
        }

        // ======================= the day, as an agenda =======================
        Rectangle {
            id: dayPanel
            objectName: "calendarDay"
            Pulse { parent: dayPanel; key: page.sel; radius: dayPanel.radius }     // a day picked pulses at once (drawn from what is loaded: no spinner)
            x: month.width + 14
            width: both.width - x
            height: parent.height
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.border
            clip: true

            Row {
                id: dayHead
                x: 18; y: 16
                spacing: 14
                Rectangle {
                    width: 58; height: 64; radius: 10
                    color: Theme.surface2
                    border.width: 1
                    border.color: Theme.border
                    Column {
                        anchors.centerIn: parent
                        Txt { anchors.horizontalCenter: parent.horizontalCenter; text: Qt.locale("en_GB").monthName(new Date(page.sel).getMonth(), Locale.ShortFormat).toUpperCase(); font.pixelSize: Theme.fTiny; font.weight: Font.DemiBold; font.letterSpacing: 0.8; color: Theme.text3; elide: Text.ElideNone }
                        Txt { anchors.horizontalCenter: parent.horizontalCenter; text: new Date(page.sel).getDate(); font.pixelSize: Theme.fDay; font.weight: Font.DemiBold; color: page.sel === page.today ? Theme.accent : Theme.text; elide: Text.ElideNone }
                    }
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Txt { text: Qt.locale("en_GB").dayName(new Date(page.sel).getDay(), Locale.LongFormat); font.pixelSize: 16; font.weight: Font.DemiBold; elide: Text.ElideNone }
                    Txt { text: page.rel() + (page.dayItems.length ? " · " + Theme.many(page.dayItems.length, "item") : ""); color: Theme.text3; elide: Text.ElideNone }
                }
            }
            Rectangle { y: dayHead.y + dayHead.height + 16; width: parent.width; height: 1; color: Theme.border }

            Flickable {
                id: agenda
                x: 0; y: dayHead.y + dayHead.height + 17
                width: parent.width
                height: parent.height - y - 44
                contentHeight: rail.height + 24
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                Column {
                    id: rail
                    x: 18; y: 16
                    width: agenda.width - 36
                    Repeater {
                        model: page.agenda
                        delegate: Item {
                            id: row
                            required property var modelData
                            required property int index
                            readonly property bool last: index === page.agenda.length - 1
                            readonly property color c: modelData.now ? Theme.accent : page.colour(modelData.x)
                            width: rail.width
                            height: body.height + 14

                            Txt { x: 0; y: 1; width: 52; text: Time.hhmm(modelData.at); mono: true; font.pixelSize: Theme.fSmall; color: modelData.now ? Theme.accent : Theme.text3; font.weight: modelData.now ? Font.DemiBold : Font.Normal; elide: Text.ElideNone }
                            Rectangle { x: 74; y: 4; width: 1; height: parent.height - 2; color: Theme.border; visible: !row.last }
                            Rectangle {
                                x: 69; y: 4; width: 10; height: 10; radius: 5
                                color: row.c
                                Rectangle { anchors.centerIn: parent; width: 16; height: 16; radius: 8; color: Theme.alpha(row.c, 0.25); z: -1; visible: !!row.modelData.now }
                            }
                            Column {
                                id: body
                                x: 92
                                width: parent.width - 92
                                spacing: 1
                                Txt { visible: !!row.modelData.now; text: "Now"; color: Theme.accent; font.weight: Font.DemiBold; elide: Text.ElideNone }
                                Txt { visible: !row.modelData.now; text: row.modelData.x ? row.modelData.x.title : ""; font.weight: Font.Medium; width: parent.width; wrapMode: Text.Wrap; elide: Text.ElideNone }
                                Txt { visible: !row.modelData.now; text: row.modelData.x ? (row.modelData.x.k === "announcement" ? "Goes out · " : "") + row.modelData.x.line : ""; color: Theme.text3; font.pixelSize: Theme.fSmall; width: parent.width }
                                Row {
                                    visible: !row.modelData.now
                                    spacing: 8
                                    topPadding: 6
                                    Tag { c: row.c; text: row.modelData.x ? page.kinds[row.modelData.x.k].label + (row.modelData.x.overdue && row.modelData.x.k === "task" ? " · past its date" : "") : "" }
                                    Link { text: "Open →"; anchors.verticalCenter: parent.verticalCenter; onClicked: Nav.go(row.modelData.x.to[0], row.modelData.x.to.length > 1 ? row.modelData.x.to[1] : null) }
                                }
                            }
                        }
                    }
                    Empty {
                        visible: page.dayItems.length === 0
                        width: rail.width
                        icon: "calendar"
                        title: "Nothing on this day"
                        text: "Deadlines, scheduled automation and announcements waiting to go out appear here."
                        h: 200
                    }
                }
            }
            Rectangle { anchors.bottom: parent.bottom; anchors.bottomMargin: 43; width: parent.width; height: 1; color: Theme.border }
            Txt { x: 18; anchors.bottom: parent.bottom; anchors.bottomMargin: 14; text: "Read-only. An item opens the page that owns it."; color: Theme.text3; font.pixelSize: Theme.fSmall; elide: Text.ElideNone }
        }
    }

    situation: {
        var wk = parsed.filter(function (x) { return x.at >= Time.now && x.at < Time.now + 7 * 86400000 })
        var n = function (k) { return wk.filter(function (x) { return x.k === k }).length }
        var late = parsed.filter(function (x) { return x.overdue }).length
        return "In the next 7 days: " + Theme.many(n("task"), "task deadline") + ", " + Theme.fmt(n("todo")) + " of your to-dos and " + Theme.many(n("rule"), "scheduled run") + "."
               + (late ? " " + Theme.fmt(late) + (late === 1 ? " is" : " are") + " already past " + (late === 1 ? "its" : "their") + " date." : "")
    }
    situationAt: Time.now

    // put something on the calendar: a to-do for yourself, with when it is due (todo.add)
    property string tdt: ""
    // tomorrow at 17:00, as the concept starts it
    property var tdue: { var d = new Date(Time.now); d.setDate(d.getDate() + 1); d.setHours(17, 0, 0, 0); return d.getTime() }
    function addTodo() {
        falcon.call("todo.add", { text: tdt.trim(), due_at: Time.d(tdue).toISOString() }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not added"); return }
            Msg.ok("Added, due " + Time.atDay(page.tdue)); page.tdt = ""; page.tdue = null; page.load()
        })
    }
    Box {
        objectName: "putOnCalendar"
        width: parent.width
        accentFoot: true
        title: "Put something on the calendar"
        sub: "a to-do for yourself with when it is due; it is said here before it is added"
        Column {
            width: parent.width
            spacing: 8
            Row {
                width: parent.width
                spacing: 8
                Field { objectName: "calTodo"; width: parent.width - 190 - addB.width - 16; placeholderText: "What to remember"; text: page.tdt; onTextEdited: page.tdt = text }
                DateTimeField { width: 190; value: page.tdue; placeholder: "When it is due"; onChanged: function (v) { page.tdue = v } }
                Btn { id: addB; kind: "primary"; text: "Add it"; enabled: page.tdt.trim() !== "" && page.tdue !== null; onClicked: page.addTodo() }
            }
            Rectangle {
                readonly property bool said: page.tdt.trim() !== "" && page.tdue !== null
                width: parent.width
                height: pv.height + (said ? 20 : 0)
                radius: Theme.radius
                color: said ? Theme.surface2 : "transparent"
                Txt { id: pv; x: parent.said ? 12 : 2; y: parent.said ? 10 : 0; width: parent.width - 2 * x; wrapMode: Text.WordWrap; elide: Text.ElideNone
                      font.pixelSize: parent.said ? 13 : 13; color: parent.said ? Theme.text : Theme.text3
                      text: parent.said ? (Time.ms(page.tdue) < Time.now ? "That time has passed. Choose a later one." : "A to-do for you, due " + Time.atDay(page.tdue) + ". Only you see it; it shows on Tasks and here.") : "Say what to remember, and by when." }
            }
        }
    }
}
