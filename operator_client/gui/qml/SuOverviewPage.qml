import QtQuick
import "."

// THE SUPER USER'S OVERVIEW: what is waiting on you, the fleet, and this week's deviations. Four
// figures; the fleet map beside what waits on you (a row opens the decision in a panel); the week's
// deviations beside the ones worth a look (a row opens in place; only its link leaves the page).
Page {
    id: page
    objectName: "overviewView"

    property string by: "Status"
    property var cpu: ({})
    property string openDev: ""

    readonly property var q: Desk.queue
    readonly property int urgent: q.filter(function (x) { return x.sev === "high" || x.sev === "critical" }).length
    readonly property var devs: Fleet.deviations.map(function (d) {
        var m = Fleet.byPc[d.observed_pc_id], x = Rules.devRecord(d)
        return { id: x.id, short: x.short, who: m ? (m.user || m.host) : "—", at: d.detected_at, open: !d.resolved_at,
                 expected: x.expected, happened: x.happened }
    }).sort(function (a, b) { return (b.open ? 1 : 0) - (a.open ? 1 : 0) || Time.ms(b.at) - Time.ms(a.at) })
    readonly property var week: devs.filter(function (d) { return Time.ms(d.at) >= Time.now - 7 * 86400000 })
    readonly property var perDay: {
        var v = [0, 0, 0, 0, 0, 0, 0]
        week.forEach(function (d) { var k = Math.floor((Time.startOfDay(Time.now) - Time.startOfDay(Time.ms(d.at))) / 86400000); if (k >= 0 && k < 7) v[6 - k] += 1 })
        return [{ name: "Deviations", c: Theme.med, v: v }]
    }
    readonly property var off: Fleet.machines.filter(function (m) { return !m.online })
    readonly property int behind: Fleet.machines.filter(function (m) { return m.behind }).length

    function loadCpu() {
        Fleet.machines.filter(function (m) { return m.online }).slice(0, 120).forEach(function (m) {
            falcon.call("hierarchy.pc_state", { pc_id: m.pc_id }, function (ok, r) { if (ok && r.levels) { var c = Object.assign({}, page.cpu); c[m.host] = r.levels.cpu; page.cpu = c } })
        })
    }
    onByChanged: if (by === "CPU") loadCpu()

    Drawer {
        id: decide
        page: page
        width: Math.min(980, (page.Window.window ? page.Window.window.width : 1200) - 32)
        title: "Decide"
        property string id0: ""
        readonly property var d: { for (var i = 0; i < Desk.queue.length; i++) if (Desk.queue[i].id === id0) return Desk.queue[i]; return null }
        Work { width: parent.width; d: decide.d; onDecided: function (id) { var next = Desk.queue.filter(function (x) { return x.id !== id })[0]; if (next) decide.id0 = next.id } }
        Txt { visible: decide.d === null; text: "Decided. Nothing else is waiting here."; color: Theme.text3 }
    }

    Row {
        width: parent.width
        spacing: 14
        readonly property real cw: (width - 42) / 4
        Kpi { width: parent.cw; label: "Waiting on you"; value: Theme.fmt(page.q.length); delta: page.q.length ? page.urgent + " urgent" : "Nothing waiting"; dc: page.urgent ? Theme.crit : Theme.text3 }
        Kpi { width: parent.cw; label: "Deviations this week"; value: Theme.fmt(page.week.length)
              delta: page.week.length ? page.week.filter(function (d) { return d.open }).length + " still open" : "Every rule kept"
              dc: page.week.some(function (d) { return d.open }) ? Theme.crit : Theme.text3 }
        Kpi { width: parent.cw; label: "Machines online"; none: Fleet.machines.length === 0; noneValue: "0"; noneText: "No machines yet"
              value: Theme.fmt(Fleet.machines.length - page.off.length); unit: "/ " + Theme.fmt(Fleet.machines.length)
              delta: page.off.length ? (page.off.length === 1 ? page.off[0].host + " is" : Theme.fmt(page.off.length) + " are") + " offline" : "All online"; dc: page.off.length ? Theme.crit : Theme.text3 }
        Kpi { width: parent.cw; label: "On current version"; none: Fleet.machines.length === 0; noneText: "No machines yet"
              value: String(Fleet.machines.length ? Math.round((Fleet.machines.length - page.behind) / Fleet.machines.length * 100) : 0); unit: "%"
              delta: page.behind ? Theme.fmt(page.behind) + " holding the next version back" : "the next version can be approved"; dc: page.behind ? Theme.med : Theme.text3 }
    }

    Row {
        width: parent.width
        spacing: 14
        readonly property real h: Math.max(fp.implicitHeight, wp.implicitHeight)
        Panel {
            id: fp
            width: (parent.width - 14) * 7 / 12
            height: parent.h
            title: "Fleet"
            sub: Theme.fmt(Fleet.machines.length) + " machines · click one to see its card"
            extra: Segmented { options: ["Status", "CPU", "Version", "Check-in"]; value: page.by; onPicked: function (v) { page.by = v } }
            HostMap {
                visible: Fleet.machines.length > 0
                width: parent.width
                by: page.by
                cpu: page.cpu
                openLabel: "See {h} in Registry →"
                moreLabel: "on Departments →"
                onOpen: function (h) { Nav.go("registry", h) }
                onMore: Nav.go("departments")
            }
            Empty { visible: Fleet.loaded && Fleet.machines.length === 0; width: parent.width; h: 220; icon: "desktop"; title: "No machines yet"; text: "Machines appear here by department as they are registered."; act: "Open Registry →"; onActed: Nav.go("registry") }
        }
        Panel {
            id: wp
            width: (parent.width - 14) * 5 / 12
            height: parent.h
            flush: true
            title: "Waiting on you"
            sub: "click one to decide it"
            Column {
                width: parent.width
                Empty { visible: page.q.length === 0; width: parent.width; h: 180; icon: "check"; title: "Nothing is waiting on you"; text: "Reports nobody below you can take, and decisions only you can make, appear here." }
                Repeater {
                    model: page.q.slice(0, 6)
                    Rectangle {
                        required property var modelData
                        width: parent.width; height: 40
                        color: wa.containsMouse ? Theme.surface2 : "transparent"
                        Rectangle { x: 14; width: 8; height: 8; radius: 2; color: Fleet.sevColor(modelData.sev); anchors.verticalCenter: parent.verticalCenter }
                        Txt { x: 32; width: parent.width - 110; anchors.verticalCenter: parent.verticalCenter; text: modelData.short }
                        Txt { anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter; text: modelData.age; mono: true; color: Theme.text3; font.pixelSize: 11 }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                        MouseArea { id: wa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { decide.id0 = modelData.id; decide.open() } }
                    }
                }
                Item { visible: page.q.length > 6; width: parent.width; height: 36
                       More { x: 14; anchors.verticalCenter: parent.verticalCenter; n: page.q.length - 6; what: "waiting"; onClicked: { decide.id0 = page.q[6].id; decide.open() } } }
            }
        }
    }

    Row {
        width: parent.width
        spacing: 14
        readonly property real h: Math.max(dp.implicitHeight, lp.implicitHeight)
        Panel {
            id: dp
            width: (parent.width - 14) * 7 / 12
            height: parent.h
            title: "Deviations, 7 days"
            sub: "broken rules with someone to ask"
            extra: Btn { small: true; kind: "link"; text: "Accountability →"; onClicked: Nav.go("accountability") }
            DayBars { visible: page.week.length > 0; width: parent.width; height: 214; series: page.perDay }
            Empty { visible: page.week.length === 0; width: parent.width; h: 170; icon: "barchart"; title: "No deviations this week"; text: "Each day's broken rules." }
        }
        Panel {
            id: lp
            width: (parent.width - 14) * 5 / 12
            height: parent.h
            flush: true
            title: "Worth a look"
            sub: "this week · open first, then dealt with"
            Column {
                width: parent.width
                Empty { visible: page.week.length === 0; width: parent.width; h: 180; icon: "check"; title: "Nothing this week"; text: "When a rule is broken, it appears here, the open ones first." }
                Repeater {
                    model: page.week.slice(0, 6)
                    Column {
                        required property var modelData
                        readonly property bool on: page.openDev === modelData.id
                        width: parent.width
                        Rectangle {
                            width: parent.width; height: 40
                            color: parent.on ? Theme.accentSoft : da.containsMouse ? Theme.surface2 : "transparent"
                            Rectangle { x: 14; width: 8; height: 8; radius: 2; color: modelData.open ? Theme.med : Theme.text4; anchors.verticalCenter: parent.verticalCenter }
                            Txt { x: 32; width: parent.width - 220; anchors.verticalCenter: parent.verticalCenter; text: modelData.short; color: modelData.open ? Theme.text : Theme.text3 }
                            Txt { x: parent.width - 180; width: 100; anchors.verticalCenter: parent.verticalCenter; text: modelData.open ? modelData.who : "Dealt with"; color: Theme.text3; font.pixelSize: 12 }
                            Txt { anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter; text: Time.at(modelData.at); mono: true; color: Theme.text3; font.pixelSize: 11 }
                            MouseArea { id: da; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.openDev = parent.parent.on ? "" : modelData.id }
                        }
                        Rectangle {
                            visible: parent.on
                            width: parent.width; height: visible ? ex.height + 20 : 0
                            color: Theme.surface2
                            Column { id: ex; x: 32; y: 8; width: parent.width - 46; spacing: 3
                                     Txt { width: parent.width; font.pixelSize: 12; textFormat: Text.RichText
                                           text: "<span style='color:" + Theme.text3 + "'>Expected </span>" + modelData.expected + "<br><span style='color:" + Theme.text3 + "'>What happened </span>" + modelData.happened }
                                     Link { text: "Open in Accountability →"; font.pixelSize: 12; onClicked: Nav.go("accountability", modelData.id) } }
                        }
                        Rectangle { width: parent.width; height: 1; color: Theme.grid }
                    }
                }
            }
        }
    }
}
