import QtQuick
import "."

// ONE DECISION ONLY THE SUPER USER MAKES, whole. On the left why it is theirs, its picture, and for
// reports the reports themselves to tick; on the right the choices, the input the chosen one needs, and
// one act. A decided item shows what was decided and when, with Change.
Rectangle {
    id: root
    property var d: null
    signal decided(string id)
    property var pick: ({})
    property string input: ""
    property var depts: []
    property var untick: ({})
    property var done: ({})

    color: Theme.surface
    radius: Theme.radius
    border.width: 1
    border.color: Theme.border
    implicitHeight: Math.max(leftCol.height, rightCol.height) + 40

    readonly property var opt: {
        if (!d) return null
        var k = pick[d.id]
        for (var i = 0; i < d.options.length; i++) if (d.options[i].key === k) return d.options[i]
        return d.options[0]
    }
    readonly property var ticked: d && d.reports ? d.reports.filter(function (r) { return !root.untick[r.id] }) : []
    readonly property string missing: !opt ? "" : opt.cannot ? opt.cannot + "."
        : (opt.need === "message" || opt.need === "version") && input.trim() === "" ? (opt.need === "version" ? "Write the version first." : "Write the message first.")
        : opt.need === "depts" && !depts.length ? "Pick at least one department."
        : d && d.reports && opt.key === "mark" && !ticked.length ? "Tick at least one." : ""

    function act() {
        var o = opt, x = d
        var finish = function (text) { var dn = Object.assign({}, root.done); dn[x.id] = { text: text, at: Date.now() }; root.done = dn; root.input = ""; Desk.refresh(); root.decided(x.id); Msg.ok(text) }
        var fail = function (r) { Msg.failed(r && r.message ? r.message : "Not done") }
        if (o.go) { Nav.go(o.go[0], o.go[1]); return }
        if (x.kind === "reports" && o.key === "mark") {
            var left = root.ticked.length
            root.ticked.forEach(function (r) { falcon.call("reports.mark", { report_id: r.id }, function (ok, res) { if (!ok) fail(res); if (--left === 0) finish(root.ticked.length + " marked addressed") }) })
            return
        }
        if (x.kind === "reports" && o.key === "route") {
            falcon.call("reports.routing_set", { category: x.cat, department_ids: root.depts, include_earlier: true }, function (ok, res) {
                if (!ok) { fail(res); return } finish(Desk.word(x.cat) + " now goes to " + Theme.listNames(root.depts.map(function (id) { return Fleet.deptName(id) }))) })
            return
        }
        if (x.kind === "gate" && o.key === "approve") {
            falcon.call("updates.approve", { version: root.input.trim() }, function (ok, res) { if (!ok) { fail(res); return } finish("Approved " + root.input.trim()) })
            return
        }
        if (x.kind === "gate" && o.waits) { finish("Waiting for the gate"); return }
        if (x.kind === "proposal") {
            falcon.call("proposals.decide", { proposal_id: x.p.id, accept: o.key === "yes" }, function (ok, res) {
                if (!ok) { fail(res); return }
                finish(o.key !== "yes" ? "Dismissed" : res.paused ? "Paused" : res.mark ? "Mark " + res.mark + " from the machine it is on, on the Restricted page" : res.task_description ? "Give this as a task: " + res.task_description : "Accepted")
            })
            return
        }
        if (x.kind === "restricted") {
            falcon.call("flow.restricted_consent", { consent_id: x.c.id, grant: o.key === "yes" }, function (ok, res) {
                if (!ok) { fail(res); return } finish(o.key === "yes" ? "Allowed · the flow goes on" : "Kept paused") })
            return
        }
        if (x.kind === "handover" && o.key === "refuse") {
            falcon.call("enroll.refuse", { enrollment_id: x.w.id, reason: "refused" }, function (ok, res) { if (!ok) { fail(res); return } finish("Refused") })
            return
        }
        if (x.kind === "task" && o.key === "complete") {
            falcon.call("task.dept_complete", { task_id: x.task.id }, function (ok, res) { if (!ok) { fail(res); return } finish("Marked complete") })
            return
        }
        if (x.kind === "task" && o.key === "notyet") {
            falcon.call("task.dept_reopen", { task_id: x.task.id, note: root.input.trim() }, function (ok, res) { if (!ok) { fail(res); return } finish("Sent back as ongoing") })
            return
        }
    }

    Column {
        id: leftCol
        x: 20; y: 20
        width: root.width / 2 - 40
        spacing: 10
        Row { spacing: 8
              St { square: true; text: root.d ? Fleet.sevWord(root.d.sev) : ""; c: root.d ? Fleet.sevColor(root.d.sev) : Theme.text4 }
              Tag { visible: !!root.d && root.d.kind === "reports"; text: root.d && root.d.cat ? Desk.word(root.d.cat) : ""; iconName: root.d ? root.d.icon : "" } }
        Txt { width: parent.width; text: root.d ? root.d.title : ""; font.pixelSize: Theme.fTitle; font.weight: Font.DemiBold; wrapMode: Text.WordWrap; elide: Text.ElideNone }
        Txt { width: parent.width; text: root.d ? root.d.why : ""; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone; bottomPadding: 6 }
        DecisionPicture { width: parent.width; d: root.d; big: true; visible: !!root.d && root.d.kind !== "reports" }
        Column {
            visible: !!root.d && !!root.d.reports
            width: parent.width
            Repeater {
                model: root.d && root.d.reports ? root.d.reports.slice(0, 5) : []
                Item {
                    required property var modelData
                    width: leftCol.width; height: 34
                    Check { anchors.verticalCenter: parent.verticalCenter; controlled: true; checked: !root.untick[modelData.id]
                            onToggled: function (on) { var u = Object.assign({}, root.untick); u[modelData.id] = !on; root.untick = u } }
                    Txt { x: 26; width: parent.width - 120; anchors.verticalCenter: parent.verticalCenter; text: modelData.summary || ("R-" + modelData.id) }
                    Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: Time.at(modelData.generated_at); mono: true; color: Theme.text3 }
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                }
            }
            Txt { topPadding: 8; color: Theme.text3; font.pixelSize: 12
                  text: root.d && root.d.reports ? root.ticked.length + " of " + root.d.reports.length + " ticked" + (root.d.reports.length > 5 ? " · the first five shown" : "") : "" }
        }
    }
    Rectangle { x: root.width / 2; y: 0; width: 1; height: root.height; color: Theme.border }
    Column {
        id: rightCol
        x: root.width / 2 + 20; y: 20
        width: root.width / 2 - 40
        spacing: 10
        // decided
        Rectangle {
            readonly property var dn: root.d ? root.done[root.d.id] : null
            visible: !!dn
            width: parent.width; height: 56; radius: 6
            color: Theme.alpha(Theme.ok, 0.09); border.width: 1; border.color: Theme.alpha(Theme.ok, 0.35)
            Icon { x: 12; anchors.verticalCenter: parent.verticalCenter; name: "checkcircle"; size: 16; color: Theme.ok }
            Column { x: 36; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 130
                     Txt { text: parent.parent.dn ? parent.parent.dn.text : ""; font.weight: Font.DemiBold; width: parent.width }
                     Txt { text: parent.parent.dn ? "by you at " + Time.hhmm(parent.parent.dn.at) : ""; color: Theme.text3; font.pixelSize: 12 } }
            Btn { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; small: true; text: "Change"
                  onClicked: { var x = Object.assign({}, root.done); delete x[root.d.id]; root.done = x } }
        }
        Column {
            visible: !!root.d && !root.done[root.d.id]
            width: parent.width
            spacing: 8
            Repeater {
                model: root.d ? root.d.options : []
                Choice { required property var modelData; width: rightCol.width; on: root.opt !== null && modelData.key === root.opt.key; icon: modelData.icon; title: modelData.title; desc: modelData.desc
                         onClicked: { var p = Object.assign({}, root.pick); p[root.d.id] = modelData.key; root.pick = p; root.input = "" } }
            }
            TextArea2 { visible: root.opt !== null && root.opt.need === "message" && !root.opt.cannot; width: parent.width; placeholder: "A note for them; every Admin told sees it"
                        text: root.input; onEdited: function (t) { root.input = t } }
            Field { visible: root.opt !== null && root.opt.need === "version" && !root.opt.cannot; width: 200; placeholderText: "Next version, e.g. 1.4.3"; text: root.input; onTextEdited: root.input = text }
            Select { visible: root.opt !== null && root.opt.need === "depts"; width: parent.width; multiple: true; search: true; placeholder: "Which departments?"; values: root.depts
                     options: Fleet.depts.map(function (x) { return { value: x.id, label: x.admins.length ? x.name : x.name + " · no Admin", disabled: !x.admins.length } })
                     onPicked: function (v) { root.depts = v } }
            Item {
                width: parent.width; height: 34
                Txt { anchors.verticalCenter: parent.verticalCenter; width: parent.width - btns.width - 10; text: root.missing; color: Theme.text3; font.pixelSize: 12 }
                Row { id: btns; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                      Btn { text: "Skip"; onClicked: root.decided(root.d.id) }
                      Btn { kind: "primary"; text: root.opt ? root.opt.verb : ""; enabled: root.missing === ""; onClicked: root.act() } }
            }
        }
    }
}
