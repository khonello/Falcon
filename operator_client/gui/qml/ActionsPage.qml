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
    function usedBy(a) { return events.filter(function (e) { return (e.actions || []).some(function (x) { return x.id === a.id }) }) }
    readonly property var catWord: ({ control: "Control", monitoring: "Monitoring", custom: "Custom" })
    readonly property var rows: lib
    readonly property var cur: { for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; return rows.length ? rows[0] : null }
    readonly property var curRuns: runs
    readonly property int bad: strip.problems || 0

    RunOnce { id: runOnce; page: page }

    // --- the version 1 concept's layout (docs/design/concepts-admin.html, AdminActionsLayout) -------------------------------------------------
    property var picks: []                // machines picked to run it on now
    property bool loading: false
    property var pickedId: null
    property int busy: 0
    onSelChanged: picks = []
    Component.onCompleted: { load(); var a = Nav.takeArrive("actions"); if (a !== null && Fleet.byHost[a]) picks = [a] }
    onCurChanged: { loadRuns(); loading = true; ldT.restart() }
    Timer { id: ldT; interval: Theme.loadMs; onTriggered: { page.loading = false; page.pickedId = page.cur ? page.cur.id : null } }
    function runNow() {
        var a = cur, hosts = picks.slice()
        busy = hosts.length
        hosts.forEach(function (h) {
            var m = Fleet.byHost[h]
            falcon.call("control.action_run", { action_id: a.id, pc_id: m.pc_id }, function (ok, r) {
                page.busy -= 1
                if (!ok) Msg.failed(h + ": " + (r && r.message ? r.message : "not started"))
                if (page.busy === 0) { Msg.ok(a.name + " started on " + Theme.listNames(hosts, 3)); page.picks = []; again.restart() }
            })
        })
    }
    situation: {
        if (!lib.length) return "No actions yet."
        var custom = lib.filter(function (a) { return a.cat === "custom" }).length, byHand = strip.by_hand || 0
        var badRuns = Object.keys(board).map(function (k) { return board[k] }).filter(function (x) { return x.problems })
        return Theme.many(lib.length, "action") + ", " + Theme.fmt(custom) + " of them written here. " + Theme.many(byHand, "run") + " by hand this week"
               + (badRuns.length ? "; " + Theme.listNames(badRuns.map(function (x) { var a = page.lib.filter(function (y) { return y.id === x.action_id })[0]; return a ? a.name : "an action" }), 2) + " had a run go wrong." : ".")
    }
    situationAt: Time.now

    // runs by hand across every action, for Ran by hand lately
    property var hand: []
    function loadHand() { falcon.call("actions.runs", { limit: 200 }, function (ok, r) { page.hand = ok ? (r.runs || []).filter(function (x) { return !x.event_id }).slice(0, 6) : [] }) }
    Timer { running: true; interval: 10; onTriggered: page.loadHand() }
    function badRun(x) { return x.outcome === "Failed" || x.outcome === "Timed out" }
    property var outRun: null
    Modal {
        id: outM
        page: page
        title: page.outRun ? page.outRun.action + " on " + page.outRun.host : ""
        subtitle: page.outRun ? Time.atDay(page.outRun.at) + " · " + (page.outRun.event_id ? page.outRun.by.replace(/^rule: /, "") : "by hand") : ""
        width: 640
        RunOutput { width: 592; executionId: outM.visible && page.outRun ? page.outRun.run_id : 0 }
        footer: Btn { text: "Close"; onClicked: outM.close() }
    }
    function showOut(x) { outRun = x; outM.open() }

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
            gap: 2
            title: "Your actions"
            sub: String(page.lib.length)
            Repeater {
                model: [["control", "Control"], ["monitoring", "Monitoring"], ["custom", "Custom"]]
                delegate: Column {
                    id: cg
                    required property var modelData
                    readonly property var xs: page.lib.filter(function (a) { return a.cat === modelData[0] })
                    visible: xs.length > 0
                    width: parent.width
                    spacing: 2
                    Txt { topPadding: 10 + 1.2; bottomPadding: 4 - 1.2; text: cg.modelData[1]; font.pixelSize: 12; font.weight: Font.DemiBold; color: Theme.text3 }
                    Repeater {
                        model: cg.xs
                        delegate: Rectangle {
                            required property var modelData
                            readonly property var bb: page.b(modelData)
                            readonly property int used: page.usedBy(modelData).length
                            width: cg.width; height: lc.height + 18; radius: Theme.radius
                            color: page.cur && page.cur.id === modelData.id ? Theme.surface3 : aa.containsMouse ? Theme.surface2 : "transparent"
                            Icon { x: 10; y: 13; name: modelData.cat === "custom" ? "code" : modelData.cat === "monitoring" ? "eye" : "control"; size: 13; color: Theme.text3 }
                            Column { id: lc; x: 31; y: 9; width: parent.width - 31 - 10 - (parent.bb.problems ? 26 : 0); spacing: 1
                                Txt { width: parent.width; text: modelData.name; font.weight: Font.DemiBold }
                                Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12
                                      text: modelData.cat === "custom" ? (modelData.language === "powershell" ? "PowerShell" : "Python") + (modelData.created_by_name ? " · by " + modelData.created_by_name : "")
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
            sub: page.cur ? (page.cur.cat === "custom" ? (page.cur.language === "powershell" ? "PowerShell" : "Python") + ", written here" : "comes with Falcon") : "pick an action on the left"
            extra: Btn { visible: page.cur !== null && page.cur.cat === "custom"; small: true; iconName: "edit"; text: "Edit the script"; onClicked: Nav.go("actions", "edit-" + page.cur.id) }
            Txt { visible: page.cur !== null; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; font.pixelSize: 17; font.weight: Font.Medium; lh: 1.45; text: page.cur ? page.cur.description || page.cur.name : "" }
            Row {
                visible: page.cur !== null
                spacing: 24
                topPadding: 4
                Txt { textFormat: Text.StyledText; font.pixelSize: 13; elide: Text.ElideNone; text: "<font color='" + Theme.text3 + "'>Time limit</font>&nbsp; " + (page.cur && page.cur.timeout_seconds ? page.cur.timeout_seconds + "s" : "—") }
                Txt { textFormat: Text.StyledText; font.pixelSize: 13; width: Math.min(implicitWidth, sheet.innerW - 160)
                      text: "<font color='" + Theme.text3 + "'>Used by</font>&nbsp; " + (page.cur ? (page.usedBy(page.cur).map(function (e) { return Auto.nameOf(e) }).join(", ") || "no rule yet") : "") }
            }
            // run it now (acx-run: under a rule)
            Column {
                visible: page.cur !== null
                width: parent.width
                spacing: 8
                topPadding: 8
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Item {
                    width: parent.width
                    height: rh.height + 12
                    Txt { id: rh; y: 8; text: "Run it now"; font.weight: Font.DemiBold; elide: Text.ElideNone }
                    Txt { x: rh.implicitWidth + 10; y: rh.y + rh.baselineOffset - baselineOffset; text: "click machines to pick them; offline ones are dashed"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                    Row { anchors.right: parent.right; y: rh.y + rh.baselineOffset - 14; spacing: 10
                        Link { text: "Every machine"; font.pixelSize: 13; onClicked: page.picks = Fleet.machines.filter(function (m) { return m.online }).map(function (m) { return m.host }) }
                        Link { text: "Clear"; font.pixelSize: 13; onClicked: page.picks = [] } }
                }
                Repeater {
                    model: [["ADMIN PCS", Fleet.machines.filter(function (m) { return m.admin })], ["OTHER MACHINES", Fleet.machines.filter(function (m) { return !m.admin })]]
                    delegate: Column {
                        required property var modelData
                        visible: modelData[1].length > 0
                        width: parent.width
                        spacing: 8
                        Txt { topPadding: 4; text: modelData[0]; color: Theme.text4; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                        Flow {
                            width: parent.width
                            spacing: 8
                            Repeater {
                                model: parent.parent.modelData[1].slice().sort(function (a, b) { return a.host.localeCompare(b.host) })
                                delegate: Rectangle {
                                    required property var modelData
                                    readonly property bool on: page.picks.indexOf(modelData.host) >= 0
                                    width: Math.max(64, mn.implicitWidth + 16); height: 42; radius: 7
                                    color: !modelData.online ? "transparent" : on ? Theme.mix(Theme.accent, Theme.surface3, 0.28) : Theme.surface3
                                    border.width: 1
                                    border.color: !modelData.online ? Theme.borderStrong : ma.containsMouse ? Theme.borderStrong : "transparent"
                                    Txt { id: mn; anchors.centerIn: parent; text: modelData.host.replace(/^WS-/, ""); mono: true; font.pixelSize: 11; font.weight: Font.DemiBold; elide: Text.ElideNone
                                          color: !modelData.online ? Theme.text4 : parent.on ? Theme.accent : Theme.text3 }
                                    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; enabled: modelData.online; cursorShape: Qt.PointingHandCursor
                                                onClicked: page.picks = parent.on ? page.picks.filter(function (h) { return h !== modelData.host }) : page.picks.concat([modelData.host]) }
                                    Tip { text: modelData.host + (modelData.user ? ", " + modelData.user : "") + (modelData.online ? "" : " · offline") }
                                }
                            }
                        }
                    }
                }
                Item {
                    width: parent.width
                    height: runB.height + 10
                    Txt { y: 10; width: parent.width - runB.width - 12; anchors.verticalCenter: runB.verticalCenter; color: Theme.text2; font.pixelSize: 13
                          text: page.picks.length && page.cur ? page.cur.name + " on " + Theme.listNames(page.picks, 4) + (page.cur.timeout_seconds ? ", up to " + page.cur.timeout_seconds + "s each." : ".") : "Pick at least one machine." }
                    Btn { id: runB; y: 10; anchors.right: parent.right; kind: "primary"; iconName: "caretr"; text: "Run on " + page.picks.length; enabled: page.picks.length > 0 && page.busy === 0; onClicked: page.runNow() }
                }
            }
            // its last runs
            Column {
                visible: page.cur !== null
                width: parent.width
                spacing: 0
                topPadding: 8
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Item {
                    width: parent.width
                    height: lh2.height + 20
                    Txt { id: lh2; y: 16; text: "Its last runs"; font.weight: Font.DemiBold; elide: Text.ElideNone }
                    Txt { x: lh2.implicitWidth + 10; y: lh2.y + lh2.baselineOffset - baselineOffset; text: "from rules and by hand, this week"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                }
                Repeater {
                    model: page.runs.slice(0, 6)
                    delegate: Item {
                        required property var modelData
                        required property int index
                        readonly property real flex: (width - 90 - 80 - 64 - 48) / 2.3
                        width: parent.width; height: 36
                        Txt { width: 90; anchors.verticalCenter: parent.verticalCenter; mono: true; color: Theme.text3; elide: Text.ElideNone
                              text: Time.sameDay(Time.ms(modelData.at), Time.now) ? Time.hhmm(modelData.at) : Time.dayName(modelData.at) + " " + Time.hhmm(modelData.at) }
                        Txt { x: 102; width: 80; anchors.verticalCenter: parent.verticalCenter; mono: true; text: modelData.host || "" }
                        Txt { x: 194; width: parent.flex; anchors.verticalCenter: parent.verticalCenter; color: Theme.text3; font.pixelSize: 13; text: modelData.event_id ? String(modelData.by).replace(/^rule: /, "") : "by hand" }
                        Txt { x: 206 + parent.flex; width: parent.flex * 1.3; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 13; color: page.badRun(modelData) ? Theme.crit : Theme.text
                              text: modelData.summary || (modelData.outcome === "Success" ? "done in " + (modelData.took_s || 0) + "s" : modelData.outcome === "Timed out" ? "ran out of time at " + (modelData.took_s || modelData.limit_s) + "s" : String(modelData.outcome || "").toLowerCase()) }
                        Btn { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; small: true; kind: "text"; text: "Output"; onClicked: page.showOut(modelData) }
                        Rectangle { visible: index < Math.min(6, page.runs.length) - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
                Quiet { visible: page.runs.length === 0; text: "It has not run this week." }
            }
            Pulse { parent: sheet; key: page.pickedId }
        }
    }

    // --- ran by hand lately ------------------------------------------------------------------------------------------------------------
    Box {
        width: parent.width
        title: "Ran by hand lately"
        sub: "yours and the other Admins'; Output shows what each machine returned"
        Repeater {
            model: [["bad", "Failed", "on at least one machine it failed or ran out of time"], ["ok", "Successful", "or you stopped it"]]
            delegate: Group {
                id: hg
                required property var modelData
                required property int index
                readonly property var xs: page.hand.filter(function (x) { return modelData[0] === "bad" ? page.badRun(x) : !page.badRun(x) })
                visible: xs.length > 0
                spaced: index > 0 && page.hand.some(page.badRun)
                cardGap: 5
                width: parent.width
                title: modelData[1] + " · " + xs.length
                sub: modelData[2]
                Repeater {
                    model: hg.xs
                    delegate: Card {
                        required property var modelData
                        readonly property var a: page.lib.filter(function (y) { return y.id === modelData.action_id })[0] || null
                        width: hg.cardW
                        midW: 260
                        padV: 7
                        icon: a ? (a.cat === "custom" ? "code" : a.cat === "monitoring" ? "eye" : "control") : "playcircle"
                        hot: page.badRun(modelData)
                        title: modelData.action
                        line: modelData.summary || (modelData.outcome === "Success" ? "done" : String(modelData.outcome).toLowerCase()) + (page.badRun(modelData) ? " on " + modelData.host : "")
                        lineHot: page.badRun(modelData)
                        act: "Output"
                        actDoes: true
                        onActed: page.showOut(modelData)
                        onOpen: page.sel = modelData.action_id
                        mid: Row {
                            anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right
                            spacing: 18
                            Txt { text: modelData.host + " · by hand"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                            Txt { text: Time.sameDay(Time.ms(modelData.at), Time.now) ? Time.hhmm(modelData.at) : Time.dayName(modelData.at); mono: true; color: Theme.text3; elide: Text.ElideNone }
                        }
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
