import QtQuick
import "."

// AN ADMIN'S OVERVIEW (the concept's Overview): four figures, the fleet and the open issues side by
// side, event volume with the live stream beside it, and the department underneath. An open issue
// opens in place under its row; only "Open in Issues →" leaves the page.
Page {
    id: page
    objectName: "overviewView"

    property string by: "Status"
    property var cpu: ({})
    property string openIssue: ""
    property var audit: []
    property var kinds: Kinds.keys
    property var brush: null
    property var live: []
    property string lastPush: ""
    property var tasks: []

    function load() {
        Kinds.load({ limit: 500 }, function (es0) {
            var es = es0.filter(function (e) { return e.t !== null })
            page.audit = es
            page.live = es.slice(0, 14)
        })
        falcon.call("task.list", {}, function (ok, r) { page.tasks = ok ? (r.tasks || []) : [] })
    }
    // CPU right now, for the CPU view: each machine's last report
    function loadCpu() {
        var ms = Fleet.machines.filter(function (m) { return m.online }).slice(0, 120)
        ms.forEach(function (m) {
            falcon.call("hierarchy.pc_state", { pc_id: m.pc_id }, function (ok, r) {
                if (!ok || !r.levels) return
                var c = Object.assign({}, page.cpu); c[m.host] = r.levels.cpu; page.cpu = c
            })
        })
    }
    onByChanged: if (by === "CPU") loadCpu()
    Component.onCompleted: if (falcon.isConnected) load()
    Connections {
        target: falcon
        function onConnected() { page.load() }
        function onPushReceived(type, payload) { page.lastPush = type }
        function onPushText(line, alert) {
            page.live = [{ t: Date.now(), kind: Kinds.of(page.lastPush), actor: "", what: line, host: "", fresh: true }].concat(page.live).slice(0, 40)
        }
    }
    onBrushChanged: if (brush === null) return
    Connections { target: Nav; function onRangeChanged() { page.brush = null } }

    readonly property int gap: 14
    readonly property var ms: Fleet.machines
    readonly property var off: ms.filter(function (m) { return !m.online })
    readonly property var held: ms.filter(function (m) { return m.held !== "" })
    readonly property var iss: Fleet.issues
    readonly property int pings: Fleet.pings.length
    readonly property real since: Time.now - Time.rangeHours(Nav.range) * 3600000
    readonly property var inRange: audit.filter(function (e) { return e.t >= since })
    readonly property bool all: kinds.length === Kinds.keys.length
    readonly property var picked: inRange.filter(function (e) { return kinds.indexOf(e.kind) >= 0 && (!brush || (e.t >= brush[0] && e.t < brush[1])) })
    function toggleKind(k) {
        kinds = all ? [k] : kinds.indexOf(k) >= 0 ? (kinds.length === 1 ? Kinds.keys : kinds.filter(function (x) { return x !== k })) : kinds.concat([k])
    }

    // --- the four figures --------------------------------------------------------------------------
    Row {
        width: parent.width
        spacing: page.gap
        readonly property real cw: (width - 3 * spacing) / 4
        Kpi {
            width: parent.cw
            label: "Waiting on you"
            none: page.ms.length === 0
            noneValue: "0"; noneText: "Nothing waiting"
            readonly property int n: page.iss.length + page.pings
            value: Theme.fmt(n)
            delta: n ? page.iss.length + " issue" + (page.iss.length === 1 ? "" : "s") + " · " + page.pings + " ping" + (page.pings === 1 ? "" : "s") : "Nothing waiting on you"
            dc: n ? Theme.crit : Theme.text3
        }
        Kpi {
            width: parent.cw
            label: "Machines online"
            none: page.ms.length === 0
            noneValue: "0"; noneText: "No machines yet"
            value: String(page.ms.length - page.off.length)
            unit: "/ " + page.ms.length
            delta: page.off.length ? (page.off.length === 1 ? page.off[0].host + " offline" + (page.off[0].seen ? " since " + Time.at(page.off[0].seen) : "") : page.off.length + " offline") : "All online"
            dc: page.off.length ? Theme.crit : Theme.text3
        }
        Kpi {
            width: parent.cw
            label: "Open issues"
            none: page.ms.length === 0
            noneValue: "0"; noneText: "Nothing open"
            value: String(page.iss.length)
            delta: page.iss.length ? ["critical", "high"].map(function (k) { return page.iss.filter(function (x) { return x.sev === k }).length + " " + k }).join(" · ") : "Nothing open"
            dc: page.iss.some(function (x) { return x.sev === "critical" }) ? Theme.crit : Theme.text3
        }
        Kpi {
            width: parent.cw
            label: "Sessions held now"
            none: page.ms.length === 0
            noneValue: "0"; noneText: "Nobody is inside a machine"
            value: String(page.held.length)
            delta: page.held.length ? "Longest: " + page.held[0].held + " on " + page.held[0].host
                                      + (page.held[0].heldFrom ? ", " + Time.dur((Time.now - Time.ms(page.held[0].heldFrom)) / 3600000) : "")
                                    : "Nobody is inside a machine"
        }
    }

    // --- the fleet, and the open issues --------------------------------------------------------------
    Row {
        width: parent.width
        spacing: page.gap
        readonly property real h: Math.max(fleetP.implicitHeight, issuesP.implicitHeight)
        Panel {
            id: fleetP
            width: (parent.width - page.gap) * 7 / 12
            height: parent.h
            title: "Fleet"
            sub: Theme.many(page.ms.length, "machine") + ", " + Theme.many(Fleet.depts.length, "department")
            extra: Segmented { options: ["Status", "CPU", "Version", "Check-in"]; value: page.by; onPicked: function (v) { page.by = v } }
            HostMap {
                width: parent.width
                by: page.by
                cpu: page.cpu
                onOpen: function (h) { Nav.go("machines", h) }
                onMore: Nav.go("machines")
            }
        }
        Panel {
            id: issuesP
            width: (parent.width - page.gap) * 5 / 12
            height: parent.h
            flush: true
            title: "Open issues"
            sub: "by severity · click one to see it here"
            extra: Btn { small: true; kind: "link"; text: "All issues →"; onClicked: Nav.go("issues") }
            Column {
                width: parent.width
                Empty {
                    visible: page.iss.length === 0
                    width: parent.width
                    icon: "check"
                    title: "Nothing open"
                    text: "Violations, unanswered pings, deviations and stuck updates appear here, worst first."
                }
                Repeater {
                    model: page.iss.slice(0, 8)
                    delegate: Column {
                        required property var modelData
                        readonly property bool on: page.openIssue === modelData.id
                        width: parent.width
                        Rectangle {
                            width: parent.width
                            height: 50
                            color: on ? Theme.accentSoft : ia.containsMouse ? Theme.surface2 : "transparent"
                            Rectangle { x: 14; y: 13; width: 8; height: 8; radius: 2; color: Fleet.sevColor(modelData.sev) }
                            Column {
                                x: 32
                                width: parent.width - 32 - 160
                                anchors.verticalCenter: parent.verticalCenter
                                Txt { text: modelData.title; width: parent.width }
                                Txt { text: modelData.subject || ""; mono: true; color: Theme.text3; font.pixelSize: 11; width: parent.width }
                            }
                            Txt { x: parent.width - 150; width: 76; anchors.verticalCenter: parent.verticalCenter; text: modelData.host; mono: true; color: Theme.text3 }
                            Txt {
                                x: parent.width - 74; width: 60
                                anchors.verticalCenter: parent.verticalCenter
                                horizontalAlignment: Text.AlignRight
                                mono: true
                                text: modelData.at ? Time.age(modelData.at) : "—"
                                color: Theme.text3
                            }
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                            MouseArea { id: ia; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                        onClicked: page.openIssue = on ? "" : modelData.id }
                        }
                        Rectangle {
                            visible: on
                            width: parent.width
                            height: visible ? exp.height + 20 : 0
                            color: Theme.surface2
                            Column {
                                id: exp
                                x: 32; y: 8
                                width: parent.width - 46
                                spacing: 3
                                Txt { width: parent.width; color: Theme.text2; font.pixelSize: 12
                                      text: Fleet.typeLabel[modelData.type] + " · " + Fleet.sevWord(modelData.sev) + " · " + modelData.note }
                                Link { text: "Open in Issues →"; font.pixelSize: 12; onClicked: Nav.go("issues", modelData.id) }
                            }
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                        }
                    }
                }
                Item {
                    visible: page.iss.length > 8
                    width: parent.width; height: 38
                    More { x: 14; anchors.verticalCenter: parent.verticalCenter; n: page.iss.length - 8; what: "in Issues →"; onClicked: Nav.go("issues") }
                }
            }
        }
    }

    // --- event volume, and the live stream ------------------------------------------------------------
    Row {
        width: parent.width
        spacing: page.gap
        readonly property real h: Math.max(evP.implicitHeight, liveP.implicitHeight)
        Panel {
            id: evP
            width: (parent.width - page.gap) * 8 / 12
            height: parent.h
            title: "Event volume"
            sub: Theme.fmt(page.picked.length) + " events · " + (page.brush ? Time.hhmm(page.brush[0]) + " – " + Time.hhmm(page.brush[1]) : Nav.range)
            extra: [
                Btn { visible: !page.all || page.brush !== null; small: true; kind: "text"; text: "Clear"; onClicked: { page.kinds = Kinds.keys; page.brush = null } },
                Btn { small: true; text: "Show in audit log"; iconName: "arrowr"
                      onClicked: { Nav.preset = { page: "audit", kinds: page.kinds, brush: page.brush }; Nav.go("audit") } }
            ]
            Column {
                width: parent.width
                spacing: 10
                Flow {
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: Kinds.keys.filter(function (k) { return Kinds.keys.indexOf(k) < 7 || page.audit.some(function (e) { return e.kind === k }) })
                        delegate: Rectangle {
                            required property var modelData
                            readonly property bool on: page.kinds.indexOf(modelData) >= 0
                            width: chip.implicitWidth + 18
                            height: 24
                            radius: 12
                            color: on ? Theme.surface : "transparent"
                            border.width: 1
                            border.color: ca.containsMouse ? Theme.borderStrong : Theme.border
                            Row {
                                id: chip
                                anchors.centerIn: parent
                                spacing: 6
                                Rectangle { width: 8; height: 8; radius: 2; color: Kinds.color(modelData); opacity: on ? 1 : 0.3; anchors.verticalCenter: parent.verticalCenter }
                                Txt { text: Kinds.words[modelData]; font.pixelSize: 12; color: on ? Theme.text2 : Theme.text4; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                                Txt { text: Theme.fmt(page.inRange.filter(function (e) { return e.kind === modelData }).length); mono: true; font.pixelSize: 11; color: Theme.text3; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                            }
                            MouseArea { id: ca; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.toggleKind(modelData) }
                        }
                    }
                    Txt { visible: !page.brush; text: "drag across the chart to pick a time"; color: Theme.text4; font.pixelSize: 11; height: 24; elide: Text.ElideNone }
                }
                EventHistogram {
                    visible: page.inRange.length > 0
                    width: parent.width
                    height: 170
                    entries: page.audit
                    kinds: page.kinds
                    range: Nav.range
                    brush: page.brush
                    onBrushed: function (b) { page.brush = b }
                }
                Empty {
                    visible: page.inRange.length === 0
                    width: parent.width
                    h: 170
                    icon: "barchart"
                    title: "No events in this period"
                    text: "Everything the system records lands here: sessions, actions, flows, pings, updates, deviations and violations."
                }
            }
        }
        Panel {
            id: liveP
            width: (parent.width - page.gap) * 4 / 12
            height: parent.h
            flush: true
            title: "Live activity"
            sub: page.all ? "" : "same kinds as the chart"
            extra: Row {
                spacing: 6
                Rectangle { width: 7; height: 7; radius: 4; color: Theme.ok; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: "streaming"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
            }
            Column {
                width: parent.width
                readonly property var rows: page.live.filter(function (e) { return page.kinds.indexOf(e.kind) >= 0 })
                Empty { visible: parent.rows.length === 0; width: parent.width; h: 200; icon: "thunderbolt"; title: "Quiet"; text: "Each event appears here the moment it is recorded." }
                Repeater {
                    model: parent.rows.slice(0, 12)
                    delegate: Rectangle {
                        required property var modelData
                        width: parent.width
                        height: 30
                        color: "transparent"
                        Txt { x: 14; width: 54; anchors.verticalCenter: parent.verticalCenter; mono: true; color: Theme.text3; font.pixelSize: 12; text: Time.hhmm(modelData.t) }
                        Rectangle { x: 72; width: 7; height: 7; radius: 2; color: Kinds.color(modelData.kind); anchors.verticalCenter: parent.verticalCenter }
                        Txt {
                            x: 88
                            width: parent.width - 102
                            anchors.verticalCenter: parent.verticalCenter
                            textFormat: Text.RichText
                            text: (modelData.actor ? "<span style='font-weight:500'>" + modelData.actor + "</span> " : "") + "<font color='" + Theme.text2 + "'>" + modelData.what + "</font>"
                                  + (modelData.host ? " <font color='" + Theme.text3 + "'>" + modelData.host + "</font>" : "")
                        }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
            }
        }
    }

    // --- the department ------------------------------------------------------------------------------
    Panel {
        width: parent.width
        flush: true
        title: "Departments"
        DeptTable { width: parent.width }
    }
}
