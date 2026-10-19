import QtQuick
import "."

// A MACHINE'S OWN PAGE: who it is and how it is, Enter session and Run action; then its metrics,
// processes, sessions and files in tabs, with everything the record holds about it beside them.
Page {
    id: page
    objectName: "machineView"
    bare: true

    readonly property var m: Fleet.byHost[Nav.sub] || null
    property var state0: null
    readonly property var mach: got && got.machine ? got.machine : ({})
    property var got: null                 // machines.get: its readings over the range, and what it runs
    property var events: []
    property var running: []
    property var actions: []
    property string tab: "metrics"
    readonly property var sessions: Fleet.sessionsToday.filter(function (s) { return page.m && s.hostname === page.m.host })

    Connections { target: Nav; function onRangeChanged() { if (page.m) falcon.call("machines.get", { pc_id: page.m.pc_id, range: Nav.range }, function (ok, r) { page.got = ok ? r : null }) } }
    function load() {
        if (!m) return
        falcon.call("hierarchy.pc_state", { pc_id: m.pc_id }, function (ok, r) { page.state0 = ok ? r : null })
        falcon.call("machines.get", { pc_id: m.pc_id, range: Nav.range }, function (ok, r) { page.got = ok ? r : null })
        Kinds.load({ limit: 12, pc_id: m.pc_id }, function (es) { page.events = es.slice(0, 12) })
        falcon.call("control.programs", { pc_ids: [m.pc_id] }, function (ok, r) { page.running = ok ? (r.running || []) : [] })
        falcon.call("control.action_list", {}, function (ok, r) {
            if (!ok) return
            var a = r.actions || {}, out = []
            ;["control", "monitoring"].forEach(function (k) { (a[k] || []).forEach(function (x) { out.push(x) }) })
            if ((a.custom || []).length) { out.push({ divider: true }); (a.custom || []).forEach(function (x) { out.push(x) }) }
            page.actions = out
        })
    }
    onMChanged: load()
    Component.onCompleted: load()

    Confirm { id: confirm; page: page }
    DropMenu {
        id: runMenu
        items: page.actions.map(function (a) { return a.divider ? { divider: true } : { key: a.id, label: a.name } })
        onPicked: function (id) {
            falcon.call("control.action_run", { action_id: id, pc_id: page.m.pc_id }, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Not started"); return }
                Msg.ok("Started on " + page.m.host)
            })
        }
    }
    function enter() {
        var x = m
        confirm.ask({
            title: x.held ? "End " + x.held + "'s session and enter " + x.host + "?" : "Enter " + x.host + "?",
            text: x.held ? x.held + " is in this machine now and is not warned first. " + (x.user || "Nobody") + " stays locked out while you are in."
                 : x.user ? x.user + " is signed in and is locked out while you are in. You get 30 minutes, and can extend them."
                 : "No one is signed in. You get 30 minutes, and can extend them.",
            ok: x.held ? "End and enter" : "Enter", danger: !!x.held
        }, function () {
            falcon.call("hierarchy.traverse", { pc_id: x.pc_id, force: true }, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Could not enter"); return }
                Msg.ok("You are in " + x.host)
            })
        })
    }

    Panel {
        visible: page.m === null
        width: parent.width
        Empty { width: parent.width; icon: "desktop"; title: "No such machine here"; text: Nav.sub + " is not one of this console's machines."; act: "Back to Machines"; onActed: Nav.go("machines") }
    }

    // --- who it is, and how it is ------------------------------------------------------------------------
    Rectangle {
        visible: page.m !== null
        width: parent.width
        height: headCol.height + 32
        radius: Theme.radius
        color: Theme.surface
        border.width: 1
        border.color: Theme.border
        Column {
            id: headCol
            x: 16; y: 16
            width: parent.width - 32
            spacing: 14
            Item {
                width: parent.width
                height: Math.max(nameCol.height, btns.height)
                Column {
                    id: nameCol
                    spacing: 2
                    Row {
                        spacing: 10
                        Txt { text: page.m ? page.m.host : ""; mono: true; font.pixelSize: 22; font.weight: Font.Medium; elide: Text.ElideNone }
                        Row {
                            spacing: 6
                            anchors.verticalCenter: parent.verticalCenter
                            HealthMark { k: page.m ? Fleet.mark(page.m.status) : "quiet"; anchors.verticalCenter: parent.verticalCenter }
                            Txt { text: page.m ? Fleet.words[page.m.status] : ""; elide: Text.ElideNone }
                        }
                    }
                    Txt {
                        visible: page.m && page.m.note !== ""
                        text: page.m ? page.m.note : ""
                        color: page.m && (page.m.status === "critical" || page.m.status === "high") ? Theme.crit : page.m && page.m.status === "warning" ? Theme.med : Theme.text3
                    }
                }
                Row {
                    id: btns
                    anchors.right: parent.right
                    spacing: 8
                    Btn { text: "Enter session"; enabled: page.m !== null && page.m.online && page.m.held !== "You"; onClicked: page.enter() }
                    Btn { id: runBtn; kind: "primary"; text: "Run action"; iconName: "chevd"; iconRight: true; onClicked: runMenu.openUnder(runBtn) }
                }
            }
            Rectangle {
                visible: page.m !== null && page.m.held !== ""
                width: parent.width
                height: visible ? 40 : 0
                radius: 5
                color: page.m && page.m.held === "You" ? Theme.accentSoft : Theme.alpha(Theme.ser3, 0.10)
                Row {
                    visible: page.m !== null && page.m.held === "You"
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    Btn { small: true; danger: true; text: "Leave session"
                          onClicked: falcon.call("hierarchy.end_session", { session_id: page.m.session.session_id }, function (ok, r) {
                              if (!ok) { Msg.failed(r && r.message ? r.message : "Still inside"); return }
                              Msg.ok("Left " + page.m.host + (page.m.user ? "; " + page.m.user + " has it back" : ""))
                              Fleet.refresh()
                          }) }
                }
                Row {
                    x: 12
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    Icon { name: "login"; size: 14; color: Theme.ser3; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: page.m ? (page.m.held === "You" ? "You are in a session on this machine" : page.m.held + " is in a session on this machine") : ""
                          font.weight: Font.DemiBold; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                    Txt {
                        anchors.verticalCenter: parent.verticalCenter
                        color: Theme.text2
                        elide: Text.ElideNone
                        text: page.m && page.m.heldFrom ? " since " + Time.hhmm(page.m.heldFrom) + " · " + Time.dur((Time.now - Time.ms(page.m.heldFrom)) / 3600000)
                                                         + ". " + (page.m.user || "Its owner") + " can't use it until " + (page.m.held === "You" ? "you leave." : "they leave.") : ""
                    }
                }
            }
            Grid {
                width: parent.width
                columns: Math.max(1, Math.floor(width / 170))
                columnSpacing: 20
                rowSpacing: 12
                Repeater {
                    model: page.m ? [["User", page.m.user || "—"], ["Department", page.m.deptName], ["Version", page.m.ver || "—", true],
                                     ["IP address", page.mach.ip || page.m.ip || "—", true], ["OS", page.mach.os || page.m.os || "—"],
                                     ["Agent uptime", page.mach.agent_started_at && page.m.online ? Time.span((Time.now - Time.ms(page.mach.agent_started_at)) / 3600000) : "—"],
                                     ["Last check-in", page.m.online ? "seconds ago" : Time.ago(page.m.seen)],
                                     ["Admins", (Fleet.dept(page.m.dept) || { admins: [] }).admins.map(function (a) { return a.name }).join(", ") || "None"]] : []
                    Column {
                        required property var modelData
                        width: 150
                        Txt { text: modelData[0]; color: Theme.text3; font.pixelSize: 12 }
                        Txt { text: modelData[1]; mono: !!modelData[2]; font.weight: Font.Medium; width: parent.width }
                    }
                }
            }
        }
    }

    // --- its tabs, and its events -------------------------------------------------------------------
    Row {
        visible: page.m !== null
        width: parent.width
        spacing: 14
        Column {
            width: (parent.width - 14) * 8 / 12
            spacing: 14
            Tabs {
                width: parent.width
                tabs: [{ key: "metrics", label: "Metrics" }, { key: "proc", label: "Processes" }, { key: "sess", label: "Sessions" }, { key: "files", label: "Files" }]
                current: page.tab
                onPicked: function (k) { page.tab = k }
            }
            // metrics: its readings over the top bar's range (machines.get), else its levels now
            Grid {
                visible: page.tab === "metrics"
                width: parent.width
                columns: 2
                spacing: 14
                Repeater {
                    model: page.got && page.got.series ? [["CPU", "cpu", "%", Theme.ser1, 90], ["Memory", "memory", "%", Theme.ser2, null], ["Disk", "disk", "%", Theme.ser5, 90], ["Network in", "net_kbps", " KB/s", Theme.ser3, null]]
                                                       : [["CPU", "cpu", "%", Theme.ser1, 90], ["Memory", "memory", "%", Theme.ser2, null], ["Idle", "idle_s", " s", Theme.ser3, null]]
                    Panel {
                        required property var modelData
                        width: (parent.width - 14) / 2
                        title: modelData[0]
                        sub: mp.pts.length ? "now " + Math.round(mp.pts[mp.pts.length - 1].v) + modelData[2]
                           : page.state0 && page.state0.levels && page.state0.levels[modelData[1]] !== undefined ? "now " + Math.round(page.state0.levels[modelData[1]]) + modelData[2] : "no reading yet"
                        id: mp
                        readonly property var pts: page.got && page.got.series && page.got.series[modelData[1]] ? page.got.series[modelData[1]] : []
                        TimeChart { visible: mp.pts.length > 1; width: parent.width; height: 150; unit: modelData[2].trim()
                                    yMax: modelData[2] === "%" ? 100 : 0; threshold: modelData[4]
                                    series: [{ name: modelData[0], c: modelData[3], pts: mp.pts.map(function (x) { return [Time.ms(x.at), x.v] }) }] }
                        Empty { visible: mp.pts.length <= 1; width: parent.width; h: 120; icon: "linechart"; title: "No history to draw yet"
                                text: page.got ? "Nothing reported over this range yet." : "Readings are kept by the Engine; this one does not hand them to the console." }
                    }
                }
            }
            Panel {
                visible: page.tab === "proc"
                width: parent.width
                flush: true
                title: "Running now"
                id: procP
                readonly property var procs: page.got && page.got.processes && page.got.processes.items ? page.got.processes.items : null
                sub: procs ? Theme.many(procs.length, "process") + (page.got.processes.at ? " · reported " + Time.ago(page.got.processes.at) : "") : page.running.length ? Theme.many(page.running.length, "program") : ""
                Column {
                    width: parent.width
                    Empty { visible: (procP.procs || page.running).length === 0; width: parent.width; icon: "appstore"; title: "Nothing reported yet"; text: "A machine reports what runs on it when it checks in." }
                    Repeater {
                        model: procP.procs ? procP.procs.slice().sort(function (a, b) { return (b.cpu || 0) - (a.cpu || 0) }).slice(0, 20) : page.running.slice(0, 20)
                        Rectangle {
                            required property var modelData
                            width: parent.width; height: 34; color: "transparent"
                            Txt { x: 14; width: parent.width * 0.4; anchors.verticalCenter: parent.verticalCenter; text: modelData.name; mono: true }
                            Txt { visible: modelData.cpu !== undefined; x: parent.width * 0.45; anchors.verticalCenter: parent.verticalCenter; text: Math.round(modelData.cpu || 0) + "% CPU"; color: Theme.text2; font.pixelSize: 12 }
                            Txt { visible: modelData.memory_mb !== undefined; x: parent.width * 0.62; anchors.verticalCenter: parent.verticalCenter; text: Theme.fmt(Math.round(modelData.memory_mb || 0)) + " MB"; color: Theme.text2; font.pixelSize: 12 }
                            Txt { visible: !!modelData.user; anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter; text: modelData.user || ""; color: Theme.text3; font.pixelSize: 12 }
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                        }
                    }
                }
            }
            Panel {
                visible: page.tab === "sess"
                width: parent.width
                flush: true
                title: "Sessions today"
                Column {
                    width: parent.width
                    Empty { visible: page.sessions.length === 0; width: parent.width; icon: "login"; title: "Nobody today"; text: "Who was signed in to it, and who entered it, appears here." }
                    Repeater {
                        model: page.sessions
                        Rectangle {
                            required property var modelData
                            width: parent.width; height: 38; color: "transparent"
                            Row {
                                x: 14
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 0
                                Txt { width: 180; text: modelData.occupant_name || "—" }
                                Item {
                                    width: 160; height: 20
                                    Tag {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.occupied_via === "native" ? "Owner signed in" : "Admin session"
                                        c: modelData.occupied_via === "native" ? Theme.text3 : Theme.ser3
                                    }
                                }
                                Txt { width: 90; text: Time.hhmm(modelData.entered_at); mono: true }
                                Txt { width: 90; text: modelData.ended_at ? Time.hhmm(modelData.ended_at) : "—"; mono: true }
                                Txt { width: 90; mono: true; text: Time.dur(((modelData.ended_at ? Time.ms(modelData.ended_at) : Time.now) - Time.ms(modelData.entered_at)) / 3600000) }
                            }
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                        }
                    }
                }
            }
            Panel {
                id: filesP
                visible: page.tab === "files"
                width: parent.width
                title: "Restricted files on it"
                readonly property var copies: page.m ? page.m.issues.filter(function (i) { return i.type === "file" }) : []
                Column {
                    width: parent.width
                    spacing: 6
                    Txt { visible: filesP.copies.length === 0; text: "No copy of a restricted file is on " + (page.m ? page.m.host : "it") + "."; color: Theme.text3 }
                    Repeater {
                        model: filesP.copies
                        St { required property var modelData; text: modelData.subject; c: Fleet.sevColor(modelData.sev) }
                    }
                    Link {
                        visible: filesP.copies.length > 0
                        text: (filesP.copies.length === 1 ? "The copy" : "The " + filesP.copies.length + " copies") + " of restricted files on " + (page.m ? page.m.host : "") + " →"
                        onClicked: { Nav.preset = { page: "issues", type: "file", host: page.m.host }; Nav.go("issues") }
                    }
                }
            }
        }
        Panel {
            width: (parent.width - 14) * 4 / 12
            flush: true
            title: "Events on this machine"
            Column {
                width: parent.width
                Txt { visible: page.events.length === 0; x: 14; topPadding: 14; bottomPadding: 14; text: "No events in the record."; color: Theme.text3 }
                Repeater {
                    model: page.events
                    Rectangle {
                        required property var modelData
                        width: parent.width; height: 30; color: "transparent"
                        Txt { x: 14; width: 54; anchors.verticalCenter: parent.verticalCenter; mono: true; color: Theme.text3; font.pixelSize: 12
                              text: Time.sameDay(modelData.t, Time.now) ? Time.hhmm(modelData.t) : Time.dayName(modelData.t) }
                        Rectangle { x: 72; width: 7; height: 7; radius: 2; color: Kinds.color(modelData.kind); anchors.verticalCenter: parent.verticalCenter }
                        Txt { x: 88; width: parent.width - 102; anchors.verticalCenter: parent.verticalCenter; textFormat: Text.RichText
                              text: "<span style='font-weight:500'>" + modelData.actor + "</span> <span style='color:" + Theme.text2 + "'>" + modelData.what + "</span>" }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
            }
        }
    }
}
