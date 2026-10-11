import QtQuick
import "."

// RUN AN ACTION ONCE: choose machines, read what it does to them, run, then watch each machine go
// Queued -> Running -> Success / Failed / Skipped, and open any one to see what it returned. One call
// per machine, because that is how the Engine takes them; an offline machine is skipped, not queued.
Drawer {
    id: root
    width: 560
    property var a: null                    // the action, from control.action_list
    property string scope: "pick"
    property int dept: 0
    property var picks: []
    property var run: null                  // [{pc, host, st, exec, sec}]
    property string openH: ""
    title: a ? "Run once · " + a.name : ""

    function start(action) { a = action; run = null; openH = ""; scope = "pick"; picks = []; open() }
    readonly property var targets: scope === "all" ? Fleet.machines : scope === "dept" ? Fleet.inDept(dept) : Fleet.machines.filter(function (m) { return root.picks.indexOf(m.pc_id) >= 0 })
    readonly property var online: targets.filter(function (m) { return m.online })
    readonly property int done: run ? run.filter(function (x) { return x.st === "Success" || x.st === "Failed" || x.st === "Skipped" }).length : 0
    readonly property bool risky: a && /reboot|shutdown|restart|lock/.test(String(a.builtin_type || ""))
    function stColor(s) { return s === "Running" ? Theme.ser1 : s === "Success" ? Theme.ok : s === "Failed" ? Theme.crit : Theme.text4 }

    function go() {
        var rows = targets.map(function (m) { return { pc: m.pc_id, host: m.host, st: m.online ? "Queued" : "Skipped", exec: 0, sec: 0 } })
        run = rows
        rows.forEach(function (r0, i) {
            if (r0.st === "Skipped") return
            falcon.call("control.action_run", { action_id: root.a.id, pc_id: r0.pc }, function (ok, r) {
                var rs = root.run.slice(); rs[i] = Object.assign({}, rs[i], ok ? { st: "Running", exec: r.execution_id || (r.executions && r.executions[0] ? r.executions[0].execution_id : 0), t0: Date.now() } : { st: "Failed" })
                root.run = rs
            })
        })
        poll.start()
    }
    Timer {
        id: poll
        interval: 1500
        repeat: true
        onTriggered: {
            if (!root.run) { stop(); return }
            var waiting = root.run.filter(function (x) { return x.st === "Running" && x.exec })
            if (!waiting.length) { stop(); return }
            waiting.forEach(function (x) {
                falcon.call("control.execution", { execution_id: x.exec }, function (ok, r) {
                    if (!ok || !r.execution || r.execution.status === "pending") return
                    var o = Auto.outcome(r.execution)
                    root.run = root.run.map(function (y) { return y.exec === x.exec ? Object.assign({}, y, { st: o === "Success" ? "Success" : "Failed", sec: Math.max(1, Math.round((Date.now() - (y.t0 || Date.now())) / 1000)) }) : y })
                })
            })
        }
    }

    note: root.run ? root.done + " of " + root.run.length + " finished · click a machine to see what it returned"
                   : root.scope === "pick" && !root.picks.length ? "Pick at least one machine."
                   : "Runs on " + Theme.many(root.online.length, "machine") + " with a " + (root.a ? root.a.timeout_seconds : 0) + "s time limit"
    footer: [
        Btn { text: root.run ? "Close" : "Cancel"; onClicked: root.close() },
        Btn { visible: !root.run; kind: "primary"; danger: root.risky; enabled: root.online.length > 0; text: "Run on " + root.online.length; onClicked: root.go() }
    ]

    Column {
        visible: root.a !== null && root.run === null
        width: parent.width
        spacing: 18
        Txt { width: parent.width; text: root.a ? (root.a.description || "") : ""; color: Theme.text2; wrapMode: Text.WordWrap; elide: Text.ElideNone; visible: text !== "" }
        Column {
            width: parent.width
            spacing: 10
            Txt { text: "ON WHICH MACHINES"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
            Radio { width: parent.width; options: [{ value: "pick", label: "Machines I pick" }].concat(Nav.boss ? [{ value: "dept", label: "A department" }] : []).concat([{ value: "all", label: Nav.boss ? "Every machine" : "Every machine in this department" }])
                    value: root.scope; onPicked: function (v) { root.scope = v } }
            Select { visible: root.scope === "pick"; width: parent.width; multiple: true; search: true; placeholder: "Pick machines"; values: root.picks
                     options: Fleet.machines.map(function (m) { return { value: m.pc_id, label: m.host + " · " + (m.user || "no user") + (m.online ? "" : " · offline") } })
                     onPicked: function (v) { root.picks = v } }
            Select { visible: root.scope === "dept"; width: 240; value: root.dept || null; options: Fleet.depts.map(function (d) { return { value: d.id, label: d.name + " · " + d.machines.length + " machines" } })
                     onPicked: function (v) { root.dept = v } }
        }
        Column {
            width: parent.width
            spacing: 8
            Txt { text: "TIME LIMIT"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
            Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3
                  text: (root.a ? root.a.timeout_seconds : 0) + " seconds per machine, the action's own. A run that goes over is ended and counted as timed out." }
        }
        Rectangle {
            width: parent.width
            height: imp.height + 24
            radius: Theme.radius
            readonly property color c: root.risky ? Theme.crit : Theme.ser1
            color: Theme.alpha(c, 0.09)
            border.width: 1
            border.color: Theme.alpha(c, 0.35)
            Column {
                id: imp
                x: 14; y: 12
                width: parent.width - 28
                spacing: 4
                Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; textFormat: Text.RichText
                      text: "<b>What this does to them.</b> <span style='color:" + Theme.text2 + "'>" + (root.risky ? "People on these machines are interrupted: " : "") + Theme.many(root.online.length, "machine") + " run it now.</span>" }
                Txt { visible: root.targets.length > root.online.length; width: parent.width; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                      text: (root.targets.length - root.online.length) + " offline machine" + (root.targets.length - root.online.length === 1 ? " is" : "s are") + " skipped. A one-time run is not queued for later." }
                Txt { visible: root.a !== null && root.a.action_kind === "custom"; width: parent.width; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                      text: "A custom script, run without a sandbox. The run and its output are recorded." }
            }
        }
    }
    Column {
        visible: root.run !== null
        width: parent.width
        // one bar for all of them
        Row {
            width: parent.width
            height: 8
            spacing: 1
            Repeater {
                model: root.run ? ["Success", "Failed", "Skipped"] : []
                Rectangle { required property var modelData; readonly property int n: root.run.filter(function (x) { return x.st === modelData }).length
                            visible: n > 0; width: (root.width - 48) * n / root.run.length; height: 8; color: root.stColor(modelData) }
            }
        }
        Item { width: 1; height: 14 }
        Repeater {
            model: root.run || []
            Column {
                required property var modelData
                readonly property bool fin: modelData.st === "Success" || modelData.st === "Failed"
                readonly property bool on: root.openH === modelData.host
                width: parent.width
                Item {
                    width: parent.width; height: 36
                    Txt { width: 80; text: modelData.host; mono: true; anchors.verticalCenter: parent.verticalCenter }
                    St { x: 86; anchors.verticalCenter: parent.verticalCenter; text: modelData.st + (modelData.st === "Skipped" ? " · offline" : ""); c: root.stColor(modelData.st); breathe: modelData.st === "Running" }
                    Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; mono: true; color: Theme.text3; text: modelData.sec ? modelData.sec + "s" : modelData.st === "Running" ? "…" : "" }
                    MouseArea { anchors.fill: parent; enabled: parent.parent.fin; cursorShape: Qt.PointingHandCursor; onClicked: root.openH = parent.parent.on ? "" : modelData.host }
                }
                RunOutput { visible: parent.on; x: 86; width: parent.width - 86; executionId: parent.on ? modelData.exec : 0 }
                Rectangle { width: parent.width; height: 1; color: Theme.grid }
            }
        }
    }
}
