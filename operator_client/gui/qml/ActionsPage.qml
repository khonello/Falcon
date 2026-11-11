import QtQuick
import "."

// ACTIONS: everything a rule can do, and what you can run by hand. The library (four figures that
// also filter by kind), the action beside it with the rules that use it and how its runs went, and
// under both its script (a custom one) and its recent runs, each opening to what it returned.
// Counted by the Engine (actions.board, actions.runs): runs from rules and runs by hand alike.
Page {
    id: page
    objectName: "actionsView"

    property var lib: []
    property var events: []
    property var board: ({})         // action id -> actions.board's row: runs, by hand, problems, last run, used by
    property var strip: ({})
    property var runs: []            // actions.runs for the action on the right
    property string cat: "All"
    property var sel: Nav.sub && !isNaN(Number(Nav.sub)) ? Number(Nav.sub) : null
    property int openRun: 0

    function load() {
        falcon.call("control.action_list", {}, function (ok, r) {
            var a = ok ? (r.actions || {}) : {}, out = []
            ;["control", "monitoring", "custom"].forEach(function (k) { (a[k] || []).forEach(function (x) { out.push(Object.assign({ cat: k }, x)) }) })
            page.lib = out
        })
        falcon.call("control.event_list", {}, function (ok, r) { page.events = ok ? (r.events || []) : [] })
        falcon.call("actions.board", {}, function (ok, r) {
            var b = {}
            if (ok) (r.actions || []).forEach(function (x) { b[x.action_id] = x })
            page.board = b; page.strip = ok ? (r.strip || {}) : {}
        })
        loadRuns()
    }
    function loadRuns() {
        if (!cur) { runs = []; return }
        var id = cur.id
        falcon.call("actions.runs", { action_id: id, limit: 50 }, function (ok, r) { if (ok && page.cur && page.cur.id === id) page.runs = r.runs || [] })
    }
    Connections { target: falcon; function onPushReceived(type) { if (/^(event|action|execution)/.test(type)) again.restart() } }
    Timer { id: again; interval: 600; onTriggered: page.load() }

    function b(a) { return a ? board[a.id] || {} : {} }
    function usedBy(a) { return (b(a).used_by || []) }
    function whoWord(w) { return w === "You" ? "you" : w }
    function langWord(a) { return (a.custom_script_language || a.language) === "powershell" ? "PowerShell" : "Python" }
    readonly property var catWord: ({ control: "Control", monitoring: "Monitoring", custom: "Custom" })
    readonly property var rows: lib
    readonly property var cur: { for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; var first = rows.filter(function (a) { return a.name === "Take a screenshot" })[0]; return first || rows[0] || null }
    readonly property var curRuns: runs
    readonly property int bad: strip.problems || 0

    // --- the version 1 concept's layout (docs/design/concepts-admin.html, AdminActionsLayout) -------------------------------------------------
    property var picks: []                // machines picked to run it on now
    property bool loading: false
    property var pickedId: null
    // a run by hand: each picked machine runs, then reports; when they have all reported it joins Ran by hand lately
    property var run: null                // { id, action, lim, at, xs: [{ pc, host, st, exec, sec, t0 }] }
    readonly property var here: run && cur && run.id === cur.id ? run : null
    readonly property bool busy: here !== null && here.xs.some(function (y) { return y.st === "Running" })
    readonly property int doneN: here ? here.xs.filter(function (y) { return y.st !== "Running" }).length : 0
    readonly property int failN: here ? here.xs.filter(function (y) { return Auto.problem(y.st) }).length : 0
    // your own PC: the console is on it, so it is on; an Admin's PC is not among the machines
    readonly property var mePc: {
        for (var i = 0; i < Fleet.depts.length; i++) for (var j = 0; j < (Fleet.depts[i].admins || []).length; j++) {
            var a = Fleet.depts[i].admins[j]
            if (a.account_id === falcon.accountId && a.pc_id) return { pc_id: a.pc_id, host: a.hostname || a.pc_hostname || "", user: a.name, online: true }
        }
        return null
    }
    function pcOf(h) { return mePc && mePc.host === h ? mePc : Fleet.byHost[h] }
    function tileOf(h) { return here ? here.xs.filter(function (y) { return y.host === h })[0] || null : null }
    onSelChanged: { if (!busy) run = null }
    Component.onCompleted: { load(); var a = Nav.takeArrive("actions"); if (a !== null && Fleet.byHost[a]) picks = [a] }
    onCurChanged: { loadRuns(); pickedId = cur ? cur.id : null; loading = true; ldT.restart() }
    Timer { id: ldT; interval: Theme.loadMs; onTriggered: page.loading = false }
    function runNow() {
        var a = cur
        run = { id: a.id, action: a.name, lim: a.timeout_seconds, at: new Date(Time.now).toISOString(),
                xs: picks.map(function (h) { return { pc: page.pcOf(h).pc_id, host: h, st: "Running", exec: 0, sec: 0, t0: Time.now } }) }
        run.xs.forEach(function (x) {
            falcon.call("control.action_run", { action_id: a.id, pc_id: x.pc }, function (ok, r) {
                if (ok) page.setRun(x.host, { exec: r.execution_id || (r.executions && r.executions[0] ? r.executions[0].execution_id : 0) })
                else { page.setRun(x.host, { st: "Failed" }); Msg.failed(x.host + ": " + (r && r.message ? r.message : "not started")) }
            })
        })
        poll.start()
    }
    function setRun(h, o) {
        if (!run) return
        run = Object.assign({}, run, { xs: run.xs.map(function (y) { return y.host === h ? Object.assign({}, y, o) : y }) })
    }
    // each machine reports through control.execution
    Timer {
        id: poll
        interval: 1000
        repeat: true
        onTriggered: {
            var waiting = page.run ? page.run.xs.filter(function (y) { return y.st === "Running" && y.exec }) : []
            if (page.run && !page.run.xs.some(function (y) { return y.st === "Running" })) { stop(); again.restart(); page.loadHand(); return }
            waiting.forEach(function (y) {
                falcon.call("control.execution", { execution_id: y.exec }, function (ok, r) {
                    if (!ok || !r.execution || r.execution.status === "pending") return
                    page.setRun(y.host, { st: Auto.outcome(r.execution), sec: Math.max(1, Math.round((Time.now - y.t0) / 1000)) })
                })
            })
        }
    }
    function stopRun() {
        var ids = run.xs.filter(function (y) { return y.st === "Running" && y.exec }).map(function (y) { return y.exec })
        if (!ids.length) return
        falcon.call("control.terminate_run", { execution_ids: ids }, function (ok, r) { if (!ok) Msg.failed(r && r.message ? r.message : "Not stopped") })
    }
    // the output of the run just made, as Ran by hand lately shows it
    function showHere() {
        var r = here
        showOut({ action: r.action, who: "You", at: r.at, from: "by you", xs: r.xs.map(function (y) { return { host: y.host, pc_id: y.pc, run_id: y.exec, outcome: y.st, took_s: y.sec, limit_s: r.lim, at: r.at } }) })
    }
    situation: {
        if (!lib.length) return "No actions yet."
        var custom = lib.filter(function (a) { return a.cat === "custom" }).length, byHand = strip.by_hand || 0
        var worst = handRuns.filter(badRun)[0], rules = {}
        Object.keys(board).forEach(function (k) { (board[k].used_by || []).forEach(function (u) { rules[u.event_id] = 1 }) })
        var n = Object.keys(rules).length
        return Theme.many(lib.length, "action") + ", " + Theme.fmt(custom) + " of them written here. " + Theme.many(byHand, "run") + " by hand this week"
               + (worst ? "; " + worst.action + (worst.outcome === "Timed out" ? " ran out of time on " : " failed on ") + worst.host + "." : ".")
               + (n ? " " + Theme.many(n, "rule") + (n === 1 ? " uses them." : " use them.") : "")
    }
    situationAt: Time.now

    // runs by hand across every action, for Ran by hand lately
    property var handRuns: []
    function loadHand() { falcon.call("actions.runs", { limit: 200 }, function (ok, r) { page.handRuns = ok ? (r.runs || []).filter(function (x) { return !x.event_id }) : [] }) }
    // one run on several machines is one card: the same action, by the same person, within the half hour
    readonly property var hand: {
        var by = {}, out = []
        handRuns.forEach(function (x) {
            var k = x.action + "|" + (x.who || "") + "|" + Math.round(Time.ms(x.at) / 1800000)
            if (!by[k]) { by[k] = { action: x.action, action_id: x.action_id, who: x.who, at: x.at, xs: [] }; out.push(by[k]) }
            by[k].xs.push(x)
        })
        out.forEach(function (r) { r.bad = r.xs.some(page.badRun); r.from = r.who ? "by " + page.whoWord(r.who) : "by hand" })
        var late = function (a, b) { return Time.ms(b.at) - Time.ms(a.at) }
        return out.filter(function (r) { return r.bad }).sort(late).concat(out.filter(function (r) { return !r.bad }).sort(late)).slice(0, 6)
    }
    Timer { running: true; interval: 10; onTriggered: page.loadHand() }
    function badRun(x) { return x.outcome === "Failed" || x.outcome === "Timed out" }
    RunOutputModal { id: outM; page: page }
    function showOut(r) { outM.show(r) }
    // one run from Its last runs, as the modal takes it
    function oneRun(x) { return { action: x.action, at: x.at, from: x.event_id ? String(x.by).replace(/^rule: /, "") : x.who ? "by " + whoWord(x.who) : "by hand", xs: [x] } }

    Row {
        width: parent.width
        spacing: 16
        readonly property real h: Math.max(libP.implicitHeight, sheet.implicitHeight)
        // --- your actions -----------------------------------------------------------------------------------------------------------
        Box {
            id: libP
            objectName: "actionList"
            width: (parent.width - 16) * 4 / 12
            height: parent.h
            gap: 0
            title: "The actions"
            sub: String(page.lib.length)
            Repeater {
                model: [["control", "Control"], ["monitoring", "Monitoring"], ["custom", "Custom"]]
                delegate: Column {
                    id: cg
                    required property var modelData
                    required property int index
                    readonly property var xs: page.lib.filter(function (a) { return a.cat === modelData[0] })
                    visible: xs.length > 0
                    width: parent.width
                    Txt { topPadding: cg.index === 0 ? 7.6 : 17; bottomPadding: 4 - 1.2; text: cg.modelData[1]; font.pixelSize: 12; font.weight: Font.DemiBold; color: Theme.text3 }
                    PagedList {   // six a page per kind of action (the user, 11 Nov 2026); the one picked stays on the page shown
                        id: cp; reserve: false; items: cg.xs; per: 6; keep: page.cur ? cg.xs.findIndex(function (a) { return a.id === page.cur.id }) : -1
                        delegate: Rectangle {
                            required property var modelData
                            readonly property var bb: page.b(modelData)
                            readonly property int used: page.usedBy(modelData).length
                            width: cg.width; height: 55.75; radius: Theme.radius
                            color: page.cur && page.cur.id === modelData.id ? Theme.surface3 : aa.containsMouse ? Theme.surface2 : "transparent"
                            Icon { x: 10; y: 13; name: modelData.cat === "custom" ? "code" : modelData.cat === "monitoring" ? "eye" : "control"; size: 13; color: Theme.text3 }
                            Column { id: lc; x: 31; y: 9; width: parent.width - 31 - 10 - (parent.bb.problems ? 26 : 0); spacing: 1
                                Txt { width: parent.width; text: modelData.name; font.weight: Font.DemiBold }
                                Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12
                                      text: modelData.cat === "custom" ? page.langWord(modelData) + (modelData.created_by_name ? " · by " + page.whoWord(modelData.created_by_name) : "")
                                            : parent.parent.used ? "used by " + Theme.many(parent.parent.used, "rule") : "run by hand only" } }
                            Rectangle { visible: !!parent.bb.problems; anchors.right: parent.right; anchors.rightMargin: 10; y: 10; width: 18; height: 18; radius: 9; color: Theme.crit
                                        Txt { anchors.centerIn: parent; text: parent.parent.bb.problems || ""; color: Theme.inverse; font.pixelSize: 11; elide: Text.ElideNone } }
                            MouseArea { id: aa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.sel = modelData.id }
                        }
                    }
                }
            }
        }
        // --- the picked action: what it does, run it now, its last runs -----------------------------------------------------------
        Box {
            id: sheet
            objectName: "actionSheet"
            width: (parent.width - 16) * 8 / 12
            height: parent.h
            gap: 14
            title: page.cur ? page.cur.name : "No action picked"
            sub: page.cur ? (page.cur.cat === "custom" ? page.langWord(page.cur) + ", written by " + page.whoWord(page.cur.created_by_name || "an Admin") + " on " + Time.day(page.cur.created_at) : "comes with Falcon") : "pick an action on the left"
            extra: Btn { visible: page.cur !== null && page.cur.cat === "custom"; small: true; headed: true; iconName: "edit"; text: "Edit the script"; onClicked: Nav.go("actions", "edit-" + page.cur.id) }
            Txt { visible: page.cur !== null; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; font.pixelSize: 17; font.weight: Font.Medium; lh: 1.45; textFormat: Text.StyledText
                  text: page.cur ? (page.cur.description || page.cur.name) + (page.cur.impact ? " <font color='" + Theme.text3 + "'>" + page.cur.impact + "</font>" : "") : "" }
            Row {
                visible: page.cur !== null
                spacing: 24
                Txt { textFormat: Text.StyledText; font.pixelSize: 13; elide: Text.ElideNone; text: "<font color='" + Theme.text3 + "'>Time limit</font>&nbsp; " + (page.cur && page.cur.timeout_seconds ? page.cur.timeout_seconds + "s" : "—") }
                Txt { textFormat: Text.StyledText; font.pixelSize: 13; width: Math.min(implicitWidth, sheet.innerW - 160)
                      text: "<font color='" + Theme.text3 + "'>Used by</font>&nbsp; " + (page.cur ? (page.usedBy(page.cur).map(function (u) { return u.name }).join(", ") || "no rule yet") : "") }
            }
            // run it now (acx-run: under a rule)
            Column {
                visible: page.cur !== null
                width: parent.width
                spacing: 8
                topPadding: 5
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Item {
                    width: parent.width
                    height: rh.height + 12
                    Txt { id: rh; y: 8; text: "Run it now"; font.weight: Font.DemiBold; elide: Text.ElideNone }
                    Txt { x: rh.implicitWidth + 10; y: rh.y + rh.baselineOffset - baselineOffset; text: "click machines to pick them; offline ones are dashed"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                    Row { visible: !page.busy; anchors.right: parent.right; y: rh.y + rh.baselineOffset - 14; spacing: 10
                        Link { text: "Every machine"; font.pixelSize: 13; onClicked: { page.run = null; page.picks = Fleet.machines.filter(function (m) { return m.online }).map(function (m) { return m.host }) } }
                        Link { text: "Clear"; font.pixelSize: 13; onClicked: { page.run = null; page.picks = [] } } }
                }
                Repeater {
                    model: [["ADMIN PCS", page.mePc ? [page.mePc] : []], ["OTHER MACHINES", Fleet.machines]]
                    delegate: Column {
                        required property var modelData
                        required property int index
                        visible: modelData[1].length > 0
                        width: parent.width
                        spacing: 8
                        Txt { topPadding: parent.index > 0 ? 8 : 4; text: modelData[0]; color: Theme.text4; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                        Flow {
                            width: parent.width
                            spacing: 8
                            Repeater {
                                model: parent.parent.modelData[1]
                                delegate: Rectangle {
                                    required property var modelData
                                    readonly property bool on: page.picks.indexOf(modelData.host) >= 0
                                    readonly property var st: page.tileOf(modelData.host)
                                    // running, then how it ended; else picked
                                    readonly property string state2: st ? (st.st === "Running" ? "run" : Auto.problem(st.st) ? "bad" : st.st === "Success" ? "ok" : "on") : on ? "on" : ""
                                    readonly property color tone: state2 === "bad" ? Theme.crit : state2 === "ok" ? Theme.ok : Theme.accent
                                    width: Math.max(64, mn.implicitWidth + 16); height: 42; radius: 7
                                    color: !modelData.online ? "transparent" : state2 === "" ? Theme.surface3
                                           : Theme.mix(tone, Theme.surface3, state2 === "run" ? 0.16 : state2 === "ok" ? 0.26 : 0.28)
                                    SequentialAnimation on opacity {
                                        running: parent.state2 === "run"; loops: Animation.Infinite; alwaysRunToEnd: true
                                        NumberAnimation { to: 0.6; duration: Theme.durPulse }
                                        NumberAnimation { to: 1; duration: Theme.durPulse }
                                    }
                                    border.width: modelData.online ? 1 : 0
                                    border.color: ma.containsMouse ? Theme.borderStrong : "transparent"
                                    DashBox { visible: !modelData.online }
                                    Txt { id: mn; anchors.centerIn: parent; text: modelData.host.replace(/^WS-/, ""); mono: true; font.pixelSize: 11; font.weight: Font.DemiBold; elide: Text.ElideNone
                                          color: !modelData.online ? Theme.text4 : parent.state2 !== "" ? parent.tone : Theme.text3 }
                                    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; enabled: modelData.online && !page.busy; cursorShape: Qt.PointingHandCursor
                                                onClicked: { if (page.here) page.run = null; page.picks = parent.on ? page.picks.filter(function (h) { return h !== modelData.host }) : page.picks.concat([modelData.host]) } }
                                    Tip { text: modelData.host + (modelData.user ? ", " + modelData.user : "") + (modelData.online ? "" : " · offline") + (parent.st ? " · " + parent.st.st.toLowerCase() : "") }
                                }
                            }
                        }
                    }
                }
                Item {
                    width: parent.width
                    height: runB.height + 10
                    Txt { y: 10; width: parent.width - runB.width - 12; anchors.verticalCenter: runB.verticalCenter; color: Theme.text2; font.pixelSize: 13; textFormat: Text.StyledText
                          text: page.busy ? "Running on " + page.here.xs.length + ": " + page.doneN + " of " + page.here.xs.length + " reported back."
                                : page.here ? (page.failN ? "<font color='" + Theme.crit + "'>" + page.failN + " of " + page.here.xs.length + " went wrong.</font>" : "Done on all " + page.here.xs.length + ".") + " Its output is in Ran by hand lately too."
                                : page.picks.length && page.cur ? page.cur.name + " on " + Theme.listNames(page.picks, 4) + ", up to " + page.cur.timeout_seconds + "s each." : "Pick at least one machine." }
                    Btn { id: runB; y: 10; anchors.right: parent.right
                          kind: page.busy ? "default" : "primary"
                          danger: !page.busy && !page.here && !!page.cur && !!page.cur.risky
                          iconName: page.busy ? "" : page.here ? "filesearch" : "caretr"
                          text: page.busy ? "Stop" : page.here ? "See the output" : "Run on " + page.picks.length
                          enabled: page.busy || page.here !== null || page.picks.length > 0
                          onClicked: page.busy ? page.stopRun() : page.here ? page.showHere() : page.runNow() }
                }
            }
            // its last runs
            Column {
                visible: page.cur !== null
                width: parent.width
                spacing: 8
                topPadding: 5
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Item {
                    width: parent.width
                    height: lh2.height + 16
                    Txt { id: lh2; y: 13; text: "Its last runs"; font.weight: Font.DemiBold; elide: Text.ElideNone }
                    Txt { x: lh2.implicitWidth + 10; y: lh2.y + lh2.baselineOffset - baselineOffset; text: "from rules and by hand, this week"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                }
                Repeater {
                    model: page.runs.slice(0, 6)
                    delegate: Item {
                        required property var modelData
                        required property int index
                        readonly property real flex: (width - 90 - 80 - 64 - 48) / 2.3
                        width: parent.width; height: 37
                        Txt { width: 90; anchors.verticalCenter: parent.verticalCenter; mono: true; color: Theme.text3; elide: Text.ElideNone
                              text: Time.sameDay(Time.ms(modelData.at), Time.now) ? Time.hhmm(modelData.at) : Time.dayName(modelData.at) + " " + Time.hhmm(modelData.at) }
                        Txt { x: 102; width: 80; anchors.verticalCenter: parent.verticalCenter; mono: true; text: modelData.host || "" }
                        Txt { x: 194; width: parent.flex; anchors.verticalCenter: parent.verticalCenter; color: Theme.text3; font.pixelSize: 13; text: modelData.event_id ? String(modelData.by).replace(/^rule: /, "") : "by hand" + (modelData.who ? ", " + page.whoWord(modelData.who) : "") }
                        Txt { x: 206 + parent.flex; width: parent.flex * 1.3; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 13; color: page.badRun(modelData) ? Theme.crit : Theme.text
                              text: modelData.summary || (modelData.outcome === "Success" ? "done in " + (modelData.took_s || 0) + "s" : modelData.outcome === "Timed out" ? "ran out of time at " + (modelData.took_s || modelData.limit_s) + "s" : String(modelData.outcome || "").toLowerCase()) }
                        Btn { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; small: true; kind: "text"; text: "Output"; onClicked: page.showOut(page.oneRun(modelData)) }
                        Rectangle { visible: index < Math.min(6, page.runs.length) - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
                Quiet { visible: page.runs.length === 0; text: "It has not run this week." }
            }
            Loading { parent: sheet; on: page.loading && page.cur !== null; under: sheet.headerHeight }
            Pulse { parent: sheet; key: page.pickedId }
        }
    }

    // --- ran by hand lately ------------------------------------------------------------------------------------------------------------
    Box {
        width: parent.width
        title: "Ran by hand lately"
        sub: "every Admin's; Output shows what each machine returned"
        Repeater {
            model: [["bad", "Failed", "on at least one machine it failed or ran out of time"], ["ok", "Successful", "or you stopped it"]]
            delegate: Group {
                id: hg
                required property var modelData
                required property int index
                readonly property var xs: page.hand.filter(function (r) { return modelData[0] === "bad" ? r.bad : !r.bad })
                visible: xs.length > 0
                spaced: index > 0 && page.hand.some(function (r) { return r.bad })
                cardGap: 5
                width: parent.width
                title: modelData[1] + " · " + xs.length
                sub: modelData[2]
                items: hg.xs; per: 5
                delegate: Card {
                    required property var modelData
                    readonly property var a: page.lib.filter(function (y) { return y.id === modelData.action_id })[0] || null
                    width: hg.cardW
                    midW: 260
                    padV: 7
                    icon: a ? (a.cat === "custom" ? "code" : a.cat === "monitoring" ? "eye" : "control") : "playcircle"
                    readonly property var worst: modelData.xs.filter(page.badRun)[0] || modelData.xs[0]
                    hot: modelData.bad
                    title: modelData.action
                    line: modelData.bad ? (worst.summary || String(worst.outcome)) + " on " + worst.host : modelData.xs.length > 1 ? "done on all " + modelData.xs.length : worst.summary || "done"
                    lineHot: modelData.bad
                    actions: Btn { small: true; iconName: "filesearch"; text: "Output"; onClicked: page.showOut(modelData) }
                    onOpen: page.sel = modelData.action_id
                    mid: Row {
                        anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right
                        spacing: 18
                        Txt { text: (modelData.xs.length > 1 ? modelData.xs.length + " machines" : modelData.xs[0].host) + " · " + modelData.from; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                        Txt { text: Time.sameDay(Time.ms(modelData.at), Time.now) ? Time.hhmm(modelData.at) : Time.dayName(modelData.at); mono: true; color: Theme.text3; elide: Text.ElideNone }
                    }
                }
            }
        }
        Quiet { visible: page.hand.length === 0; text: "Nothing has been run by hand lately." }
    }

    // --- write an action ---------------------------------------------------------------------------------------------------------------
    Box {
        width: parent.width
        accentFoot: true
        title: "Write an action"
        sub: "a Python or PowerShell script of your own; nothing is saved until you confirm"
        GiveSteps {
            steps: [["Say what it is", "its name, one line, and whether it changes the machine"], ["Write or upload the script", "checked as you type, and again on each machine"], ["Try it and save", "a test on one machine, and its time limit"]]
            act: "Write an action"
            onGo: Nav.go("actions", "new")
        }
    }
}
