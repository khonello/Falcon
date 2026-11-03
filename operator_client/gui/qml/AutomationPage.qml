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
        falcon.call("calendar.board", { days: 7 }, function (ok, r) {
            page.coming = ok ? (r.items || []).filter(function (x) { return x.kind === "rule" && Time.ms(x.at) >= Time.now }).sort(function (a, b) { return Time.ms(a.at) - Time.ms(b.at) }).slice(0, 5) : [] })
        falcon.call("automation.board", {}, function (ok, r) { var b = {}; if (ok) (r.rules || []).forEach(function (x) { b[x.event_id] = x }); page.board = b })
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

    readonly property var cur: { for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; return rows.length ? rows[0] : null }
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

    function ownerOf(e) { var b = board[e.id]; return b && b.owner ? b.owner : e.read_only ? "the organisation" : "an Admin" }
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
    onCurChanged: { loading = true; ldT.restart() }
    Timer { id: ldT; interval: Theme.loadMs; onTriggered: { page.loading = false; page.pickedId = page.cur ? page.cur.id : null } }
    function actionName(e, id) { var a = (e.actions || []).filter(function (x) { return x.id === id || x.action_id === id })[0]; return a ? a.name : "action " + id }
    function firingsToday(e) { return firings(e).filter(function (f) { return Time.sameDay(Time.ms(f.at), Time.now) }) }
    readonly property var todayRuns: {
        var out = []
        events.forEach(function (e) { page.firingsToday(e).forEach(function (f, i) { out.push({ key: e.id + ":" + i, e: e, f: f, bad: (f.runs || []).some(function (x) { return Auto.problem(Auto.outcome(x)) }) }) }) })
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
            var bad = (f.runs || []).some(function (x) { return Auto.problem(Auto.outcome(x)) })
            if (bad) v[6 - d].bad += 1; else if (f.by_hand) v[6 - d].hand += 1; else v[6 - d].rule += 1
        })
        return v
    }
    situation: {
        if (!events.length) return "You have no rules yet. Make one below; it runs on its own from then on."
        var ranToday = events.filter(function (e) { return page.firingsToday(e).length > 0 }).length, times = todayRuns.length
        var bad = todayRuns.filter(function (r) { return r.bad }), hosts = bad.map(function (r) { return r.f.hostname || "several machines" }).filter(function (h, i, a) { return a.indexOf(h) === i })
        return Theme.fmt(ranToday) + " of your " + Theme.many(events.length, "rule") + " ran today, " + Theme.many(times, "time") + " in all."
               + (bad.length ? " " + Theme.many(bad.length, "run") + " did not go to plan, on " + Theme.listNames(hosts, 2) + "." : " Every run went to plan.")
    }
    situationAt: Time.now

    // the next scheduled runs (calendar.board's rules), in order
    property var coming: []
    property int rpg: 0
    readonly property var runOrder: todayRuns.filter(function (r) { return r.bad }).map(function (r) { return ["bad", r] }).concat(todayRuns.filter(function (r) { return !r.bad }).map(function (r) { return ["ok", r] }))
    readonly property int rpages: Math.max(1, Math.ceil(runOrder.length / 5))
    readonly property int rpi: Math.min(rpg, rpages - 1)
    readonly property var runPage: runOrder.slice(rpi * 5, rpi * 5 + 5)

    // --- your rules, and the picked one (auo-sheet: 4 to 8, the two as tall as each other) ---------------------------------------
    Row {
        width: parent.width
        spacing: 16
        readonly property real h: Math.max(rulesP.implicitHeight, sheet.implicitHeight)
        Box {
            id: rulesP
            objectName: "ruleList"
            width: (parent.width - 16) * 4 / 12
            height: parent.h
            gap: 2
            title: "Your rules"
            sub: String(page.events.length)
            extra: Btn { small: true; iconName: "plus"; text: "Make a rule"; onClicked: Nav.go("automation", "new") }
            Repeater {
                model: page.rows.slice().sort(function (a, b) { return page.hasProb(b) - page.hasProb(a) })
                delegate: Rectangle {
                    required property var modelData
                    readonly property int n: page.firingsToday(modelData).filter(function (f) { return (f.runs || []).some(function (x) { return Auto.problem(Auto.outcome(x)) }) }).length
                    width: parent.width
                    height: lc.height + 18
                    radius: Theme.radius
                    color: page.cur && page.cur.id === modelData.id ? Theme.surface3 : ra.containsMouse ? Theme.surface2 : "transparent"
                    Icon { x: 10; y: 9 + 4; name: Auto.kindIcon(modelData.kindW); size: 13; color: Theme.text3 }
                    Column { id: lc; x: 31; y: 9; width: parent.width - 31 - 10 - (parent.n > 0 ? 26 : 0); spacing: 1
                        Txt { width: parent.width; text: modelData.name; font.weight: Font.DemiBold; color: modelData.enabled === false ? Theme.text4 : Theme.text }
                        Txt { width: parent.width; text: (modelData.enabled === false ? "switched off · " : "") + "Made by " + page.ownerOf(modelData); color: Theme.text3; font.pixelSize: 12 } }
                    Rectangle { visible: parent.n > 0; anchors.right: parent.right; anchors.rightMargin: 10; y: 9 + 1; width: Math.max(18, nb.implicitWidth + 8); height: 18; radius: 9; color: Theme.crit
                                Txt { id: nb; anchors.centerIn: parent; text: parent.parent.n; color: Theme.inverse; font.pixelSize: 11; elide: Text.ElideNone } }
                    MouseArea { id: ra; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.sel = modelData.id }
                }
            }
            Quiet { visible: page.events.length === 0; text: "No rules yet. Make one: when something happens, on which machines, do what." }
        }
        // --- the picked rule, as a sentence -------------------------------------------------------------------------------------------
        Box {
            id: sheet
            objectName: "ruleSheet"
            width: (parent.width - 16) * 8 / 12
            height: parent.h
            gap: 14
            title: page.cur ? page.cur.name : "No rule picked"
            sub: page.cur ? "made by " + page.ownerOf(page.cur) + " · " + (page.cur.enabled === false ? "switched off" : "on") : "pick a rule on the left"
            extra: Row {
                spacing: 8
                visible: page.cur !== null
                Btn { small: true; text: "Run now"; enabled: page.cur !== null && !page.cur.read_only && page.cur.enabled !== false; onClicked: page.test(page.cur) }
                Btn { visible: page.cur !== null && !page.cur.read_only; small: true; iconName: "edit"; text: "Edit"; onClicked: Nav.go("automation", "edit-" + page.cur.id) }
                Txt { visible: page.cur !== null && !!page.cur.read_only; text: "only " + (page.cur ? page.ownerOf(page.cur) : "") + " changes it"; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
            }
            Txt {
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
                visible: page.cur !== null
                width: parent.width
                spacing: 56
                opacity: page.loading ? 0 : 1
                // this week, runs a day, on a fixed scale of ten (aub-chart)
                Column {
                    id: wk
                    width: (parent.width - 56) / 2.3
                    spacing: 4
                    Txt { topPadding: 4; text: "This week · runs a day"; color: Theme.text3; font.pixelSize: 12 }
                    Item {
                        id: plot
                        width: parent.width
                        height: 186
                        readonly property real pt: 18
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
                                              font.weight: parent.parent.tot > 10 ? Font.Bold : Font.Normal; color: parent.parent.tot > 10 ? Theme.text : Theme.text2; elide: Text.ElideNone }
                                        Rectangle { visible: modelData.hand > 0; width: parent.width; height: parent.parent.hh(modelData.hand); radius: 3; color: Theme.alpha(Theme.ser6, 0.35) }
                                        Rectangle { visible: modelData.bad > 0; width: parent.width; height: parent.parent.hh(modelData.bad); radius: 3; color: Theme.crit }
                                        Rectangle { visible: modelData.rule > 0; width: parent.width; height: parent.parent.hh(modelData.rule); radius: 3; color: Theme.alpha(Theme.ser6, 0.8) }
                                    }
                                    Txt { anchors.bottom: parent.bottom; width: parent.width; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 11; color: Theme.text3; elide: Text.ElideNone
                                          text: modelData.day === 0 ? "Today" : Time.dayName(Time.now - modelData.day * 86400000) }
                                }
                            }
                        }
                    }
                    Flow {
                        width: parent.width - 26
                        x: 26
                        spacing: 14
                        topPadding: 2
                        Repeater { model: [["by the rule", Theme.alpha(Theme.ser6, 0.8)], ["run by hand", Theme.alpha(Theme.ser6, 0.35)], ["went wrong", Theme.crit]]
                            delegate: Row { required property var modelData; spacing: 5
                                Rectangle { width: 10; height: 10; radius: 2; color: modelData[1]; anchors.verticalCenter: parent.verticalCenter }
                                Txt { text: modelData[0]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } } }
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
                            readonly property var oks: xs.filter(function (x) { return Auto.outcome(x) === "Success" && x.duration_seconds })
                            Column { id: ac; y: 8; width: parent.width - 100; spacing: 1
                                Txt { width: parent.width; text: (index + 1) + ". " + modelData.name; font.weight: Font.DemiBold }
                                Txt { width: parent.width; text: modelData.description || modelData.builtin_type || "a step of this rule"; color: Theme.text3; font.pixelSize: 12 } }
                            Txt { anchors.right: parent.right; width: 90; anchors.verticalCenter: parent.verticalCenter; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone
                                  text: parent.oks.length ? Math.round(parent.oks.reduce(function (n, x) { return n + x.duration_seconds }, 0) / parent.oks.length) + "s of " + (modelData.timeout_seconds || "—") + "s"
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
    Box {
        objectName: "runsToday"
        width: parent.width
        title: "Recent runs today"
        sub: page.todayRuns.length ? "newest first; click one to see its rule above, expand it for each machine" : "nothing has run yet today"
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
                        readonly property var bads: (modelData.f.runs || []).filter(function (x) { return Auto.problem(Auto.outcome(x)) })
                        width: rg.cardW
                        midW: 260
                        padV: 7
                        icon: Auto.kindIcon(Auto.kind((modelData.e.condition_spec || {}).type))
                        hot: modelData.bad
                        title: page.rows.filter(function (r) { return r.id === modelData.e.id }).map(function (r) { return r.name })[0] || Auto.nameOf(modelData.e)
                        line: bads.length ? bads.map(function (x) { return page.actionName(modelData.e, x.action_id) + (Auto.outcome(x) === "Timed out" ? " ran out of time" + (x.duration_seconds ? " at " + x.duration_seconds + "s" : "") : " failed" + (x.exit_code !== undefined && x.exit_code !== null ? ", exit " + x.exit_code : "")) }).join("; ")
                              : Auto.lastRunText(modelData.f.runs || [])
                        lineHot: modelData.bad
                        picked: page.cur !== null && page.cur.id === modelData.e.id
                        expandable: true
                        expanded: page.expRun === modelData.key
                        onOpen: page.sel = modelData.e.id
                        onToggle: { page.sel = modelData.e.id; page.expRun = expanded ? "" : modelData.key }
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
                                Txt { width: parent.width; text: (rc.modelData.f.cause || rc.modelData.f.detail || Auto.whenOf(rc.modelData.e)) + (rc.modelData.f.hostname ? " on " + rc.modelData.f.hostname : ""); color: Theme.text3; font.pixelSize: 13 }
                                Rectangle { width: parent.width; height: 1; color: Theme.border; y: parent.height - 1 }
                            }
                            Repeater {
                                model: { var by = {}, out = []; (rc.modelData.f.runs || []).forEach(function (x) { var h = (Fleet.byPc[x.target_pc_id] || { host: "" }).host; if (!by[h]) { by[h] = []; out.push(h) } by[h].push(x) })
                                         return out.map(function (h) { return [h, by[h]] }) }
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
                                                width: parent.width; height: xn.height + 6; radius: 5
                                                color: o === "Timed out" ? Theme.mix(Theme.med, Theme.surface2, 0.16) : Auto.problem(o) ? Theme.mix(Theme.crit, Theme.surface2, 0.16) : Theme.surface2
                                                Txt { id: xn; x: 8; y: 3; width: parent.width - 16 - xo.implicitWidth - 8; text: page.actionName(rc.modelData.e, modelData.action_id); font.pixelSize: 12 }
                                                Txt { id: xo; anchors.right: parent.right; anchors.rightMargin: 8; y: 3; font.pixelSize: 12; elide: Text.ElideNone
                                                      color: parent.o === "Timed out" ? Theme.med : Auto.problem(parent.o) ? Theme.crit : Theme.text3
                                                      text: parent.o === "Success" ? (modelData.duration_seconds ? modelData.duration_seconds + "s" : "done") : parent.o === "Timed out" ? "ran out of time" + (modelData.duration_seconds ? " at " + modelData.duration_seconds + "s" : "")
                                                            : parent.o === "Failed" ? "failed" + (modelData.exit_code !== undefined && modelData.exit_code !== null ? ", exit " + modelData.exit_code : "") : parent.o.toLowerCase() }
                                            }
                                        }
                                    }
                                }
                            }
                            Column {
                                visible: rc.modelData.bad
                                width: parent.width
                                spacing: 12
                                topPadding: 4
                                Rectangle { width: parent.width; height: 1; color: Theme.border }
                                Btn { anchors.right: parent.right; small: true; kind: "primary"; text: "Run again where it went wrong"; enabled: false; tip: "The Engine cannot run a rule again on the machines where it failed yet" }
                            }
                        }
                    }
                }
            }
        }
        StepPager {
            visible: page.rpages > 1
            width: parent.width
            from: page.rpi * 5 + 1
            to: Math.min(page.runOrder.length, page.rpi * 5 + 5)
            total: page.runOrder.length
            pageNo: page.rpi
            pages: page.rpages
            onStep: function (d) { page.rpg = page.rpi + d }
        }
        Quiet { visible: page.todayRuns.length === 0; text: "No rule has run yet today." }
    }

    // --- coming up --------------------------------------------------------------------------------------------------------------------
    Box {
        width: parent.width
        title: "Coming up"
        sub: "the next scheduled runs, in order; a rule that starts on an event runs whenever it happens, so it is not listed"
        Column {
            width: parent.width
            Repeater {
                model: page.coming
                delegate: Item {
                    required property var modelData
                    required property int index
                    width: parent.width
                    height: Math.max(nt.height, nn.height) + 16
                    Column { id: nt; y: 8; width: 110; spacing: 1
                        Txt { text: Time.hhmm(modelData.at); mono: true; font.weight: Font.DemiBold; elide: Text.ElideNone }
                        Txt { text: Time.sameDay(Time.ms(modelData.at), Time.now) ? "today" : Time.dayName(modelData.at); color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
                    Column { id: nn; x: 124; y: 8; width: parent.width - 124 - 14 - sk.width; spacing: 1
                        Txt { width: parent.width; text: modelData.title; font.weight: Font.DemiBold }
                        Txt { width: parent.width; text: modelData.line || ""; color: Theme.text3; font.pixelSize: 12 } }
                    MouseArea { x: nn.x; y: nn.y; width: nn.width; height: nn.height; cursorShape: Qt.PointingHandCursor; onClicked: if (modelData.to && modelData.to[1]) page.sel = Number(modelData.to[1]) }
                    Btn { id: sk; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; small: true; text: "Skip this once"; enabled: false; tip: "The Engine cannot skip one run yet" }
                    Rectangle { visible: index < page.coming.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
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
