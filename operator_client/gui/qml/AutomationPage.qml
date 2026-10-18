import QtQuick
import "."

// AUTOMATION. What runs on its own here: four figures, the rules (switch one off in the list), the rule
// picked beside it with its last firings -- each opens to what every action returned -- and the runs of
// every rule over the week under both. A rule the Super User set is seen here, not changed or switched.
Page {
    id: page
    objectName: "automationView"

    property var events: []
    property var hist: ({})           // event id -> event_history
    property var board: ({})          // event id -> automation.board's row: who set it, by name
    property string pf: ""
    property var sel: Nav.sub && !isNaN(Number(Nav.sub)) ? Number(Nav.sub) : null
    property int openF: -1
    property int openRun: 0

    function load() {
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
        .filter(function (e) { return (pf === "" || page.hasProb(e)) && (e.name + " " + Auto.whenOf(e)).toLowerCase().indexOf(list.query.toLowerCase()) >= 0 })
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

    function ownerOf(e) { var b = board[e.id]; return b && b.owner ? b.owner : e.read_only ? "the Super User" : "this department" }
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

    PageTabs { options: [{ value: "automation", label: "Rules" }, { value: "actions", label: "Actions" }]; current: "automation" }

    Strip {
        width: parent.width
        on: page.pf === "" ? null : "probs"
        onPick: function (k) { page.pf = k ? "probs" : "" }
        items: [
            { label: "Rules", value: Theme.fmt(page.events.length), delta: page.events.some(function (e) { return e.read_only }) ? page.events.filter(function (e) { return e.read_only }).length + " set by the Super User" : "all made in this department" },
            { label: "Switched on", value: Theme.fmt(page.events.filter(function (e) { return e.enabled }).length), unit: "/ " + Theme.fmt(page.events.length),
              delta: page.events.every(function (e) { return e.enabled }) ? "every one" : page.events.filter(function (e) { return !e.enabled }).length + " switched off" },
            { label: "Fired this week", value: Theme.fmt(page.fired), delta: "each firing runs the rule's actions" },
            { key: page.probs ? "probs" : null, label: "Problems this week", value: Theme.fmt(page.probs), delta: page.probs ? "click to list the rules they came from" : "every run succeeded", dc: page.probs ? Theme.crit : undefined }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            title: page.pf ? "Rules with problems this week" : "Rules"
            sub: page.pf ? Theme.fmt(page.rows.length) : "what runs on its own here · click one to see it on the right"
            subLink: page.pf ? "every rule" : ""
            onSubLinkClicked: page.pf = ""
            placeholder: "Find a rule"
            actionLabel: "New rule"
            onAction: Nav.go("automation", "new")
            rows: page.rows
            pick: page.cur ? page.cur.id : null
            onPicked: function (k) { page.sel = k; page.openF = -1 }
            icon: function (r) { return Auto.kindIcon(r.kindW) }
            nameTitle: "Rule"
            nameText: function (r) { return r.name }
            nameLine: function (r) { return r.kindW + " · by " + page.ownerOf(r) }
            cols: [{ title: "On", width: 60, check: function (r) { return r.enabled }, locked: function (r) { return !!r.read_only }, toggle: function (r, on) { page.toggle(r, on) } },
                   { title: "Fired, 7 days", width: 130, bar: function (r) { return { v: page.firings(r).length, max: page.maxFired, text: Theme.fmt(page.firings(r).length) } } },
                   { title: "Last fired", width: 100, text: function (r) { var f = page.firings(r)[0]; return f ? Time.at(f.at) : "—" } }]
            nowTitle: "Last run"
            now: function (r) {
                var f = page.firings(r)[0]
                return !r.enabled ? ["Switched off", "wait"] : !f ? ["Not fired here this week", "wait"]
                     : [(f.runs || []).length ? Auto.lastRunText(f.runs) : "Nothing ran", (f.runs || []).some(function (x) { return Auto.problem(Auto.outcome(x)) }) ? "bad" : "good"]
            }
            showEmpty: page.events.length === 0
            emptyIcon: "thunderbolt"
            emptyTitle: "No rules yet"
            emptyText: "A rule watches for something on the department's machines and runs actions when it happens."
            emptyAct: "New rule"
            onEmptyAction: Nav.go("automation", "new")
        }
        SidePanel {
            id: side
            width: (parent.width - 14) * 4 / 12
            readonly property var r: page.cur
            readonly property var fs: r ? page.firings(r) : []
            readonly property int pr: r ? page.runs(r).filter(function (x) { return Auto.problem(Auto.outcome(x)) }).length : 0
            showEmpty: r === null
            emptyIcon: "thunderbolt"
            emptyText: "Pick a rule in the list."
            title: r ? r.name : ""
            sub: r && page.sel === r.id ? "the one you picked" : "the first in the list · click another"
            facts: r ? [["When", Auto.whenOf(r).replace(/^./, function (x) { return x.toUpperCase() })], ["On", Auto.whereFact(r)], ["Do", (r.actions || []).map(function (a) { return a.name }).join(", ") || "Nothing yet"],
                        ["Last fired", fs.length ? Time.atDay(fs[0].at) : "Not this week"], ["Fired, 7 days", Theme.fmt(fs.length)],
                        ["Problems, 7 days", pr ? pr + " failed or timed out" : "None", pr ? Theme.crit : null], ["Owner", page.ownerOf(r).replace(/^./, function (x) { return x.toUpperCase() })]] : []
            actions: [
                Item { width: sw.implicitWidth; height: Theme.control      // the actions wrap, so the switch centres in its own box
                       Check { id: sw; text: "Switched on"; controlled: true; checked: side.r !== null && side.r.enabled; enabled: side.r !== null && !side.r.read_only
                               anchors.verticalCenter: parent.verticalCenter; onToggled: function (on) { page.toggle(side.r, on) } } },
                Btn { text: "Test on one machine"; enabled: side.r !== null && (side.r.actions || []).length > 0; onClicked: page.test(side.r) },
                Btn { kind: "primary"; iconName: "edit"; text: "Edit"; enabled: side.r !== null && !side.r.read_only
                      tip: side.r && side.r.read_only ? "Set by the Super User for the whole organisation. Only they can change it." : ""
                      onClicked: Nav.go("automation", "edit-" + side.r.id) }
            ]
            Column {
                width: parent.width
                spacing: 0
                Txt { width: parent.width; text: "LAST FIRINGS · CLICK ONE TO SEE WHAT EACH ACTION RETURNED"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66; bottomPadding: 6 }
                Txt { visible: side.fs.length === 0; text: "It has not fired in the last 7 days."; color: Theme.text3; font.pixelSize: 12 }
                Repeater {
                    model: side.fs.slice(0, 5)
                    Column {
                        required property var modelData
                        required property int index
                        readonly property bool on: page.openF === index
                        width: parent.width
                        topPadding: 7; bottomPadding: 7
                        Item {
                            width: parent.width; height: 20
                            Txt { text: Time.atDay(modelData.at); mono: true; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                            Txt { x: 100; text: modelData.hostname || (modelData.machines + " machines"); mono: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                            Row {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 8
                                Repeater {
                                    model: Auto.summarize(modelData.runs || [])
                                    St { required property var modelData; size: 12; c: Auto.outColor(modelData[0])
                                         text: modelData[0] === "Success" ? (modelData[1] === 1 ? "Succeeded" : "All " + modelData[1] + " succeeded") : modelData[1] + " " + modelData[0].toLowerCase() }
                                }
                            }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.openF = parent.parent.on ? -1 : index }
                        }
                        Txt { visible: !!modelData.subject; text: modelData.subject || ""; color: Theme.text3; font.pixelSize: 12; width: parent.width }
                        Column {
                            visible: parent.on
                            x: 10
                            width: parent.width - 10
                            spacing: 10
                            topPadding: 8
                            Repeater {
                                model: parent.visible ? (modelData.runs || []).slice(0, 6) : []
                                Column {
                                    required property var modelData
                                    width: parent.width
                                    spacing: 4
                                    Item { width: parent.width; height: 20
                                           Txt { text: (side.r.actions || []).filter(function (a) { return a.id === modelData.action_id }).map(function (a) { return a.name })[0] || "Action"
                                                 font.weight: Font.Medium; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                                           St { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; size: 12; text: Auto.outcome(modelData); c: Auto.outColor(Auto.outcome(modelData)) } }
                                    RunOutput { width: parent.width; executionId: modelData.id }
                                }
                            }
                        }
                        Rectangle { width: parent.width; height: 1; color: Theme.grid }
                    }
                }
            }
        }
    }

    Panel {
        width: parent.width
        title: "Runs per day"
        sub: "all rules · last 7 days · by outcome"
        extra: Row {
            spacing: 14
            Repeater { model: page.perDay; Row { required property var modelData; spacing: 6
                       Rectangle { width: 10; height: 10; radius: 2; color: modelData.c; anchors.verticalCenter: parent.verticalCenter }
                       Txt { text: modelData.name; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } } }
        }
        DayBars {
            visible: page.allRuns.length > 0
            width: parent.width
            height: 170
            series: page.perDay
        }
        Empty { visible: page.allRuns.length === 0; width: parent.width; h: 170; icon: "barchart"; title: "No runs yet"; text: "Every run of every rule, by day and by outcome." }
    }
}
