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
    onCurChanged: loadRuns()
    Component.onCompleted: load()
    Connections { target: falcon; function onPushReceived(type) { if (/^(event|action|execution)/.test(type)) again.restart() } }
    Timer { id: again; interval: 600; onTriggered: page.load() }

    function b(a) { return a ? board[a.id] || {} : {} }
    function usedBy(a) { return events.filter(function (e) { return (e.actions || []).some(function (x) { return x.id === a.id }) }) }
    readonly property var catWord: ({ control: "Control", monitoring: "Monitoring", custom: "Custom" })
    readonly property var rows: lib.filter(function (a) { return (cat === "All" || page.catWord[a.cat] === cat) && (a.name + " " + (a.description || "")).toLowerCase().indexOf(list.query.toLowerCase()) >= 0 })
    readonly property var cur: { for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; return rows.length ? rows[0] : null }
    readonly property var curRuns: runs
    readonly property int bad: strip.problems || 0

    RunOnce { id: runOnce; page: page }

    Strip {
        width: parent.width
        on: page.cat === "All" ? null : page.cat
        onPick: function (k) { page.cat = k || "All" }
        items: [
            { label: "Actions", value: Theme.fmt(page.lib.length), delta: page.lib.filter(function (a) { return a.cat === "control" }).length + " control · " + page.lib.filter(function (a) { return a.cat === "monitoring" }).length + " monitoring" },
            { key: "Custom", label: "Custom", value: Theme.fmt(page.lib.filter(function (a) { return a.cat === "custom" }).length), delta: "scripts written here" },
            { label: "Runs this week", value: Theme.fmt(page.strip.runs || 0), delta: Theme.fmt(page.strip.by_hand || 0) + " by hand" },
            { label: "Problems this week", value: Theme.fmt(page.bad), delta: page.bad ? "failed or ran out of time" : "every run succeeded", dc: page.bad ? Theme.crit : undefined }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            title: page.cat === "All" ? "Action library" : page.cat + " actions"
            sub: page.cat === "All" ? "click one to see it on the right" : Theme.fmt(page.rows.length)
            subLink: page.cat === "All" ? "" : "every action"
            onSubLinkClicked: page.cat = "All"
            placeholder: "Find an action"
            actionLabel: "New custom action"
            actionDisabled: Nav.boss
            onAction: Nav.go("actions", "new")
            rows: page.rows
            pick: page.cur ? page.cur.id : null
            onPicked: function (k) { page.sel = k; page.openRun = 0 }
            icon: function (a) { return a.cat === "control" ? "control" : a.cat === "custom" ? "code" : "eye" }
            nameTitle: "Action"
            nameText: function (a) { return a.name + (a.custom_script_language ? " · " + (a.custom_script_language === "python" ? "Python" : "PowerShell") : "") }
            nameLine: function (a) { return a.description || (a.builtin_type || "").replace(/_/g, " ") }
            cols: [{ title: "Used by", width: 120, text: function (a) { var n = page.usedBy(a).length; return n ? Theme.many(n, "rule") : "No rules" } },
                   { title: "Runs, 7 days", width: 100, text: function (a) { return Theme.fmt(page.b(a).runs || 0) } },
                   { title: "Time limit", width: 90, text: function (a) { return a.timeout_seconds + "s" } }]
            nowTitle: "Last run"
            now: function (a) { var x = page.b(a).last_run; if (!x) return ["Not run yet", "wait"]; var o = x.outcome; return [o, o === "Success" ? "good" : o === "Stopped by you" || o === "Running" ? "wait" : "bad"] }
            showEmpty: page.lib.length === 0
            emptyIcon: "appstore"
            emptyTitle: "No actions yet"
            emptyText: "The built-in actions and the custom scripts written here appear in the library."
        }
        SidePanel {
            id: aside
            width: (parent.width - 14) * 4 / 12
            readonly property var a: page.cur
            readonly property var counts: { var c = {}; page.curRuns.forEach(function (x) { var o = x.outcome; c[o] = (c[o] || 0) + 1 }); return c }
            readonly property int probs: page.b(a).problems || 0
            showEmpty: a === null
            emptyIcon: "appstore"
            emptyText: "Pick an action in the list."
            title: a ? a.name : ""
            sub: a ? (a.description || "") : ""
            facts: a ? [["Kind", page.catWord[a.cat] + (a.custom_script_language ? " · " + (a.custom_script_language === "python" ? "Python" : "PowerShell") : "")], ["Time limit", a.timeout_seconds + "s"],
                        ["Runs, 7 days", Theme.fmt(page.b(a).runs || 0)], ["Problems, 7 days", probs ? String(probs) : "None", probs ? Theme.crit : null],
                        [a.cat === "custom" ? "Written by" : "Comes with", a.cat === "custom" ? (a.created_by_name || "this department") : "Falcon"]] : []
            actions: [
                Btn { visible: page.cur !== null && page.cur.cat === "custom"; iconName: "edit"; text: "Edit script"; enabled: !Nav.boss; onClicked: Nav.go("actions", "edit-" + page.cur.id) },
                Btn { kind: "primary"; iconName: "caretr"; text: "Run once"; onClicked: runOnce.start(page.cur) }
            ]
            Column {
                width: parent.width
                spacing: 6
                Txt { text: "USED BY"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Txt { visible: page.cur !== null && page.usedBy(page.cur).length === 0; text: "No rule uses it yet. It can still be run by hand."; color: Theme.text3; font.pixelSize: 12 }
                Repeater {
                    model: page.cur ? page.usedBy(page.cur) : []
                    Item { required property var modelData; width: parent.width; height: 26
                           Rectangle { width: 7; height: 7; radius: 4; color: Auto.kindColor(Auto.kind((modelData.condition_spec || {}).type)); anchors.verticalCenter: parent.verticalCenter }
                           Txt { x: 16; width: parent.width - 100; text: Auto.nameOf(modelData); anchors.verticalCenter: parent.verticalCenter }
                           Txt { anchors.right: parent.right; text: Auto.kind((modelData.condition_spec || {}).type); color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter } }
                }
            }
            Column {
                width: parent.width
                spacing: 8
                Txt { text: "OUTCOMES, 7 DAYS"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Txt { visible: page.curRuns.length === 0; text: "It has not run this week."; color: Theme.text3; font.pixelSize: 12 }
                Row {
                    visible: page.curRuns.length > 0
                    width: parent.width; height: 8; spacing: 2
                    Repeater { model: Object.keys(aside.counts)
                               Rectangle { required property var modelData; width: (parent.width - 6) * aside.counts[modelData] / page.curRuns.length; height: 8; radius: 2; color: Auto.outColor(modelData) } }
                }
                Row { spacing: 12
                      Repeater { model: Object.keys(aside.counts)
                                 St { required property var modelData; size: 12; c: Auto.outColor(modelData); text: aside.counts[modelData] + " " + modelData.toLowerCase() } } }
            }
        }
    }

    Panel {
        visible: page.cur !== null && page.cur.cat === "custom"
        width: parent.width
        title: "Script"
        sub: page.cur ? (page.cur.custom_script_language === "python" ? "Python" : "PowerShell") + " · checked when saved and again on each machine when it arrives" : ""
        Column {
            width: parent.width
            spacing: 10
            Rectangle {
                width: parent.width; height: sc.height + 24; radius: 5; color: Theme.surface2
                Txt { id: sc; x: 12; y: 12; width: parent.width - 24; mono: true; font.pixelSize: 12; wrapMode: Text.NoWrap; elide: Text.ElideNone; text: page.cur ? (page.cur.custom_script || "") : "" }
            }
            Row { spacing: 16
                  St { text: "Compiles"; c: Theme.ok; size: 12 }
                  St { text: "Only standard and Windows-native imports"; c: Theme.ok; size: 12 }
                  Txt { text: "Runs without a sandbox, with the worker client's rights"; color: Theme.text3; font.pixelSize: 12 } }
        }
    }
    Panel {
        visible: page.cur !== null
        width: parent.width
        flush: true
        title: page.cur ? "Recent runs · " + page.cur.name : ""
        sub: page.curRuns.length + " in the last 7 days, from rules and by hand · click one to see what it returned"
        Column {
            width: parent.width
            Rectangle {
                width: parent.width; height: 34; color: Theme.surface2
                Row { anchors.fill: parent
                      Repeater { model: [["When", 120], ["From", 230], ["Machine", 100], ["Time taken", 190], ["Result", page.w - 120 - 230 - 100 - 190 - 150], ["Outcome", 150]]
                                 Txt { required property var modelData; width: modelData[1]; leftPadding: 14; text: modelData[0]; color: Theme.text3; font.pixelSize: 12; font.weight: Font.Medium; anchors.verticalCenter: parent.verticalCenter } } }
            }
            Txt { visible: page.curRuns.length === 0; x: 14; topPadding: 14; bottomPadding: 14; text: "No runs this week."; color: Theme.text3 }
            Repeater {
                model: page.curRuns.slice(0, 8)
                Column {
                    id: runRow
                    required property var modelData
                    readonly property bool on: page.openRun === modelData.run_id
                    readonly property real secs: modelData.took_s || 0
                    width: parent.width
                    Rectangle {
                        width: parent.width; height: 38
                        color: ra.containsMouse ? Theme.surface2 : "transparent"
                        Row {
                            anchors.fill: parent
                            Txt { width: 120; leftPadding: 14; text: Time.atDay(modelData.at); mono: true; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                            Txt { width: 230; leftPadding: 14; text: modelData.by === "hand" ? "By hand" : String(modelData.by || "").replace(/^rule: /, ""); anchors.verticalCenter: parent.verticalCenter }
                            Txt { width: 100; leftPadding: 14; text: modelData.host || "—"; mono: true; anchors.verticalCenter: parent.verticalCenter }
                            Row { width: 190; leftPadding: 14; spacing: 8; anchors.verticalCenter: parent.verticalCenter
                                  Bar { width: 80; v: runRow.secs; max: Math.max(1, modelData.limit_s || 1); c: Auto.outColor(modelData.outcome); anchors.verticalCenter: parent.verticalCenter }
                                  Txt { text: Math.round(runRow.secs) + "s / " + (modelData.limit_s || 0) + "s"; mono: true; elide: Text.ElideNone } }
                            Txt { width: page.w - 120 - 230 - 100 - 190 - 150; leftPadding: 14; text: modelData.summary || "—"; color: modelData.summary ? Theme.text : Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                            Item { width: 150; height: parent.height
                                   St { x: 14; anchors.verticalCenter: parent.verticalCenter; text: modelData.outcome; c: Auto.outColor(modelData.outcome) } }
                        }
                        MouseArea { id: ra; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.openRun = runRow.on ? 0 : modelData.run_id }
                    }
                    RunOutput { visible: runRow.on; x: 134; width: parent.width - 148; executionId: runRow.on ? modelData.run_id : 0; topPadding: 4; bottomPadding: 12 }
                    Rectangle { width: parent.width; height: 1; color: Theme.grid }
                }
            }
        }
    }
}
