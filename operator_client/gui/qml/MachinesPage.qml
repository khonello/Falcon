import QtQuick
import "."

// MACHINES (an Admin's console): four figures that also filter, the list worst first, the machine
// picked beside it, and its last 24 hours under both. A click selects; its own page (charts,
// processes, sessions, files) is reached only by "Open its page →" (docs/design/click-in-place.md).
Page {
    id: page
    objectName: "machinesView"

    property string f: ""                 // "" | online | look | current
    property bool insideOnly: false
    property string sel: ""
    property var cpu: ({})

    readonly property var all: Fleet.machines.slice().sort(function (a, b) {
        return Fleet.order[a.status] - Fleet.order[b.status] || a.host.localeCompare(b.host)
    })
    readonly property var held: Fleet.machines.filter(function (m) { return m.held !== "" })
    readonly property int off: Fleet.machines.filter(function (m) { return !m.online }).length
    readonly property int behind: Fleet.machines.filter(function (m) { return m.behind }).length
    readonly property int look: Fleet.machines.filter(function (m) { return m.status !== "healthy" }).length
    readonly property var rows: all.filter(function (m) {
        var q = list.query.toLowerCase()
        return (f === "" || (f === "online" ? m.online : f === "look" ? m.status !== "healthy" : !m.behind))
            && (!insideOnly || m.held !== "")
            && (m.host + " " + m.user).toLowerCase().indexOf(q) >= 0
    })
    readonly property var cur: {
        for (var i = 0; i < rows.length; i++) if (rows[i].host === sel) return rows[i]
        return rows.length ? rows[0] : null
    }
    // each machine's readings now, its address and what its health is about (machines.list); the one picked over
    // the top bar's range (machines.get), drawn under the list
    property var info: ({})
    property var series: null
    function loadInfo() {
        falcon.call("machines.list", {}, function (ok, r) {
            var m = {}, c = {}
            if (ok) (r.machines || []).forEach(function (x) { m[x.hostname] = x; if (x.cpu !== null && x.cpu !== undefined) c[x.hostname] = x.cpu })
            page.info = m; page.cpu = c
        })
    }
    function loadSeries() {
        series = null
        if (!cur) return
        var host = cur.host
        falcon.call("machines.get", { pc_id: cur.pc_id, range: Nav.range }, function (ok, r) { if (ok && page.cur && page.cur.host === host) page.series = r.series || null })
    }
    onCurChanged: loadSeries()
    Component.onCompleted: loadInfo()
    Connections { target: Fleet; function onLoadedChanged() { page.loadInfo() } }
    Connections { target: Nav; function onRangeChanged() { page.loadSeries() } }
    readonly property var curInfo: cur ? info[cur.host] || null : null
    function pct(v) { return v === null || v === undefined ? "—" : Math.round(v) + "%" }
    readonly property var labels: ({ "": "Machines", online: "Online", look: "Need a look", current: "On the current version" })

    Confirm { id: confirm; page: page }
    function enter(m) {
        confirm.ask({
            title: m.held ? "End " + m.held + "'s session and enter " + m.host + "?" : "Enter " + m.host + "?",
            text: m.held ? m.held + " is in this machine now and is not warned first. " + (m.user || "Nobody") + " stays locked out while you are in."
                 : m.user ? m.user + " is signed in and is locked out while you are in. You get 30 minutes, and can extend them."
                 : "No one is signed in. You get 30 minutes, and can extend them.",
            ok: m.held ? "End and enter" : "Enter", danger: !!m.held
        }, function () {
            falcon.call("hierarchy.traverse", { pc_id: m.pc_id, force: true }, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Could not enter"); return }
                Msg.ok("You are in " + m.host + (m.user ? " · " + m.user + " is locked out" : ""))
            })
        })
    }

    Strip {
        width: parent.width
        on: page.f === "" ? null : page.f
        onPick: function (k) { page.f = k === null ? "" : k }
        items: [
            { label: "Machines", value: Theme.fmt(Fleet.machines.length), delta: "in this department" },
            { key: "online", label: "Online", value: Theme.fmt(Fleet.machines.length - page.off), unit: "/ " + Theme.fmt(Fleet.machines.length),
              delta: page.off ? Theme.fmt(page.off) + " not checking in" : "every one", dc: page.off ? Theme.crit : undefined },
            { key: "look", label: "Need a look", value: Theme.fmt(page.look), delta: page.look ? "not healthy, or offline" : "every one is healthy",
              dc: Fleet.machines.some(function (m) { return m.status === "critical" }) ? Theme.crit : undefined },
            { key: "current", label: "On the current version", value: Theme.fmt(Fleet.machines.length - page.behind), unit: "/ " + Theme.fmt(Fleet.machines.length),
              delta: page.behind ? Theme.fmt(page.behind) + " still on an older one" : "every one on " + (Fleet.version || "the current version") }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            title: page.labels[page.f]
            sub: page.f !== "" ? Theme.fmt(page.rows.length) : "worst first · click one to see it on the right"
            subLink: page.f !== "" ? "every machine" : ""
            onSubLinkClicked: page.f = ""
            placeholder: "Filter by machine or person"
            tools: Segmented {
                visible: page.held.length > 0
                options: [{ value: "all", label: "All" }, { value: "in", label: "Someone inside · " + page.held.length }]
                value: page.insideOnly ? "in" : "all"
                onPicked: function (v) { page.insideOnly = v === "in" }
            }
            rows: page.rows
            rowKey: "host"
            pick: page.cur ? page.cur.host : null
            onPicked: function (k) { page.sel = k }
            icon: "desktop"
            nameTitle: "Machine"
            nameMono: true
            nameText: function (m) { return m.host }
            nameLine: function (m) { return (m.user || "No one signed in") + (m.held ? " · " + m.held + " inside" : "") }
            cols: [
                { title: "Version", width: 90, text: function (m) { return m.ver || "—" } },
                { title: "CPU", width: 90, text: function (m) { return page.cpu[m.host] !== undefined ? Math.round(page.cpu[m.host]) + "%" : "—" } },
                { title: "Last seen", width: 110, text: function (m) { return m.online ? "now" : Time.ago(m.seen) } }
            ]
            now: function (m) {
                var k = Fleet.mark(m.status)
                return [Fleet.words[m.status], k === "crit" || k === "high" || k === "offline" ? "bad" : k === "watch" ? "wait" : "good"]
            }
            showEmpty: Fleet.loaded && Fleet.machines.length === 0
            emptyIcon: "desktop"
            emptyTitle: "No machines in this department"
            emptyText: "The Super User registers machines into a department. They show up here when they do."
        }
        SidePanel {
            id: side
            width: (parent.width - 14) * 4 / 12
            readonly property var m: page.cur
            showEmpty: m === null
            emptyIcon: "desktop"
            emptyTitle: "Nothing to show"
            emptyText: "Pick a machine in the list."
            title: m ? m.host : ""
            sub: m && page.sel === m.host ? "the one you picked" : "needs you most · click another"
            facts: m ? [
                ["Health", Fleet.words[m.status], m.status === "critical" || m.status === "high" ? Theme.crit : null, false, false, "",
                 m.status !== "healthy" ? (page.curInfo && page.curInfo.note ? page.curInfo.note : m.note) : ""],
                ["Signed in", m.user || "No one"],
                ["Inside it", m.held ? m.held + (m.heldFrom ? ", " + Time.dur((Time.now - Time.ms(m.heldFrom)) / 3600000) : "") : "Nobody else"],
                ["Version", m.ver || "—", m.behind ? Theme.med : null, true],
                ["CPU now", page.cpu[m.host] !== undefined ? Math.round(page.cpu[m.host]) + "%" : "—"],
                ["Disk", page.pct(page.curInfo ? page.curInfo.disk : null)],
                ["Last seen", m.online ? "now" : Time.ago(m.seen)],
                ["IP address", page.curInfo && page.curInfo.ip ? page.curInfo.ip : "—", null, true]
            ] : []
            actions: [
                Btn {
                    text: "Enter session"
                    // you cannot enter a machine you are already inside
                    enabled: side.m !== null && side.m.online && !(page.curInfo && page.curInfo.held_by_you)
                    tip: page.curInfo && page.curInfo.held_by_you ? "You are inside it now" : !side.m || side.m.online ? "" : "It is offline"

                    onClicked: page.enter(page.cur)
                },
                Btn { kind: "primary"; text: "Open its page →"; onClicked: Nav.go("machines", page.cur.host) }
            ]
        }
    }

    Panel {
        id: mchart
        visible: page.cur !== null
        width: parent.width
        title: page.cur ? page.cur.host + " · the last " + ({ "1h": "hour", "6h": "6 hours", "24h": "24 hours", "7d": "7 days" })[Nav.range] : ""
        sub: "CPU shaded, memory as the purple line · the same machine as on the right"
        readonly property var cpuPts: page.series && page.series.cpu ? page.series.cpu.map(function (x) { return [Time.ms(x.at), x.v] }) : []
        readonly property var memPts: page.series && page.series.memory ? page.series.memory.map(function (x) { return [Time.ms(x.at), x.v] }) : []
        TimeChart {
            visible: mchart.cpuPts.length > 1 || mchart.memPts.length > 1
            width: parent.width; height: 160; unit: "%"; yMax: 100
            series: [{ name: "CPU", c: Theme.ser6, pts: mchart.cpuPts }, { name: "Memory", c: Theme.ser3, pts: mchart.memPts }]
        }
        Empty {
            visible: mchart.cpuPts.length <= 1 && mchart.memPts.length <= 1
            width: parent.width
            h: 170
            icon: "linechart"
            title: "Nothing reported over this range yet"
            text: "A machine reports its readings while its Worker runs. Its readings right now are on the right."
        }
    }
}
