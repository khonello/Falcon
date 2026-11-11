import QtQuick
import "."

// THE ADMIN'S OVERVIEW, as the version 1 concept draws it (docs/design/concepts-admin.html, AdminOverviewPage): the situation
// in a sentence; Do first, one card per thing with its action on the line, beside your to-dos; the machines as tiles beside
// what has stopped running; today's hours with Now in the middle beside the live activity; and one sentence to do something.
// Every card that opens another page asks first and arrives with the thing picked (Nav.goAsk).
Page {
    id: page
    objectName: "overviewView"

    readonly property int gap: 14
    property var tasks: []          // every open task, with `verify` true when every target is found
    property var todos: []
    property var flows: []
    property var rules: []
    property var live: []
    property string lastPush: ""
    property int dp: 0              // Do first's page
    property string dv: "run"       // Do something: the verb
    property var dt: null           // and its target

    function load() {
        Kinds.load({ limit: 60 }, function (es) { page.live = es.filter(function (e) { return e.t !== null }).slice(0, 14) })
        falcon.call("todo.list", {}, function (ok, r) { page.todos = ok ? (r.todos || []).filter(function (t) { return !t.done }) : [] })
        falcon.call("flow.list", {}, function (ok, r) { page.flows = ok ? (r.flows || []) : [] })
        falcon.call("automation.board", {}, function (ok, r) { page.rules = ok ? (r.rules || []) : [] })
        falcon.call("task.list", {}, function (ok, r) {
            var open = ok ? (r.tasks || []).filter(function (t) { return t.status !== "completed" }) : []
            page.tasks = open
            // a task is handed in when every target is found: it waits on the person who gave it (as on Tasks)
            open.slice(0, 50).forEach(function (t) {
                falcon.call("task.get", { task_id: t.id }, function (ok2, r2) {
                    var its = ok2 ? (r2.task && r2.task.items) || r2.items || [] : []
                    if (its.length && its.every(function (i) { return i.status === "passed" }))
                        page.tasks = page.tasks.map(function (x) { return x.id === t.id ? Object.assign({ verify: true }, x) : x })
                })
            })
        })
    }
    Component.onCompleted: if (falcon.isConnected) load()
    Connections {
        target: falcon
        function onConnected() { page.load() }
        function onPushReceived(type, payload) {
            page.lastPush = type
            // a new row from the audit push itself, as the first rows come from audit.events: its person, machine and kind with it
            if (type === "audit.event" && payload)
                page.live = [{ t: Time.ms(payload.at) || Date.now(), kind: payload.kind || Kinds.of(payload.action_type), actor: payload.actor || "System",
                               what: payload.what || "", host: payload.host || "", id: payload.id, fresh: true }].concat(page.live).slice(0, 30)
            if (type === "todo.changed") falcon.call("todo.list", {}, function (ok, r) { page.todos = ok ? (r.todos || []).filter(function (t) { return !t.done }) : [] })
        }
    }

    // --- what the page reads ------------------------------------------------------------------------
    readonly property var ms: Fleet.machines
    readonly property var off: ms.filter(function (m) { return !m.online })
    readonly property var lag: ms.filter(function (m) { return m.online && (m.status === "high" || m.status === "critical") })
    readonly property var inside: ms.filter(function (m) { return m.held !== "" })
    readonly property var urgent: Fleet.issues.filter(function (i) { return i.sev === "critical" || i.past })
    readonly property var rest: Fleet.issues.filter(function (i) { return !(i.sev === "critical" || i.past) && (i.state === undefined || i.state === "open") })
    readonly property var verify: tasks.filter(function (t) { return t.verify })
    // Today, as the concept fills it: open tasks by their final deadline, and your to-dos
    readonly property var today: tasks.filter(function (t) { return t.final_deadline_at })
        .map(function (t) { return { at: t.final_deadline_at, title: t.description_raw || t.title || "", line: (t.assignee_name || "someone") + "'s task",
                                     overdue: Time.ms(t.final_deadline_at) < Time.now, to: ["tasks", t.id] } })
        .concat(todos.map(function (t) { return { at: t.due_at, title: t.text, line: "your to-do", overdue: !!t.overdue, to: ["tasks", null] } }))
        .sort(function (a, b) { return Time.ms(a.at) - Time.ms(b.at) })

    // one card per issue, as on Issues; kinds take turns, so Do first is not one kind five times. A button that names an
    // action does it here, after a confirm (the user, 2 Nov 2026); one that needs a judgement says Look and opens its page.
    // The button is the concept's: the issue's Delete copy, else its first decision that needs nothing more (Keep this,
    // Keep waiting, Accept, Remind). Delete copy is offered only where the Engine can reach the machine, as on Issues.
    function quick(i) {
        var m = Fleet.byHost[i.host]
        function act(key, verb, title, text, said, danger) {
            return { act: verb, ask: { title: title, text: text, ok: verb, danger: !!danger },
                     run: function (done) { falcon.call("issues.act", { issue_id: i.iid, key: key }, done) }, said: said }
        }
        if (i.iid === undefined) return null
        if (i.type === "file" && m && m.online)
            return act("delete", "Delete copy", "Delete the copy on " + i.host + "?", "Deletes " + (i.subject || "the copy") + " from " + i.host + " only. The original is not touched.", "Deleting the copy on " + i.host, true)
        if (i.type === "update")
            return m && m.online ? act("idle", "Keep this", "Let " + i.host + " retry when it is idle?", "The default: the machine retries by itself in its next idle window.", i.host + " retries when it is idle")
                                 : act("wait", "Keep waiting", "Retry when " + i.host + " is back online?", "The update runs as soon as " + i.host + " checks in again.", i.host + " retries when it is back")
        if (i.type === "deviation" && m && m.online) return { act: "Enter " + i.host, enter: m }
        if (i.type === "flow") {
            var who = String(i.subject || "").split(" → ")[1] || "them"
            return act("remind", "Remind", "Remind " + who + "?", "Sends the request again.", "Reminded " + who)
        }
        return null
    }
    readonly property var iconOf: ({ file: "fileprotect", update: "cloudsync", deviation: "warning", help: "message", flow: "branches" })
    function issueItems(xs, hot) {
        var ks = [], out = []
        xs.forEach(function (i) { var g = ks.filter(function (k) { return k[0] === i.type })[0]; if (g) g[1].push(i); else ks.push([i.type, [i]]) })
        for (var r = 0; ks.some(function (k) { return k[1].length > r }); r++)
            ks.forEach(function (k) {
                var i = k[1][r]; if (!i) return
                var q = page.quick(i)
                out.push({ k: "i" + i.id, ic: page.iconOf[i.type] || "alert", hot: hot, t: i.subject || i.title, s: i.title + " · " + i.host,
                           n: hot ? (i.past ? Time.waitLen(i.age - i.target) + " past its time" : "critical") : Time.waitLen(i.target - i.age) + " left",
                           act: q ? q.act : "Look", quick: q, go: ["issues", "Issues opens with “" + (i.subject || i.title) + "” on " + i.host + " picked.", i.id] })
            })
        return out
    }
    readonly property var items: {
        var srcs = [issueItems(urgent, true),
                    verify.map(function (t) { return { k: "t" + t.id, ic: "checksquare", hot: false, t: t.description_raw || t.title, s: "Task · " + (t.assignee_name || "") + (Fleet.byAccount(t.assignee_account_id) ? " on " + Fleet.byAccount(t.assignee_account_id).host : ""),
                                                       n: "every target found; any Admin can close it", act: "Verify",
                                                       go: ["tasks", "Tasks opens with " + (t.description_raw || t.title) + " picked.", t.id] } }),
                    issueItems(rest, false)]
        var out = []
        for (var r = 0; srcs.some(function (x) { return x.length > r }); r++) srcs.forEach(function (x) { if (x[r]) out.push(x[r]) })
        return out
    }
    readonly property int show: 5
    readonly property int dpages: Math.max(1, Math.ceil(items.length / show))
    readonly property int dpi: Math.min(dp, dpages - 1)

    // what stopped running: flows that are not running cleanly, automations whose last run went wrong
    // a flow is named as Flows names it: its source folder and number, unless it was given a name
    function flowName(f) { return f.name || (String(f.source_path || "").split(/[\/]/).filter(function (x) { return x }).pop() || "flow") + "-" + f.id }
    // the Admin whose workstation a machine is, by name
    function adminAt(pc) {
        for (var i = 0; i < Fleet.depts.length; i++)
            for (var k = 0; k < (Fleet.depts[i].admins || []).length; k++)
                if (Fleet.depts[i].admins[k].pc_id === pc) return Fleet.depts[i].admins[k].name
        return ""
    }
    function flowState(f) {
        if (f.consent_status === "pending") {
            var d0 = (f.destinations || []).filter(function (d) { return d.let_them_choose || d.destination_pc_id })[0]
            var who = d0 ? page.adminAt(d0.destination_pc_id) || "an Admin" : "an Admin"
            return d0 && d0.let_them_choose ? "waits for " + who + " to pick a folder" : "waits for " + who + " to agree"
        }
        if (f.pause_reason === "restricted:consent") return "paused · a restricted file needs an Admin's consent"
        if (f.status === "paused") return "paused"
        if ((f.destinations || []).some(function (d) { return !!d.paused_reason })) return "one destination paused"
        return ""
    }
    // a flow waiting for someone to pick a folder is reminded through its issue, as on Issues
    function remindOf(f) {
        if (f.consent_status !== "pending") return null
        var who = page.flowState(f).replace(/^waits for /, "").replace(/ to .*$/, "")
        return { act: "Remind", ask: { title: "Remind " + who + "?", text: "Sends the request again, with your name on it.", ok: "Remind" },
                 run: function (done) { falcon.call("flow.remind", { flow_id: f.id }, done) }, said: "Reminded " + who }
    }
    // a flow someone asks to send to you is an ask on Flows, not something stopped
    function askedOfMe(f) { return f.consent_status === "pending" && (f.destinations || []).some(function (d) { return page.adminAt(d.destination_pc_id) === Nav.me || d.owner_account_id === falcon.accountId }) }
    readonly property var flowsOff: flows.filter(function (f) { return f.status !== "inactive" && flowState(f) !== "" && !askedOfMe(f) })
    readonly property var flowsOn: flows.filter(function (f) { return f.status !== "inactive" && flowState(f) === "" })
    readonly property var rulesOff: rules.filter(function (r) { return r.on && r.last_run_problem })
    readonly property var rulesOn: rules.filter(function (r) { return r.on && !r.last_run_problem })

    situation: {
        var n = Math.min(items.length, show)
        var s = items.length ? Theme.many(n, "thing") + " to do first" + (urgent.length ? "; " + Theme.many(urgent.length, "issue") + (urgent.length === 1 ? " is past its time or critical" : " are past their time or critical") : "")
                             : "Nothing needs you right now"
        s += "."
        if (off.length) s += " " + Theme.listNames(off.map(function (m) { return m.host }), 2) + (off.length === 1 ? " is" : " are") + " offline."
        var bad = flowsOff.length + rulesOff.length
        if (bad) s += " " + Theme.fmt(bad) + " of the flows and automations " + (bad === 1 ? "is" : "are") + " not running cleanly."
        return s
    }
    situationAt: Time.now
    sub: "Every department · " + Theme.many(ms.length, "machine") + " · as " + Nav.me + " sees it"

    // --- Do first, and your to-dos (c-84: 8 to 4, the two the same height) ------------------------------
    Row {
        width: parent.width
        spacing: page.gap
        readonly property real h: Math.max(doP.implicitHeight, todoP.implicitHeight)
        Box {
            id: doP
            objectName: "doFirst"
            width: (parent.width - page.gap) * 8 / 12
            height: parent.h
            title: "Do first"
            sub: Theme.many(page.items.length, "thing") + ", the most pressing first, from every page; each with its action on the line"
            Column {
                width: parent.width
                spacing: 6
                Repeater {
                    model: page.items.slice(page.dpi * page.show, page.dpi * page.show + page.show)
                    delegate: Card {
                        required property var modelData
                        width: parent.width
                        midW: 220
                        icon: modelData.ic
                        hot: modelData.hot
                        title: modelData.t
                        line: modelData.s
                        note: modelData.n
                        act: modelData.act
                        actDoes: !!modelData.quick
                        onOpen: Nav.goAsk(modelData.go[0], null, modelData.go[1], modelData.go[2])
                        onActed: page.doQuick(modelData.quick)
                    }
                }
            }
            StepPager {
                visible: page.dpages > 1
                width: parent.width
                from: page.dpi * page.show + 1
                to: Math.min(page.items.length, page.dpi * page.show + page.show)
                total: page.items.length
                pageNo: page.dpi
                pages: page.dpages
                onStep: function (d) { page.dp = page.dpi + d }
            }
            Quiet { visible: page.items.length === 0; icon: "check"; text: "Nothing needs you right now." }
        }
        Box {
            id: todoP
            objectName: "yourTodos"
            width: (parent.width - page.gap) * 4 / 12
            height: parent.h
            title: "Your to-dos · " + page.todos.length
            readonly property int late: page.todos.filter(function (t) { return t.overdue }).length
            sub: (late ? Theme.fmt(late) + " past its date; " : "") + "the soonest first; only you see them"
            Repeater {
                model: page.todos.slice().sort(function (a, b) { return (Time.ms(a.due_at) || 9e15) - (Time.ms(b.due_at) || 9e15) }).slice(0, 4)
                delegate: SuRow {
                    required property var modelData
                    icon: "square"
                    title: modelData.text
                    line: modelData.due_at ? "due " + Time.at(modelData.due_at) + (modelData.overdue ? ", past its date" : "") : "no date"
                    lineHot: !!modelData.overdue
                    act: "Done"
                    onActed: falcon.call("todo.done", { todo_id: modelData.id, done: true }, function (ok, r) {
                        if (!ok) { Msg.failed(r.message || "Could not tick it off"); return }
                        Msg.ok("Done: " + modelData.text); page.todos = page.todos.filter(function (t) { return t.id !== modelData.id })
                    })
                }
            }
            Quiet { visible: page.todos.length === 0; icon: "check"; text: "Nothing to remember." }
            Txt { visible: page.todos.length > 4; text: "and " + Theme.fmt(page.todos.length - 4) + " more on Tasks"; color: Theme.text3; font.pixelSize: 12 }
        }
    }

    // --- the machines, and what stopped running ------------------------------------------------------
    Row {
        width: parent.width
        spacing: page.gap
        readonly property real h: Math.max(mP.implicitHeight, fP.implicitHeight)
        Box {
            id: mP
            objectName: "machineTiles"
            width: (parent.width - page.gap) * 8 / 12
            height: parent.h
            title: "Machines"
            sub: Theme.many(page.ms.length, "machine") + ", every department; " + (page.off.length ? Theme.fmt(page.off.length) + " offline" : "all online")
                 + (page.lag.length ? ", " + Theme.fmt(page.lag.length) + " need a look" : "") + (page.inside.length ? ", " + Theme.fmt(page.inside.length) + " with someone inside" : "")
                 + "; click one to see it on Machines"
            readonly property int maxT: 22
            readonly property var sorted: page.ms.slice().sort(function (a, b) {
                var w = function (m) { return (m.online && (m.status === "high" || m.status === "critical")) * 2 + (!m.online ? 1 : 0) }
                return w(b) - w(a) })
            Item {
                width: parent.width
                // the key sits at the foot of the box (margin-top: auto): as tall as the box beside it allows
                height: Math.max(tiles.height + 10 + key.height, fP.implicitHeight - mP.headerHeight - 16)
            Flow {
                id: tiles
                width: parent.width
                spacing: 10
                Repeater {
                    model: mP.sorted.slice(0, page.ms.length > mP.maxT ? mP.maxT - 1 : mP.maxT)
                    delegate: Rectangle {
                        required property var modelData
                        readonly property bool isOff: !modelData.online
                        readonly property bool isLag: modelData.online && (modelData.status === "high" || modelData.status === "critical")
                        width: 66; height: 42; radius: 7
                        color: isOff ? "transparent" : isLag ? Theme.mix(Theme.crit, Theme.surface3, 0.16) : Theme.surface3
                        border.width: 1
                        border.color: isOff ? Theme.text4 : isLag ? Theme.alpha(Theme.crit, 0.35) : ta.containsMouse ? Theme.borderStrong : "transparent"
                        Txt { anchors.centerIn: parent; width: parent.width - 6; horizontalAlignment: Text.AlignHCenter; text: modelData.host.replace(/^WS-/, ""); font.pixelSize: 12; font.weight: Font.Medium
                              color: parent.isOff ? Theme.text4 : parent.isLag ? Theme.crit : Theme.text2 }
                        MouseArea { id: ta; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                    onClicked: Nav.goAsk("machines", null, "Machines opens with " + modelData.host + " picked.", modelData.host) }
                    }
                }
                Rectangle {
                    visible: page.ms.length > mP.maxT
                    width: 66; height: 42; radius: 7; color: "transparent"; border.width: 1; border.color: Theme.border
                    Txt { anchors.centerIn: parent; text: "+" + Theme.fmt(page.ms.length - mP.maxT + 1); color: Theme.text3; font.pixelSize: 12 }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: Nav.goAsk("machines", null, "Machines opens with every machine listed.") }
                }
            }
            Row {
                id: key
                anchors.bottom: parent.bottom
                spacing: 18
                topPadding: 4
                Repeater {
                    model: [["fine", Theme.surface3, "transparent"], ["needs a look", Theme.mix(Theme.crit, Theme.surface3, 0.16), Theme.alpha(Theme.crit, 0.35)], ["offline", "transparent", Theme.text4]]
                    delegate: Row {
                        required property var modelData
                        spacing: 6
                        Rectangle { width: 14; height: 11; radius: 3; color: modelData[1]; border.width: 1; border.color: modelData[2]; anchors.verticalCenter: parent.verticalCenter }
                        Txt { text: modelData[0]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                    }
                }
            }
            }
        }
        Box {
            id: fP
            objectName: "stuckRuns"
            width: (parent.width - page.gap) * 4 / 12
            height: parent.h
            title: "Flows and automations"
            sub: (page.flowsOff.length + page.rulesOff.length ? "only what has stopped or is stuck is listed; " : "")
                 + Theme.many(page.flowsOn.length, "flow") + " and " + Theme.many(page.rulesOn.length, "automation") + (page.rulesOn.length === 1 ? " is" : " are") + " running fine"
            PagedList {   // a flow waiting for someone is reminded here, through its issue; anything else is looked at on its page; five a page
                id: ovp; per: 5; items: page.flowsOff.map(function (f) { var s = page.flowState(f), q = page.remindOf(f)
                                                        return { ic: "branches", t: page.flowName(f), s: s, hot: s.indexOf("paused") >= 0, act: q ? q.act : "Fix", quick: q,
                                                                 go: ["flows", "Flows opens with " + page.flowName(f) + " picked.", f.id] } })
                       .concat(page.rulesOff.map(function (r) { return { ic: "thunderbolt", t: r.name, s: String(r.last_run || "its last run went wrong").replace(/ success$/, " succeeded"), hot: true, act: "Look",
                                                                          go: ["automation", "Automation opens with " + r.name + " picked.", r.event_id] } }))
                delegate: SuRow {
                    required property var modelData
                    icon: modelData.ic
                    title: modelData.t
                    line: modelData.s
                    lineHot: modelData.hot
                    act: modelData.act
                    onActed: modelData.quick ? page.doQuick(modelData.quick) : Nav.goAsk(modelData.go[0], null, modelData.go[1], modelData.go[2])
                    onOpen: Nav.goAsk(modelData.go[0], null, modelData.go[1], modelData.go[2])
                }
            }
            Quiet { visible: page.flowsOff.length + page.rulesOff.length === 0; icon: "check"; text: "Every flow and automation is running fine." }
        }
    }

    // --- today, and the live activity ----------------------------------------------------------------
    Row {
        width: parent.width
        spacing: page.gap
        readonly property real h: Math.max(dayP.implicitHeight, liveP.implicitHeight)
        Box {
            id: dayP
            objectName: "today"
            width: (parent.width - page.gap) * 8 / 12
            height: parent.h
            title: "Today"
            sub: "what has passed today above Now, what comes next below it; it moves on as the day does"
            extra: Txt { text: "The month in Calendar"; color: calA.containsMouse ? Theme.accent : Theme.text3; font.pixelSize: 13; elide: Text.ElideNone
                         MouseArea { id: calA; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: Nav.go("calendar") } }
            DayAgenda {
                width: parent.width
                items: page.today
            }
        }
        Box {
            id: liveP
            width: (parent.width - page.gap) * 4 / 12
            height: parent.h
            title: "Live activity"
            sub: "on your machines, as it happens"
            subDot: Theme.ok
            Quiet { visible: page.live.length === 0; text: "Each event appears here the moment it is recorded." }
            Column {
                width: parent.width
                Repeater {
                    model: page.live.slice(0, 9)
                    delegate: Item {
                        required property var modelData
                        width: parent.width
                        height: ln.height + 13
                        Txt { y: 6 + ln.baselineOffset - baselineOffset; width: 62; mono: true; color: Theme.text3; font.pixelSize: 13; text: Time.hhmm(modelData.t); elide: Text.ElideNone }
                        Rectangle { x: 70; y: 6 + ln.baselineOffset - 7; width: 7; height: 7; radius: 2; color: Kinds.color(modelData.kind) }
                        Txt {
                            id: ln
                            x: 88; y: 6
                            width: parent.width - 88
                            textFormat: Text.StyledText
                            text: (modelData.actor ? "<span style='font-weight:500'>" + modelData.actor + "</span> " : "") + "<font color='" + Theme.text2 + "'>" + modelData.what + "</font>"
                                  + (modelData.host ? " <font color='" + Theme.text3 + "' face='" + Theme.mono + "'>" + modelData.host + "</font>" : "")
                        }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
            }
        }
    }

    // --- do something, in one sentence --------------------------------------------------------------
    Confirm { id: confirm; page: page }
    function doQuick(q) {
        if (q.enter) { page.enter(q.enter); return }
        confirm.ask(q.ask, function () { q.run(function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not done"); return }
            Msg.ok(q.said + " · recorded"); Fleet.refresh(); page.load()
        }) })
    }
    function enter(m) {
        // two Admins are never on one machine at once, and nobody is pushed out (docs/design/v1-it-admin.md)
        if (m.held && m.held !== Nav.me) {
            confirm.ask({ title: m.held + " is in " + m.host, text: m.held + " has been inside" + (m.heldFrom ? " since " + Time.hhmm(m.heldFrom) : "") + ". Two Admins are never on one machine at once, and nobody is pushed out. Send them a message on Messages, or enter when they have left.", ok: "OK" }, null)
            return
        }
        confirm.ask({ title: "Enter " + m.host + "?", text: m.user ? m.user + " is signed in and cannot use the machine while you are in. You get 30 minutes, and can extend them." : "No one is signed in. You get 30 minutes, and can extend them.", ok: "Enter" },
                    function () { falcon.call("hierarchy.traverse", { pc_id: m.pc_id }, function (ok, r) {
                        if (!ok) { Msg.failed(r && r.message ? r.message : "Could not enter"); return }
                        Msg.ok("You are in " + m.host) }) })
    }
    readonly property var doVerbs: [{ value: "run", label: "Run an action on" }, { value: "task", label: "Give a task to" }, { value: "enter", label: "Enter" }, { value: "pause", label: "Pause the flow" }]
    readonly property var doTargets: dv === "pause" ? flowsOn.map(function (f) { return { value: f.id, label: page.flowName(f) } })
                                   : dv === "task" ? ms.filter(function (m) { return m.user }).map(function (m) { return { value: m.host, label: m.user + " on " + m.host } })
                                   : ms.map(function (m) { return { value: m.host, label: m.host + (m.user ? " · " + m.user : "") } })
    readonly property var doMachine: dv !== "pause" && dt !== null ? Fleet.byHost[dt] || null : null
    readonly property string doPrev: dt === null ? "" : dv === "run" ? "Opens Actions with " + dt + " picked, to choose what to run."
                                   : dv === "task" ? "Opens a new task for " + (doMachine ? doMachine.user : "them") + " on " + dt + "."
                                   : dv === "enter" ? "Enters " + dt + ". " + (doMachine && doMachine.user ? doMachine.user + " cannot use it while you are inside." : "Nobody is signed in.")
                                   : "Pauses " + flowName(flows.filter(function (f) { return f.id === dt })[0] || { id: dt }) + ". Files stop moving until you resume it; nothing is lost."
    function doIt() {
        if (dv === "run") Nav.goAsk("actions", null, "Actions opens with " + dt + " picked.", dt)
        else if (dv === "task") { Nav.preset = { page: "tasks", host: dt }; Nav.goAsk("tasks", "new", "A new task opens for " + (doMachine ? doMachine.user : "them") + " on " + dt + ".") }
        else if (dv === "enter") { if (doMachine) enter(doMachine) }
        else falcon.call("flow.pause", { flow_id: dt }, function (ok, r) { if (!ok) { Msg.failed(r.message || "Not paused"); return } Msg.ok("Paused · nothing is lost"); page.load() })
        dt = null
    }
    Box {
        objectName: "doSomething"
        width: parent.width
        accentFoot: true
        title: "Do something"
        sub: "one sentence; what it does is said before it is done"
        Row {
            width: parent.width
            spacing: 8
            Select { width: 200; options: page.doVerbs; value: page.dv; onPicked: function (v) { page.dv = v; page.dt = null } }
            Select {
                width: parent.width - 200 - goB.width - 16
                search: true
                options: page.doTargets
                value: page.dt
                placeholder: page.dv === "pause" ? "which flow" : page.dv === "task" ? "whom" : "which machine"
                onPicked: function (v) { page.dt = v }
            }
            Btn { id: goB; kind: "primary"; text: "Do it"; enabled: page.dt !== null; onClicked: page.doIt() }
        }
        Rectangle {
            visible: page.doPrev !== ""
            width: parent.width
            height: visible ? pv.height + 20 : 0
            radius: Theme.radius
            color: Theme.surface2
            Txt { id: pv; x: 12; y: 10; width: parent.width - 24; text: page.doPrev; wrapMode: Text.WordWrap; elide: Text.ElideNone }
        }
    }
}
