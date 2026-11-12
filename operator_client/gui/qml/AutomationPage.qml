import QtQuick
import "."

// AUTOMATION. What runs on its own here: four figures, the rules (switch one off in the list), the rule
// picked beside it with its last firings -- each opens to what every action returned -- and the runs of
// every rule over the week under both. A rule set for the whole organisation is seen here, not changed or switched.
Page {
    id: page
    objectName: "automationView"

    property var events: []
    property var hist: ({})           // event id -> event_history
    property var board: ({})          // event id -> automation.board's row: who set it, by name
    property string pf: ""
    property var sel: { var a = Nav.takeArrive("automation"); return a !== null ? Number(a) : Nav.sub && !isNaN(Number(Nav.sub)) ? Number(Nav.sub) : null }
    property int openF: -1
    property int openRun: 0

    function load() {
        falcon.call("automation.board", {}, function (ok, r) { var b = {}; if (ok) (r.rules || []).forEach(function (x) { b[x.event_id] = x }); page.board = b; page.coming = ok ? r.coming_up || [] : [] })
        falcon.call("control.event_list", {}, function (ok, r) {
            page.events = ok ? (r.events || []) : []
            page.events.forEach(function (e) {
                falcon.call("control.event_history", { event_id: e.id }, function (ok2, r2) {
                    if (!ok2) return
                    var h = Object.assign({}, page.hist); h[e.id] = r2; page.hist = h
                })
            })
        })
    }
    Component.onCompleted: load()
    Connections { target: falcon; function onPushReceived(type) { if (/^(event|action)/.test(type)) again.restart() } }
    Timer { id: again; interval: 500; onTriggered: page.load() }

    readonly property real weekAgo: Time.now - 7 * 86400000
    function firings(e) { var h = hist[e.id]; return h ? (h.firings || []).filter(function (f) { return Time.ms(f.at) >= page.weekAgo }) : [] }
    function runs(e) { return firings(e).reduce(function (a, f) { return a.concat(f.runs || []) }, []) }
    function hasProb(e) { return runs(e).some(function (x) { return Auto.problem(Auto.outcome(x)) }) }
    readonly property var allRuns: events.reduce(function (a, e) { return a.concat(page.runs(e)) }, [])
    readonly property int fired: events.reduce(function (a, e) { return a + page.firings(e).length }, 0)
    readonly property int probs: allRuns.filter(function (x) { return Auto.problem(Auto.outcome(x)) }).length
    readonly property var rows: events.map(function (e) { return Object.assign({ name: Auto.nameOf(e), kindW: Auto.kind((e.condition_spec || {}).type) }, e) })

    // opens on the rule that ran last, with that run picked
    readonly property var curId: sel !== null ? sel : todayRuns.length ? todayRuns[0].e.id : rows.length ? rows[0].id : null
    readonly property var cur: { for (var i = 0; i < rows.length; i++) if (rows[i].id === curId) return rows[i]; return rows.length ? rows[0] : null }
    property var pickT: null              // the run picked below, by when it fired; null when a rule was picked from the list
    readonly property var pickAt: sel === null && todayRuns.length ? todayRuns[0].f.at : pickT
    function pick(id, at) { sel = id; pickT = at === undefined ? null : at }
    // the run picked among today's, for the panel beside them: what each action did on each machine
    readonly property var curRun: { for (var i = 0; i < todayRuns.length; i++) if (cur && todayRuns[i].e.id === cur.id && todayRuns[i].f.at === pickAt) return todayRuns[i]
                                    return null }
    readonly property int maxFired: Math.max(1, Math.max.apply(null, events.map(function (e) { return page.firings(e).length }).concat([0])))
    // runs per day, by outcome, oldest first
    readonly property var perDay: ["Success", "Failed", "Timed out", "Stopped by you"].map(function (k) {
        var v = [0, 0, 0, 0, 0, 0, 0]
        page.allRuns.forEach(function (x) {
            if (Auto.outcome(x) !== k) return
            var d = Math.floor((Time.startOfDay(Time.now) - Time.startOfDay(Time.ms(x.started_at))) / 86400000)
            if (d >= 0 && d < 7) v[6 - d] += 1
        })
        return { name: k, c: Auto.outColor(k), v: v }
    })

    function setBy(e) { var b = board[e.id]; return b && (b.set_by || b.owner) ? b.set_by || b.owner : "an Admin" }
    function mine(e) { return e.created_by_account_id === falcon.accountId }
    function byWord(e) { return mine(e) ? "you" : setBy(e) }
    // Test on one machine: the rule's actions once, on the first machine it applies to that is online (recorded as run by hand)
    function test(e) {
        var ids = (e.condition_spec || {}).pc_ids, ms = Fleet.machines.filter(function (m) { return m.online && (!ids || !ids.length || ids.indexOf(m.pc_id) >= 0) })
        if (!ms.length) { Msg.warn("No machine it applies to is online"); return }
        falcon.call("control.event_test", { event_id: e.id, pc_id: ms[0].pc_id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not run"); return }
            Msg.ok("Ran once on " + ms[0].host + " · recorded as run by hand"); again.restart()
        })
    }
    function toggle(e, on) {
        falcon.call("control.event_update", { event_id: e.id, enabled: on }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not changed"); return }
            Msg.ok(Auto.nameOf(e) + (on ? " switched on" : " switched off")); page.load()
        })
    }

    // --- the version 1 concept's layout (docs/design/concepts-admin.html, AdminAutomationPage) ----------------------------------------------
    property string expRun: ""
    property bool loading: false
    property var pickedId: null
    onCurChanged: { pickedId = cur ? cur.id : null; loading = true; ldT.restart() }
    Timer { id: ldT; interval: Theme.loadMs; onTriggered: page.loading = false }
    function actionName(e, id) { var a = (e.actions || []).filter(function (x) { return x.id === id || x.action_id === id })[0]; return a ? a.name : "action " + id }
    function firingsToday(e) { return firings(e).filter(function (f) { return !f.by_hand && Time.sameDay(Time.ms(f.at), Time.now) }) }
    function badOf(f) { return (f.runs || []).filter(function (x) { return Auto.problem(Auto.outcome(x)) }) }
    function hostOf(x) { return x.host || (Fleet.byPc[x.target_pc_id] || { host: "" }).host }
    // what a run came to, in a line: what it did, or what went wrong
    function effect(e, f) {
        var rs = f.runs || [], bad = badOf(f)
        if (!bad.length) return rs.map(function (x) { return Auto.pastOf(page.actionName(e, x.action_id)) }).filter(function (w, i, a) { return a.indexOf(w) === i }).join(", ")
        var many = rs.length > (e.actions || []).length
        return bad.map(function (x) {
            var n = page.actionName(e, x.action_id), out = Auto.outcome(x) === "Timed out"
            return many ? n + " on " + page.hostOf(x) + " " + (out ? "ran out of time at " + Auto.secs(x) + "s" : "failed") : n + " " + (out ? "ran out of time at " + Auto.secs(x) + "s" : "failed, exit " + x.exit_code)
        }).join("; ")
    }
    // why it ran
    function cause(e, f) {
        var host = f.machines > 1 ? Theme.many(f.machines, "machine") : f.hostname || ""
        if (Auto.kind((e.condition_spec || {}).type) === "Schedule") return "It was " + Time.hhmm(f.at) + ", so it ran on " + host
        var m = Fleet.byHost[f.hostname]
        return (f.detail || f.subject || Auto.whenOf(e)) + " on " + host + (m && m.user ? ", " + m.user + " signed in" : "")
    }
    property var again: ({})              // runs sent again where they went wrong, by key
    function runAgain(r) {
        var k = r.key
        falcon.call("automation.run_again", { event_id: r.e.id, at: r.f.at }, function (ok, res) {
            if (!ok) { Msg.failed(res && res.message ? res.message : "Not done"); return }
            var a = Object.assign({}, page.again); a[k] = true; page.again = a
            var bad = page.badOf(r.f)
            Msg.ok(bad.map(function (x) { return page.actionName(r.e, x.action_id) }).filter(function (w, i, l) { return l.indexOf(w) === i }).join(", ") + " runs again on "
                   + Theme.listNames(bad.map(page.hostOf).filter(function (w, i, l) { return l.indexOf(w) === i }), 3))
        })
    }
    function badN(e) { return firingsToday(e).filter(function (f) { return page.badOf(f).length > 0 && !page.again[e.id + ":" + f.at] }).length }
    readonly property var todayRuns: {
        var out = []
        events.forEach(function (e) { if (e.enabled !== false) page.firingsToday(e).forEach(function (f) { var k = e.id + ":" + f.at; out.push({ key: k, e: e, f: f, bad: page.badOf(f).length > 0 && !page.again[k], done: !!page.again[k] }) }) })
        return out.sort(function (a, b) { return Time.ms(b.f.at) - Time.ms(a.f.at) })
    }
    // runs a day this week for the picked rule: by the rule, run by hand, went wrong
    readonly property var week: {
        var v = [], e = cur
        for (var d = 6; d >= 0; d--) v.push({ day: d, rule: 0, hand: 0, bad: 0 })
        if (!e) return v
        page.firings(e).forEach(function (f) {
            var d = Math.floor((Time.startOfDay(Time.now) - Time.startOfDay(Time.ms(f.at))) / 86400000)
            if (d < 0 || d > 6) return
            if (f.by_hand) v[6 - d].hand += 1; else if (page.badOf(f).length) v[6 - d].bad += 1; else v[6 - d].rule += 1
        })
        return v
    }
    situation: {
        if (!events.length) return "You have no rules yet. Make one below; it runs on its own from then on."
        var ranToday = events.filter(function (e) { return page.firingsToday(e).length > 0 }).length, times = todayRuns.length
        var bad = todayRuns.filter(function (r) { return r.bad }), hosts = bad.reduce(function (a, r) { return a.concat(page.badOf(r.f).map(page.hostOf)) }, []).filter(function (h, i, a) { return a.indexOf(h) === i })
        var off = events.filter(function (e) { return e.enabled === false }).map(function (e) { return Auto.nameOf(e) }), nx = coming.filter(function (c) { return (page.events.filter(function (e) { return e.id === c.event_id })[0] || {}).enabled !== false })[0]
        return Theme.fmt(ranToday) + " of the " + Theme.many(events.length, "rule") + " ran today, " + Theme.many(times, "time") + " in all."
               + (bad.length ? " " + Theme.many(bad.length, "run") + " did not go to plan, on " + Theme.listNames(hosts) + "." : " Everything they did worked.")
               + (off.length ? " " + Theme.listNames(off) + " is switched off." : "")
               + (nx ? " Next: " + nx.name + " " + page.dayWord(nx.at) + " at " + Time.hhmm(nx.at) + "." : "")
    }
    situationAt: Time.now

    // the next scheduled runs (automation.board's coming_up), in order
    property var coming: []
    property var skipped: ({})            // runs skipped this once, by rule and time
    function dayWord(x) {
        var d = Math.round((Time.startOfDay(Time.ms(x)) - Time.startOfDay(Time.now)) / 86400000)
        return d === 0 ? "today" : d === 1 ? "tomorrow" : Time.dayName(x)
    }
    function skip(c, on) {
        falcon.call("automation.skip", { event_id: c.event_id, at: c.at, undo: !on }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not done"); return }
            var s = Object.assign({}, page.skipped); s[c.event_id + ":" + c.at] = on; page.skipped = s
            if (on) Msg.ok(c.name + " will skip " + page.dayWord(c.at) + " " + Time.hhmm(c.at))
        })
    }
    property int rpg: 0
    readonly property var runOrder: todayRuns.filter(function (r) { return r.bad }).map(function (r) { return ["bad", r] }).concat(todayRuns.filter(function (r) { return !r.bad }).map(function (r) { return ["ok", r] }))
    readonly property int rper: Math.max(2, Math.round(5 * Theme.viewScale))        // five runs on the design's 900-high window; follows the screen
    readonly property int rpages: Math.max(1, Math.ceil(runOrder.length / rper))
    readonly property int rpi: Math.min(rpg, rpages - 1)
    readonly property var runPage: runOrder.slice(rpi * rper, rpi * rper + rper)

    // --- your rules, and the picked one (auo-sheet: 4 to 8, the two as tall as each other) ---------------------------------------
    Row {
        width: parent.width
        spacing: 16
        readonly property real h: rulesP.implicitHeight
        Box {
            id: rulesP
            objectName: "ruleList"
            width: (parent.width - 16) * 4 / 12
            height: implicitHeight  // its own height: a neighbour's growth never drags it (the user, 12 Nov 2026)
            title: "The rules"
            sub: String(page.events.length)
            extra: Btn { small: true; headed: true; iconName: "plus"; text: "Make a rule"; onClicked: Nav.go("automation", "new") }
            PagedList {   // a long list pages in place (the user, 11 Nov 2026)
                id: rp; items: page.rows.filter(function (r) { return page.badN(r) > 0 }).concat(page.rows.filter(function (r) { return page.badN(r) === 0 })); per: 8
                delegate: Rectangle {
                    required property var modelData
                    readonly property int n: page.badN(modelData)
                    width: parent.width
                    height: 55.75
                    radius: Theme.radius
                    color: page.cur && page.cur.id === modelData.id ? Theme.surface3 : ra.containsMouse ? Theme.surface2 : "transparent"
                    Icon { x: 10; y: 9 + 4; name: Auto.kindIcon(modelData.kindW); size: 13; color: Theme.text3 }
                    Column { id: lc; x: 31; y: 9; width: parent.width - 31 - 10 - (parent.n > 0 ? 26 : 0); spacing: 1
                        Txt { width: parent.width; text: modelData.name; font.weight: Font.DemiBold; color: modelData.enabled === false ? Theme.text4 : Theme.text }
                        Txt { width: parent.width; text: "Set " + Time.day(modelData.created_at) + " by " + page.byWord(modelData); color: Theme.text3; font.pixelSize: 12 } }
                    Rectangle { visible: parent.n > 0; anchors.right: parent.right; anchors.rightMargin: 10; y: 9 + 1; width: Math.max(18, nb.implicitWidth + 8); height: 18; radius: 9; color: Theme.crit
                                Txt { id: nb; anchors.centerIn: parent; text: parent.parent.n; color: Theme.inverse; font.pixelSize: 11; elide: Text.ElideNone } }
                    MouseArea { id: ra; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.pick(modelData.id) }
                }
            }
            Quiet { visible: page.events.length === 0; text: "No rules yet. Make one: when something happens, on which machines, do what." }
        }
        // --- the picked rule, as a sentence -------------------------------------------------------------------------------------------
        Box {
            id: sheet
            objectName: "ruleSheet"
            width: (parent.width - 16) * 8 / 12
            height: implicitHeight  // its own height: a neighbour's growth never drags it (the user, 12 Nov 2026)
            gap: 14
            title: page.cur ? page.cur.name : "No rule picked"
            sub: page.cur ? "set by " + page.byWord(page.cur) + " · " + (page.cur.enabled === false ? "switched off" : "on since " + Time.day(page.cur.created_at)) : "pick a rule on the left"
            extra: Row {
                spacing: 8
                visible: page.cur !== null
                Btn { visible: page.cur !== null; small: true; headed: true; text: "Run now"; enabled: page.cur !== null && page.cur.enabled !== false; onClicked: page.test(page.cur) }
                Btn { visible: page.cur !== null; small: true; headed: true; iconName: "edit"; text: "Edit"; onClicked: Nav.go("automation", "edit-" + page.cur.id) }
            }
            Txt {
                id: big
                visible: page.cur !== null
                width: parent.width
                wrapMode: Text.WordWrap; elide: Text.ElideNone
                textFormat: Text.StyledText
                font.pixelSize: 17
                font.weight: Font.Medium
                lh: 1.45
                color: page.cur && page.cur.enabled === false ? Theme.text4 : Theme.text
                text: page.cur ? "<font color='" + Theme.text3 + "'>When</font> " + Auto.whenOf(page.cur) + " <font color='" + Theme.text3 + "'>on</font> " + Auto.whereOf(page.cur)
                                 + "<font color='" + Theme.text3 + "'>, do</font> " + (page.cur.actions || []).map(function (a) { return a.name }).join(", ") : ""
            }
            Row {
                id: two
                visible: page.cur !== null
                width: parent.width
                // auo-two fills what the list leaves; the chart never goes under its 220
                height: 220 + 36
                spacing: 56
                opacity: page.loading ? 0 : 1
                // this week, runs a day, on a fixed scale of ten (aub-chart)
                Column {
                    id: wk
                    width: (parent.width - 56) / 2.3
                    height: parent.height
                    spacing: 4
                    Txt { topPadding: 4; text: "This week · runs a day"; color: Theme.text3; font.pixelSize: 12 }
                    Item {
                        id: plot
                        width: parent.width
                        height: wk.height - 26 - 6 - 34.5
                        readonly property real pt: 14
                        readonly property real foot: 16
                        readonly property real ph: height - pt - foot
                        Repeater {
                            model: [0, 5, 10]
                            delegate: Item {
                                required property var modelData
                                y: plot.pt + plot.ph * (1 - modelData / 10)
                                width: plot.width
                                Rectangle { x: 22; width: parent.width - 22; height: 1; color: Theme.grid }
                                Txt { x: 0; width: 16; horizontalAlignment: Text.AlignRight; y: -8; text: modelData; mono: true; font.pixelSize: 11; color: Theme.text4; elide: Text.ElideNone }
                            }
                        }
                        Row {
                            x: 26
                            width: plot.width - 26
                            height: plot.height
                            spacing: 10
                            Repeater {
                                model: page.week
                                delegate: Item {
                                    required property var modelData
                                    width: (plot.width - 26 - 60) / 7
                                    height: plot.height
                                    readonly property int tot: modelData.rule + modelData.hand + modelData.bad
                                    readonly property real k: Math.min(1, 10 / Math.max(1, tot))
                                    function hh(v) { return v / 10 * plot.ph * k }
                                    Column {
                                        anchors.bottom: parent.bottom; anchors.bottomMargin: plot.foot
                                        width: parent.width
                                        spacing: 2
                                        Txt { visible: parent.parent.tot > 0; width: parent.width; horizontalAlignment: Text.AlignHCenter; text: parent.parent.tot; font.pixelSize: parent.parent.tot > 10 ? 12 : 11
                                              font.weight: Font.Bold; color: parent.parent.tot > 10 ? Theme.text : Theme.text2; elide: Text.ElideNone }
                                        Rectangle { visible: modelData.hand > 0; width: parent.width; height: parent.parent.hh(modelData.hand); radius: 3; color: Theme.alpha(Theme.ser6, 0.35) }
                                        Rectangle { visible: modelData.bad > 0; width: parent.width; height: parent.parent.hh(modelData.bad); radius: 3; color: Theme.alpha(Theme.crit, 0.8) }
                                        Rectangle { visible: modelData.rule > 0; width: parent.width; height: parent.parent.hh(modelData.rule); radius: 3; color: Theme.alpha(Theme.ser6, 0.8) }
                                    }
                                    Txt { anchors.bottom: parent.bottom; width: parent.width; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 11; color: Theme.text3; elide: Text.ElideNone
                                          text: modelData.day === 0 ? "Today" : Time.dayName(Time.now - modelData.day * 86400000) }
                                }
                            }
                        }
                    }
                    Column {
                        width: parent.width - 26
                        x: 26
                        topPadding: 2
                        spacing: 4
                        Row {
                            spacing: 14
                            Repeater { model: [["by the rule", Theme.alpha(Theme.ser6, 0.8)], ["run by hand", Theme.alpha(Theme.ser6, 0.35)], ["went wrong", Theme.crit]]
                                delegate: Row { required property var modelData; spacing: 5
                                    Rectangle { width: 10; height: 10; radius: 2; color: modelData[1]; anchors.verticalCenter: parent.verticalCenter }
                                    Txt { text: modelData[0]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } } }
                        }
                        Txt { width: parent.width; text: "over 10 stops at the top; the number is the count"; color: Theme.text4; font.pixelSize: 12 }
                    }
                }
                // its actions (auo-act)
                Column {
                    width: (parent.width - 56) * 1.3 / 2.3
                    Txt { topPadding: 4; bottomPadding: 0; text: "Its actions"; color: Theme.text3; font.pixelSize: 12 }
                    Repeater {
                        model: page.cur ? page.cur.actions || [] : []
                        delegate: Item {
                            required property var modelData
                            required property int index
                            width: parent.width
                            height: ac.height + 16
                            readonly property var xs: page.cur ? page.runs(page.cur).filter(function (x) { return x.action_id === modelData.id || x.action_id === modelData.action_id }) : []
                            readonly property var oks: xs.filter(function (x) { return Auto.outcome(x) === "Success" && Auto.secs(x) })
                            Column { id: ac; y: 8; width: parent.width - 100; spacing: 1
                                Txt { width: parent.width; text: (index + 1) + ". " + modelData.name; font.weight: Font.DemiBold }
                                Txt { width: parent.width; text: modelData.description || "a step of this rule"; color: Theme.text3; font.pixelSize: 12 } }
                            Txt { anchors.right: parent.right; width: 90; anchors.verticalCenter: parent.verticalCenter; anchors.verticalCenterOffset: -4; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone
                                  text: parent.oks.length ? Math.round(parent.oks.reduce(function (n, x) { return n + Auto.secs(x) }, 0) / parent.oks.length) + "s of " + (modelData.timeout_seconds || "—") + "s"
                                        : "limit " + (modelData.timeout_seconds || "—") + "s" }
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                        }
                    }
                }
            }
            Loading { parent: sheet; on: page.loading && page.cur !== null; under: sheet.headerHeight + 60 }
            Pulse { parent: sheet; key: page.pickedId }
        }
    }

    // --- recent runs today -----------------------------------------------------------------------------------------------------------
    Row {
        width: parent.width
        spacing: 16
        Box {
            id: runsBox
            objectName: "runsToday"
            width: (parent.width - 16) * 8 / 12
            height: implicitHeight  // its own height: a neighbour's growth never drags it (the user, 12 Nov 2026)
            title: "Recent runs today"
            sub: page.todayRuns.length ? "newest first; click one to see its rule above, its machines are on the right" : "nothing has run yet today"
            Repeater {
                model: [["bad", "Failed", "an action failed or ran out of time"], ["ok", "Successful", "everything it did worked"]]
                delegate: Group {
                    id: rg
                    required property var modelData
                    required property int index
                    readonly property var xs: page.runPage.filter(function (e) { return e[0] === modelData[0] }).map(function (e) { return e[1] })
                    visible: xs.length > 0
                    spaced: index > 0 && page.runPage.some(function (e) { return e[0] === "bad" })
                    cardGap: 5
                    width: parent.width
                    title: modelData[1] + " · " + page.todayRuns.filter(function (r) { return rg.modelData[0] === "bad" ? r.bad : !r.bad }).length
                    sub: modelData[2]
                    Repeater {
                        model: rg.xs
                        delegate: Card {
                            id: rc
                            required property var modelData
                            width: rg.cardW
                            midW: 260
                            padV: 7
                            icon: Auto.kindIcon(Auto.kind((modelData.e.condition_spec || {}).type))
                            hot: modelData.bad
                            title: page.rows.filter(function (r) { return r.id === modelData.e.id }).map(function (r) { return r.name })[0] || Auto.nameOf(modelData.e)
                            line: modelData.done ? "running again now" : page.effect(modelData.e, modelData.f)
                            lineHot: modelData.bad
                            picked: page.cur !== null && page.cur.id === modelData.e.id && page.pickAt === modelData.f.at
                            expandable: true
                            expanded: page.expRun === modelData.key
                            onOpen: page.pick(modelData.e.id, modelData.f.at)
                            onToggle: { page.pick(modelData.e.id, modelData.f.at); page.expRun = expanded ? "" : modelData.key }
                            mid: Row {
                                anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right
                                spacing: 18
                                Txt { text: rc.modelData.f.machines > 1 ? Theme.many(rc.modelData.f.machines, "machine") : rc.modelData.f.hostname || ""; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                                Txt { text: Time.hhmm(rc.modelData.f.at); mono: true; color: Theme.text3; elide: Text.ElideNone }
                            }
                            // opened: why it ran, then what each action did on each machine
                            Column {
                                width: parent.width
                                spacing: 8
                                Column {
                                    width: parent.width
                                    bottomPadding: 10
                                    Txt { width: parent.width; text: page.cause(rc.modelData.e, rc.modelData.f); color: Theme.text3; font.pixelSize: 13 }
                                    Rectangle { width: parent.width; height: 1; color: Theme.border; y: parent.height - 1 }
                                }
                                Column {
                                    visible: rc.modelData.bad
                                    width: parent.width
                                    spacing: 12
                                    topPadding: 4
                                    Btn { anchors.right: parent.right; small: true; kind: "primary"; text: "Run again where it went wrong"; onClicked: page.runAgain(rc.modelData) }
                                }
                            }
                        }
                    }
                }
            }
            StepPager {
                visible: page.rpages > 1
                width: parent.width
                noun: "runs"
                from: page.rpi * page.rper + 1
                to: Math.min(page.runOrder.length, page.rpi * page.rper + page.rper)
                total: page.runOrder.length
                pageNo: page.rpi
                pages: page.rpages
                onStep: function (d) { page.rpg = page.rpi + d }
            }
            Quiet { visible: page.todayRuns.length === 0; text: "No rule has run yet today." }
        }
        Box {
            id: runP
            objectName: "runMachines"
            width: (parent.width - 16) * 4 / 12
            height: implicitHeight  // its own height: a neighbour's growth never drags it (the user, 12 Nov 2026)
            title: page.curRun ? "The run at " + Time.hhmm(page.curRun.f.at) : "No run picked"
            sub: page.curRun ? (page.curRun.f.machines > 1 ? Theme.many(page.curRun.f.machines, "machine") : page.curRun.f.hostname || "") + "; what each action did" : "pick a run on the left"
            // (the user, 12 Nov 2026: an opened card holds fixed details; a list that can grow is on the right, paged)
            PagedList {
                objectName: "runMachineList"
                per: 5
                spacing: 8
                items: page.curRun ? (function () { var by = {}, out = []; (page.curRun.f.runs || []).forEach(function (x) { var h = page.hostOf(x); if (!by[h]) { by[h] = []; out.push(h) } by[h].push(x) }); var hasBad = function (h) { return by[h].some(function (x) { return Auto.problem(Auto.outcome(x)) }) }; return out.filter(hasBad).concat(out.filter(function (h) { return !hasBad(h) })).map(function (h) { return [h, by[h]] }) })() : []
                delegate: Item {
                    required property var modelData
                    width: parent.width
                    height: fx.height
                    Txt { y: 3; width: 70; text: modelData[0]; mono: true; font.pixelSize: 12; color: Theme.text2; elide: Text.ElideRight }
                    Column {
                        id: fx
                        x: 80; width: parent.width - 80
                        spacing: 3
                        Repeater {
                            model: modelData[1]
                            delegate: Rectangle {
                                required property var modelData
                                readonly property string o: Auto.outcome(modelData)
                                width: parent.width; height: xn.height + 8; radius: 5
                                color: o === "Timed out" ? Theme.mix(Theme.med, Theme.surface2, 0.16) : Auto.problem(o) ? Theme.mix(Theme.crit, Theme.surface2, 0.16) : Theme.surface2
                                Txt { id: xn; x: 8; y: 3; width: parent.width - 16 - xo.implicitWidth - 8; text: page.actionName(page.curRun.e, modelData.action_id); font.pixelSize: 12 }
                                Txt { id: xo; anchors.right: parent.right; anchors.rightMargin: 8; y: 3; font.pixelSize: 12; elide: Text.ElideNone
                                      color: parent.o === "Timed out" ? Theme.med : Auto.problem(parent.o) ? Theme.crit : Theme.text3
                                      text: parent.o === "Success" ? Auto.secs(modelData) + "s" : parent.o === "Timed out" ? "ran out of time at " + Auto.secs(modelData) + "s"
                                            : parent.o === "Failed" ? "failed, exit " + modelData.exit_code : parent.o.toLowerCase() }
                            }
                        }
                    }
                }
            }
            Quiet { visible: page.curRun === null; text: "Pick a run on the left to see each machine." }
        }
    }

    // --- coming up --------------------------------------------------------------------------------------------------------------------
    Box {
        width: parent.width
        title: "Coming up"
        sub: "the next scheduled runs, in order; a rule that starts on an event runs whenever it happens, so it is not listed"
        Column {
            width: parent.width
            PagedList {   // a long list pages in place (the user, 11 Nov 2026)
                id: cop; items: page.coming; per: 6
                delegate: Item {
                    id: nx
                    required property var modelData
                    required property int index
                    readonly property var ev: page.events.filter(function (e) { return e.id === modelData.event_id })[0] || null
                    readonly property bool isOff: ev !== null && ev.enabled === false
                    readonly property bool skipped: !!page.skipped[modelData.event_id + ":" + modelData.at]
                    readonly property bool quiet: isOff || skipped
                    width: parent.width
                    height: Math.max(nt.height, nn.height) + 16
                    Column { id: nt; y: 8; width: 110; spacing: 1
                        Txt { text: Time.hhmm(modelData.at); mono: true; font.weight: Font.DemiBold; elide: Text.ElideNone; color: nx.quiet ? Theme.text4 : Theme.text }
                        Txt { text: page.dayWord(modelData.at); color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
                    Column { id: nn; x: 124; y: 8; width: parent.width - 124 - 14 - sk.width; spacing: 1
                        Txt { width: parent.width; text: modelData.name; font.weight: Font.DemiBold; color: nx.quiet ? Theme.text4 : Theme.text }
                        Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12
                              text: nx.ev ? (nx.ev.actions || []).map(function (a) { return a.name }).join(", ") + " on " + Theme.many(Auto.machinesOf(nx.ev), "machine") : "" } }
                    MouseArea { x: nn.x; y: nn.y; width: nn.width; height: nn.height; cursorShape: Qt.PointingHandCursor; onClicked: page.pick(modelData.event_id) }
                    Row {
                        id: sk
                        anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                        spacing: 6
                        Txt { visible: nx.isOff || nx.skipped; anchors.verticalCenter: parent.verticalCenter; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone
                              text: nx.isOff ? "switched off; it will not run" : "skipped this once" }
                        Btn { visible: !nx.isOff && nx.skipped; small: true; kind: "text"; text: "Undo"; onClicked: page.skip(nx.modelData, false) }
                        Btn { visible: !nx.quiet && nx.ev !== null; small: true; text: "Skip this once"; onClicked: page.skip(nx.modelData, true) }
                    }
                    Rectangle { visible: index < cop.shown.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                }
            }
            Quiet { visible: page.coming.length === 0; text: "No rule is set to run at a time." }
        }
    }

    // --- make a rule ------------------------------------------------------------------------------------------------------------------
    Box {
        width: parent.width
        accentFoot: true
        title: "Make a rule"
        sub: "nothing runs until you switch it on at the end"
        GiveSteps {
            steps: [["Say when it starts", "when something happens, when a reading crosses a line, or at a time"], ["Pick the machines", "every machine, or the ones you name"], ["Say what it does", "one or more actions, in order, each with a time limit"]]
            act: "Make a rule"
            onGo: Nav.go("automation", "new")
        }
    }
}
