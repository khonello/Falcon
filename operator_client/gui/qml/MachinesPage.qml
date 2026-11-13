import QtQuick
import "."

// MACHINES, as the version 1 concept draws it (docs/design/concepts-admin.html, AdminMachinesPage): which of my machines needs me,
// and what do I do on it? The situation in a sentence; one card per machine, serious first, the department a label on each and a
// filter on the list; a click picks it and draws it on the right (loading in place, then a pulse), Expand opens its details;
// check-ins this week for every machine; and what waits to join: a machine installed without a licence code, let in with the code on its screen.
Page {
    id: page
    objectName: "machinesView"

    property string sel: { var a = Nav.takeArrive("machines"); return a !== null ? String(a) : Nav.sub ? String(Nav.sub) : "" }
    property string exp: ""
    property var dept: null
    property var info: ({})               // machines.list: readings now, address, health note
    property var got: null                // machines.get for the picked one
    property var weeks: ({})              // host -> check_ins
    property var sparks: ({})             // host -> the last 24 hours of CPU, for its card
    property bool loading: false

    readonly property var ms: Fleet.machines.filter(function (m) { return page.dept === null || m.dept === page.dept })
    function serious(m) { return m.online && (m.status === "high" || m.status === "critical") }
    readonly property var look: ms.filter(serious).sort(function (a, b) { return a.host.localeCompare(b.host) })
    readonly property var fine: ms.filter(function (m) { return !serious(m) }).sort(function (a, b) { return a.host.localeCompare(b.host) })
    readonly property var off: ms.filter(function (m) { return !m.online })
    readonly property var held: ms.filter(function (m) { return m.held !== "" })
    readonly property var behind: ms.filter(function (m) { return m.behind })
    readonly property var cur: { for (var i = 0; i < ms.length; i++) if (ms[i].host === sel) return ms[i]; return null }
    readonly property var curInfo: cur ? info[cur.host] || null : null

    function loadInfo() {
        falcon.call("machines.list", {}, function (ok, r) {
            var m = {}
            if (ok) (r.machines || []).forEach(function (x) { m[x.hostname] = x })
            page.info = m
        })
        // check-ins this week, one machine at a time (machines.get carries them)
        Fleet.machines.slice(0, 60).forEach(function (x) {
            falcon.call("machines.get", { pc_id: x.pc_id, range: "24h" }, function (ok, r) {
                if (!ok) return
                var w = Object.assign({}, page.weeks); w[x.host] = r.check_ins || []; page.weeks = w
                var s = Object.assign({}, page.sparks); s[x.host] = (r.series && r.series.cpu ? r.series.cpu : []).map(function (p) { return p.v }); page.sparks = s
            })
        })
    }
    function loadCur() {
        got = null
        if (!cur) return
        var host = cur.host
        loading = true; ldT.restart()
        falcon.call("machines.get", { pc_id: cur.pc_id, range: "24h" }, function (ok, r) { if (ok && page.cur && page.cur.host === host) page.got = r })
    }
    Timer { id: ldT; interval: Theme.loadMs; onTriggered: page.loading = false }
    onCurChanged: loadCur()
    Component.onCompleted: { if (falcon.isConnected) loadInfo(); loadCur(); loadAsks() }
    Connections { target: Fleet; function onLoadedChanged() { page.loadInfo() } }

    function mine(m) { return m.held === Nav.me || m.held === "You" }
    function pct(v) { return v === null || v === undefined ? "—" : Math.round(v) + "%" }
    function whatOf(m) {
        var x = info[m.host] || {}, out = []
        out.push(!m.online ? "Off, last seen " + (m.seen ? Time.dur((Time.now - Time.ms(m.seen)) / 3600000) + " ago" : "a while ago") : "On, " + (m.user ? m.user + " signed in" : "nobody signed in"))
        if (serious(m) || m.status === "warning") { if (m.note) out.push(m.note.charAt(0).toLowerCase() + m.note.slice(1)) }
        if (m.held) out.push(page.mine(m) ? "you are inside" : m.held + " is inside")
        if (m.online && x.cpu >= 90) out.push("CPU at " + Math.round(x.cpu) + "%")
        if (m.online && x.disk >= 90) out.push("disk " + Math.round(x.disk) + "% full")
        if (m.behind && !(serious(m) || m.status === "warning")) out.push("one version behind")
        return out.join(" · ")
    }

    situation: {
        if (!ms.length) return page.dept !== null ? "There are no machines in " + Fleet.deptName(page.dept) + " yet." : "There are no machines yet."
        return (look.length ? Theme.fmt(look.length) + (look.length === 1 ? " needs" : " need") + " a look (" + Theme.listNames(look.map(function (m) { return m.host }), 3) + ")" : "Nothing serious is open")
               + "; " + (off.length ? Theme.fmt(off.length) + " offline" : "all online") + (held.length ? ", " + Theme.fmt(held.length) + " with someone inside" : "")
               + (behind.length ? ", " + Theme.fmt(behind.length) + " behind on the version" : "") + "."
    }
    situationAt: Time.now

    // entering: two Admins are never on one machine at once, and nobody is pushed out (docs/design/v1-it-admin.md)
    Confirm { id: confirm; page: page }
    function enter(m) {
        if (m.held && !mine(m)) {
            confirm.ask({ title: m.held + " is in " + m.host, text: m.held + " is inside now. Two Admins are never on one machine at once, and nobody is pushed out. Send them a message on Messages, or enter when they have left.", ok: "OK" }, null)
            return
        }
        confirm.ask({ title: "Enter " + m.host + "?", text: m.user ? m.user + " is signed in and cannot use the machine while you are in. You get 30 minutes, and can extend them." : "No one is signed in. You get 30 minutes, and can extend them.", ok: "Enter" },
                    function () { falcon.call("hierarchy.traverse", { pc_id: m.pc_id }, function (ok, r) {
                        if (!ok) { Msg.failed(r && r.message ? r.message : "Could not enter"); return }
                        Msg.ok("You are in " + m.host + (m.user ? " · " + m.user + " cannot use it while you are in" : "")) }) })
    }

    // --- the machines, and the picked one ----------------------------------------------------------------
    Row {
        width: parent.width
        spacing: 14
        Box {
            id: listP
            objectName: "machineCards"
            width: (parent.width - 14) * 8 / 12
            height: Math.max(implicitHeight, rightCol.implicitHeight)
            title: "Machines"
            sub: (page.dept !== null ? Fleet.deptName(page.dept) : "every department") + "; one card per machine, serious first; click one to draw it on the right, expand it for its details"
            extra: Select {
                width: 170; small: true
                value: page.dept === null ? "" : page.dept
                options: [{ value: "", label: "Every department" }].concat(Fleet.depts.map(function (d) { return { value: d.id, label: d.name } }))
                onPicked: function (v) { page.dept = v === "" ? null : v; page.sel = ""; page.exp = "" }
            }
            Repeater {
                model: [["look", "Serious", "something serious is open on it", page.look], ["fine", "Fine", "nothing serious", page.fine]]
                delegate: Group {
                    id: grp
                    required property var modelData
                    required property int index
                    visible: modelData[3].length > 0
                    spaced: index > 0 && page.look.length > 0
                    width: listP.innerW
                    title: modelData[1] + " · " + modelData[3].length
                    sub: modelData[2]
                    // four a page, as every list pages (the user, 12 Nov 2026: in place of "and N more"); the machine picked stays on the page shown
                    Paged { id: mgp; items: grp.modelData[3]; per: 4; keep: grp.modelData[3].findIndex(function (m) { return m.host === page.sel }) }
                    paging: mgp
                    Repeater {
                        model: mgp.shown
                        delegate: Card {
                            id: mc
                            required property var modelData
                            readonly property var xi: page.info[modelData.host] || {}
                            objectName: "machine_" + modelData.host
                            width: grp.cardW
                            midW: 200
                            actW: 150
                            icon: "desktop"
                            hot: page.serious(modelData)
                            title: modelData.host
                            tag: modelData.deptName || "no department"
                            line: page.whatOf(modelData)
                            lineHot: page.serious(modelData)
                            opacity: modelData.online ? 1 : 0.7
                            picked: page.sel === modelData.host
                            expandable: true
                            expanded: page.exp === modelData.host
                            onOpen: page.sel = modelData.host
                            onToggle: { page.exp = expanded ? "" : modelData.host; page.sel = modelData.host }
                            // am-facts: the day's CPU as a line and its reading now, then the version
                            mid: Row {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 14
                                Txt { visible: !mc.modelData.online; text: "no data since " + (mc.modelData.seen ? Time.age(mc.modelData.seen) + " ago" : "a while"); color: Theme.text4; font.pixelSize: 12; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                                Row {
                                    visible: mc.modelData.online
                                    spacing: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                    Spark { width: 96; height: 22; max: 100; c: page.serious(mc.modelData) ? Theme.crit : Theme.ser6; values: page.sparks[mc.modelData.host] || []; anchors.verticalCenter: parent.verticalCenter }
                                    Txt { width: Math.max(30, implicitWidth); horizontalAlignment: Text.AlignRight; text: page.pct(mc.xi.cpu); color: Theme.text2; font.pixelSize: 12; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                                }
                                Txt { text: mc.modelData.ver || "—"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                            }
                            // opened: its facts beside who is at the keyboard and when it was entered, then what to do
                            Column {
                                width: parent.width
                                spacing: 10
                                Row {
                                    width: parent.width
                                    spacing: 24
                                    Column {
                                        width: Math.min(420, parent.width - 230 - 24)
                                        y: 2
                                        Repeater {
                                            model: [["Signed in", mc.modelData.user || "nobody"], ["Inside", mc.modelData.held ? (page.mine(mc.modelData) ? "you" : mc.modelData.held) : "nobody"],
                                                    ["Address", mc.xi.ip || "—"], ["Version", mc.modelData.ver + (mc.modelData.behind ? ", one behind" : "")],
                                                    ["Last seen", mc.modelData.online ? "now" : mc.modelData.seen ? Time.age(mc.modelData.seen) + " ago" : "—"]]
                                            delegate: Item {
                                                required property var modelData
                                                required property int index
                                                width: parent.width
                                                height: fv.height + 10
                                                Txt { y: 5; width: 120; text: modelData[0]; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                                                Txt { id: fv; x: 132; y: 5; width: parent.width - 132; text: modelData[1]; font.pixelSize: 13 }
                                                Rectangle { visible: index < 4; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                                            }
                                        }
                                    }
                                    Column {
                                        width: 230
                                        spacing: 6
                                        readonly property var use: page.got && page.cur && page.cur.host === mc.modelData.host ? page.got.keyboard || null : null
                                        Txt { topPadding: 4; text: "At the keyboard"; color: Theme.text3; font.pixelSize: 12 }
                                        Row {
                                            spacing: 6
                                            readonly property bool inUse: !!(parent.use && parent.use.state === "in_use")
                                            Rectangle { width: 7; height: 7; radius: 3.5; anchors.verticalCenter: parent.verticalCenter; color: parent.inUse ? Theme.ok : Theme.text4 }
                                            Txt { font.pixelSize: 13; elide: Text.ElideNone
                                                  text: !mc.modelData.online ? "offline" : !mc.modelData.user ? "nobody signed in" : parent.inUse ? "in use now" : parent.parent.use && parent.parent.use.idle_s !== null && parent.parent.use.idle_s !== undefined ? "idle for " + Time.dur(parent.parent.use.idle_s / 3600) : "idle" }
                                        }
                                        Txt { topPadding: 4; text: "Entered"; color: Theme.text3; font.pixelSize: 12 }
                                        Repeater {
                                            model: page.got && page.cur && page.cur.host === mc.modelData.host && page.got.sessions ? page.got.sessions.slice(0, 3) : []
                                            delegate: Item {
                                                required property var modelData
                                                required property int index
                                                width: 230; height: 27.75
                                                Txt { anchors.verticalCenter: parent.verticalCenter; text: Time.atDay(modelData.started_at); font.pixelSize: 13; elide: Text.ElideNone }
                                                Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone
                                                      text: modelData.ended_at ? Time.dur((Time.ms(modelData.ended_at) - Time.ms(modelData.started_at)) / 3600000) : "inside now" }
                                                Rectangle { visible: index < 2; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                                            }
                                        }
                                    }
                                }
                                Row {
                                    anchors.right: parent.right
                                    spacing: 8
                                    Btn { visible: mc.modelData.behind && mc.modelData.online; small: true; text: "Update now"; onClicked: falcon.call("update.now", { pc_id: mc.modelData.pc_id }, function (ok, r) { if (ok) Msg.ok("Updating now"); else Msg.failed(r && r.message ? r.message : "Not done") }) }
                                    Btn { small: true; kind: "primary"; text: page.mine(mc.modelData) ? "You are inside" : "Enter"
                                          enabled: mc.modelData.online && !page.mine(mc.modelData); onClicked: page.enter(mc.modelData) }
                                    Btn { small: true; kind: "text"; text: "Run an action"; onClicked: Nav.goAsk("actions", null, "Actions opens with " + mc.modelData.host + " picked.", mc.modelData.host) }
                                }
                            }
                        }
                    }
                }
            }
            Quiet { visible: page.ms.length === 0; text: "No machines yet. A machine joins by itself with its licence code, at setup." }
        }

        // the picked machine: its health and the last 24 hours, then storage and what is running
        Column {
            id: rightCol
            width: (parent.width - 14) * 4 / 12
            spacing: 14
            Box {
                id: pickP
                objectName: "machinePicked"
                width: parent.width
                title: page.cur ? page.cur.host : "No machine picked"
                sub: !page.cur ? "click a machine on the left to draw it here"
                     : (page.cur.user ? page.cur.user + (page.cur.online ? " is signed in" : " was the last signed in") : "nobody signed in") + (page.cur.held ? " · " + (page.mine(page.cur) ? "you are" : page.cur.held + " is") + " inside" : "")
                St { visible: page.cur !== null; text: page.cur ? Fleet.words[page.cur.online ? page.cur.status : "offline"] : ""; c: page.cur ? (!page.cur.online ? Theme.text4 : page.serious(page.cur) ? Theme.crit : page.cur.status === "warning" ? Theme.med : Theme.ok) : Theme.text4 }
                Txt {
                    visible: page.cur !== null && page.got !== null && !!page.got.about
                    width: parent.width
                    height: visible ? implicitHeight - 4 : 0
                    color: Theme.text3
                    font.pixelSize: 12
                    text: !page.got || !page.got.about ? "" : [page.got.about.os, page.got.about.memory_total_mb ? Math.round(page.got.about.memory_total_mb / 1024) + " GB memory" : "",
                          page.cur && !page.cur.online ? "off" : page.got.about.boot_at ? "up " + Math.floor((Time.now - Time.ms(page.got.about.boot_at)) / 3600000) + "h" : "", page.got.about.registered_at ? "registered " + Time.day(page.got.about.registered_at) + " " + new Date(Time.ms(page.got.about.registered_at)).getFullYear() : ""].filter(function (s) { return s }).join(" · ")
                }
                // off: the graphs stay, faded, with what they show said across them; the panel keeps its size (the user, 13 Nov 2026)
                readonly property bool off: page.cur !== null && !page.cur.online
                readonly property string offNote: off ? page.cur.host + " is off" + (page.cur.seen ? " · last seen " + Time.age(page.cur.seen) + " ago" : "") + " · no new readings" : ""
                Repeater {
                    model: [["CPU", "cpu", Theme.ser6], ["Memory", "memory", Theme.ser3]]
                    delegate: Column {
                        required property var modelData
                        width: parent.width
                        spacing: 4
                        readonly property var pts: page.cur && page.got && page.got.series && page.got.series[modelData[1]] ? page.got.series[modelData[1]] : []
                        Item {
                            width: parent.width
                            height: hv.height
                            Txt { id: hl; y: hv.baselineOffset - baselineOffset; text: modelData[0]; font.pixelSize: 13; elide: Text.ElideNone }
                            Txt { id: hv; x: hl.implicitWidth + 8; text: parent.parent.pts.length && !page.loading ? Math.round(parent.parent.pts[parent.parent.pts.length - 1].v) + "%" : "—"; font.pixelSize: 15; font.weight: Font.DemiBold; elide: Text.ElideNone }
                            Txt { x: hv.x + hv.implicitWidth + 8; y: hv.baselineOffset - baselineOffset; text: pickP.off ? "the last it read, before it went off" : "last 24 hours"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                        }
                        Item {
                            width: parent.width; height: 164
                            TimeChart {
                                anchors.fill: parent
                                opacity: pickP.off ? 0.35 : 1
                                hours: 24; unit: "%"; yMax: 100
                                series: [{ name: modelData[0], c: modelData[2], pts: parent.parent.pts.map(function (x) { return [Time.ms(x.at), x.v] }) }]
                            }
                            Rectangle {
                                visible: pickP.off
                                anchors.centerIn: parent
                                width: Math.min(parent.width - 24, offT.implicitWidth + 24); height: offT.implicitHeight + 14
                                radius: Theme.radius
                                color: Theme.surface2
                                border.width: 1; border.color: Theme.border
                                Txt { id: offT; anchors.centerIn: parent; width: parent.width - 24; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; elide: Text.ElideNone
                                      text: pickP.offNote; color: Theme.text2; font.pixelSize: 12 }
                            }
                        }
                    }
                }
                Loading { parent: pickP; on: page.loading && page.cur !== null; under: pickP.headerHeight; text: page.cur ? "Loading " + page.cur.host : "Loading" }
                Pulse { parent: pickP; key: page.sel || null }
            }
            Box {
                id: runP
                objectName: "machineRunning"
                width: parent.width
                gap: 10
                readonly property real disk: page.got && page.got.about && page.got.about.disk_percent !== null && page.got.about.disk_percent !== undefined ? page.got.about.disk_percent : -1
                readonly property real size: page.got && page.got.about && page.got.about.disk_total_gb ? page.got.about.disk_total_gb : 0
                // storage
                Column {
                    width: parent.width
                    spacing: page.cur ? 8 : 4
                    Item {
                        width: parent.width
                        height: sv.height
                        Txt { id: sl; y: sv.baselineOffset - baselineOffset; text: "Storage"; font.pixelSize: 13; elide: Text.ElideNone }
                        Txt { id: sv; x: sl.implicitWidth + 8; text: page.cur && runP.disk >= 0 && !page.loading ? Math.round(runP.disk) + "%" : "—"; font.pixelSize: 15; font.weight: Font.DemiBold; elide: Text.ElideNone }
                        Txt { visible: page.cur !== null; x: sv.x + sv.implicitWidth + 8; y: sv.baselineOffset - baselineOffset; text: page.cur && !page.cur.online ? "used, drive C:, last known" : "used, drive C:"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                    }
                    Rectangle {
                        width: parent.width; height: 8; radius: 4; color: Theme.grid
                        Rectangle { width: parent.width * Math.max(0, page.cur ? runP.disk : 0) / 100; height: parent.height; radius: 4
                                    color: runP.disk >= 90 ? Theme.crit : Theme.mix(Theme.ser1, Theme.surface, 0.8) }
                    }
                    Item {
                        visible: page.cur !== null && runP.size > 0 && runP.disk >= 0
                        width: parent.width
                        height: visible ? su.height : 0
                        Txt { id: su; textFormat: Text.StyledText; font.pixelSize: 12; color: Theme.text3; elide: Text.ElideNone
                              text: "<b><font color='" + Theme.text2 + "'>" + Math.round(runP.size * runP.disk / 100) + " GB</font></b> used" }
                        Txt { anchors.right: parent.right; textFormat: Text.StyledText; font.pixelSize: 12; color: Theme.text3; elide: Text.ElideNone
                              text: "<b><font color='" + Theme.text2 + "'>" + Math.round(runP.size * (1 - runP.disk / 100)) + " GB</font></b> free of " + Math.round(runP.size) + " GB" }
                    }
                }
                // running now: a second section under a rule
                Column {
                    width: parent.width
                    spacing: page.cur ? 8 : 4
                    topPadding: page.cur ? 14 : 0
                    Rectangle { visible: page.cur !== null; width: parent.width; height: 1; color: Theme.border }
                    Item {
                        width: parent.width
                        height: rl.height + (page.cur ? 6 : 0)
                        Txt { id: rl; y: page.cur ? 6 : 0; text: "Running now"; font.pixelSize: 13; elide: Text.ElideNone }
                        Txt { x: rl.implicitWidth + 8; y: rl.y; text: page.cur ? "the busiest programs; point at one to end it" : "the most busy programs"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                    }
                    Txt { visible: !page.cur; text: "Shown for the machine you pick."; color: Theme.text3; font.pixelSize: 13 }
                    // room for its seven rows whatever the machine's state, so the panel keeps one size (the user, 13 Nov 2026)
                    Column {
                        visible: page.cur !== null
                        width: parent.width
                        height: 22 + 7 * 29
                        readonly property bool off: page.cur !== null && !page.cur.online
                        readonly property var rows: page.got && page.got.processes && page.got.processes.items ? page.got.processes.items.slice().sort(function (a, b) { return (b.cpu || 0) - (a.cpu || 0) }).slice(0, 7) : []
                        Item {
                            width: parent.width; height: 22
                            Txt { text: "Program"; color: Theme.text4; font.pixelSize: 12 }
                            Txt { x: parent.width - 44 - 8 - 60 - 8 - 44; width: 44; horizontalAlignment: Text.AlignRight; text: "CPU"; color: Theme.text4; font.pixelSize: 12 }
                            Txt { x: parent.width - 44 - 8 - 60; width: 60; horizontalAlignment: Text.AlignRight; text: "Memory"; color: Theme.text4; font.pixelSize: 12 }
                        }
                        Repeater {
                            model: parent.off ? [] : parent.rows
                            delegate: Item {
                                required property var modelData
                                required property int index
                                width: parent.width; height: 29
                                MouseArea { id: pr; anchors.fill: parent; hoverEnabled: true }
                                Txt { width: parent.width - 44 - 8 - 60 - 8 - 44 - 8; anchors.verticalCenter: parent.verticalCenter; text: modelData.name; mono: true; font.pixelSize: 13 }
                                Txt { x: parent.width - 44 - 8 - 60 - 8 - 44; width: 44; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter; text: (modelData.cpu || 0).toFixed(0) + "%"; font.pixelSize: 13; elide: Text.ElideNone }
                                Txt { x: parent.width - 44 - 8 - 60; width: 60; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone
                                      text: modelData.memory_mb >= 1000 ? (modelData.memory_mb / 1000).toFixed(1) + " GB" : modelData.memory_mb + " MB" }
                                Btn { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; small: true; kind: "text"; danger: true; text: "End"; opacity: pr.containsMouse || hovered ? 1 : 0
                                      onClicked: falcon.call("machines.end_program", { pc_id: page.cur.pc_id, name: modelData.name }, function (ok, r) { if (ok) Msg.ok("Ended"); else Msg.failed(r && r.message ? r.message : "Not done") }) }
                                Rectangle { visible: index < parent.parent.rows.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                            }
                        }
                        Item {
                            visible: parent.off || parent.rows.length === 0
                            width: parent.width; height: 7 * 29
                            Txt { anchors.centerIn: parent; width: parent.width - 24; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; elide: Text.ElideNone
                                  color: Theme.text3; font.pixelSize: 13
                                  text: parent.parent.off ? page.cur.host + " is off; what is running on it is not known until it is back." : "Nothing reported yet." }
                        }
                    }
                }
                Loading { parent: runP; on: page.loading && page.cur !== null; under: 14; text: page.cur ? "Loading " + page.cur.host : "Loading" }
                Pulse { parent: runP; key: page.sel || null }
            }
        }
    }

    // --- check-ins this week (am-wk: the host, a column a day, the count) ------------------------------------------
    Box {
        objectName: "checkIns"
        width: parent.width
        title: "Check-ins this week"
        sub: "a check-in is the machine's worker reaching the Engine: the PC is on and connected, whether or not anyone is signed in to it"
        Column {
            id: wk
            width: parent.width
            readonly property var days: { var w = page.weeks[Object.keys(page.weeks)[0]] || []; return w.map(function (d) { return d.day }) }
            readonly property real dayW: (width - 12 - 76 - 12 - 96 - 12 - 12 * Math.max(0, days.length - 1)) / Math.max(1, days.length)
            Item {
                width: parent.width; height: 31.5
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                Repeater {
                    model: wk.days
                    delegate: Txt { required property var modelData; required property int index; x: 6 + 76 + 12 + index * (wk.dayW + 12); width: wk.dayW; y: 7
                                    text: index === wk.days.length - 1 ? "Today" : Time.dayName(modelData); color: Theme.text4; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter }
                }
            }
            Repeater {
                model: page.ms.slice().sort(function (a, b) { return a.host.localeCompare(b.host) })
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    readonly property var w: page.weeks[modelData.host] || []
                    width: parent.width; height: 33.75
                    color: page.sel === modelData.host || wa.containsMouse ? Theme.surface2 : "transparent"
                    MouseArea { id: wa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.sel = modelData.host }
                    Txt { x: 6; width: 76; anchors.verticalCenter: parent.verticalCenter; text: modelData.host; mono: true; font.pixelSize: 13 }
                    Repeater {
                        model: parent.w
                        delegate: Item {
                            required property var modelData
                            required property int index
                            x: 6 + 76 + 12 + index * (wk.dayW + 12)
                            width: wk.dayW; height: 33.75
                            Icon { anchors.centerIn: parent; name: modelData.yes ? "check" : "close"; size: 12; color: modelData.yes ? Theme.text2 : Theme.text4 }
                        }
                    }
                    Txt { anchors.right: parent.right; anchors.rightMargin: 6; width: 96; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone
                          text: parent.w.length ? Theme.fmt(parent.w.filter(function (d) { return d.yes }).length) + " of " + parent.w.length + " days" : "—" }
                    Rectangle { visible: index < page.ms.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                }
            }
        }
    }

    // --- add a machine: it only registers; its department is set on Departments ----------------------------------
    // installed without a licence code: an Admin lets it in with the code on its screen (one with a code has joined by itself)
    property var asks: []
    property var codes: ({})
    function loadAsks() { falcon.call("enroll.list", {}, function (ok, r) { page.asks = ok ? (r.requests || []) : [] }) }
    Connections { target: falcon; function onPushReceived(type) { if (/^enroll/.test(type)) page.loadAsks() } }
    function letIn(a) {
        falcon.call("enroll.confirm", { enrollment_id: a.id, code: String(page.codes[a.id] || "").trim() }, function (ok, r) {
            if (ok) { Msg.ok(a.hostname + " joined · its key went to the machine"); page.loadAsks(); Fleet.refresh() } else Msg.failed(r && r.message ? r.message : "Wrong code") })
    }
    function refuse(a) {
        falcon.call("enroll.refuse", { enrollment_id: a.id, reason: "refused" }, function (ok, r) { if (ok) { Msg.ok("Refused " + a.hostname); page.loadAsks() } else Msg.failed(r && r.message ? r.message : "Not refused") })
    }
    Box {
        objectName: "waitingToJoin"
        visible: page.asks.length > 0
        width: parent.width
        title: "Waiting to join · " + page.asks.length
        sub: "installed without a licence code; type the code on its screen to let it in"
        PagedList {   // a long list pages in place (the user, 11 Nov 2026)
            id: ap; items: page.asks; per: 4
            delegate: Rectangle {
                id: jr
                required property var modelData
                width: parent.width; height: 52; radius: 8; color: Theme.surface2
                Rectangle { x: 10; anchors.verticalCenter: parent.verticalCenter; width: 30; height: 30; radius: 15; color: Theme.surface3
                            Icon { anchors.centerIn: parent; name: "desktop"; size: 14; color: Theme.text2 } }
                Column { x: 50; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 50 - acts.width - 24; spacing: 1
                    Row { spacing: 8
                        Txt { text: jr.modelData.hostname; mono: true; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideNone }
                        Txt { text: jr.modelData.peer || ""; mono: true; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone } }
                    Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12
                          text: "asked to join at " + Time.hhmm(jr.modelData.created_at) + ", as " + (jr.modelData.requested_level === "admin" ? "an IT Admin's PC" : "a person's PC") } }
                Row { id: acts; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                    Field { small: true; width: 170; placeholderText: "The code on its screen"; text: page.codes[jr.modelData.id] || ""
                            onTextEdited: { var c = Object.assign({}, page.codes); c[jr.modelData.id] = text; page.codes = c } }
                    Btn { small: true; text: "Refuse"; onClicked: page.refuse(jr.modelData) }
                    Btn { small: true; kind: "primary"; text: "Let it in"; enabled: String(page.codes[jr.modelData.id] || "").trim() !== ""; onClicked: page.letIn(jr.modelData) } }
            }
        }
    }
}
