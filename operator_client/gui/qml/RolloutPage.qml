import QtQuick
import "."

// ROLLOUT, at both levels. A version is approved only when every machine runs the one before it, so
// the page is the machines holding the next one back: the list, the machine beside it, and how many
// run the current version under both. In an Admin's console the machines are the department's;
// approving and leaving a machine out of the gate are the Super User's.
Page {
    id: page
    objectName: "rolloutView"

    property string sel: Nav.sub ? String(Nav.sub) : ""
    property int dept: 0
    property string next: ""

    readonly property string cur: Fleet.version || "—"
    readonly property var behind: Fleet.machines.filter(function (m) { return m.behind })
    readonly property var rows: behind.filter(function (m) { return (!dept || m.dept === dept) && (m.host + " " + m.user + " " + m.deptName).toLowerCase().indexOf(list.query.toLowerCase()) >= 0 })
    readonly property var m: { for (var i = 0; i < rows.length; i++) if (rows[i].host === sel) return rows[i]; return rows.length ? rows[0] : null }
    readonly property int on: Fleet.machines.length - behind.length
    readonly property int fails: behind.reduce(function (a, x) { return a + (x.failures || 0) }, 0)
    readonly property var depts: Fleet.depts.filter(function (d) { return d.machines.length }).map(function (d) {
        return { d: d, n: d.machines.length, ok: d.machines.filter(function (x) { return !x.behind }).length }
    }).sort(function (a, b) { return a.ok / a.n - b.ok / b.n })

    Confirm { id: confirm; page: page }
    function retry(x) {
        falcon.call("updates.rollout_department", Nav.boss ? { department_id: x.dept } : {}, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not retried"); return }
            Msg.ok("Retrying " + Theme.many((r.targeted || []).length, "machine") + " in " + x.deptName); Fleet.refresh()
        })
    }
    function approve() {
        confirm.ask({ title: "Approve " + next.trim() + "?", ok: "Approve", text: "Every machine is told to update, department by department. The record notes that you approved it." },
                    function () { falcon.call("updates.approve", { version: page.next.trim() }, function (ok, r) {
                        if (!ok) { Msg.failed(r && r.message ? r.message : "Not approved"); return }
                        Msg.ok("Approved " + page.next.trim()); page.next = ""; Fleet.refresh() }) })
    }

    Strip {
        width: parent.width
        items: [
            { label: "Current version", value: page.cur, delta: Fleet.rollout && Fleet.rollout.version ? "approved " + Time.at(Fleet.rollout.version.approved_at) + (Nav.boss ? " by you" : " by the Super User") : "" },
            { label: "Running it", value: Theme.fmt(page.on), unit: "/ " + Theme.fmt(Fleet.machines.length), delta: Fleet.machines.length ? Math.round(page.on / Fleet.machines.length * 100) + "% of machines" : "" },
            { label: "Holding the next one back", value: Theme.fmt(page.behind.length), dc: page.behind.length ? Theme.crit : Theme.ok,
              delta: page.behind.length ? (Nav.boss ? "the next version waits on them" : "from this department") : (Nav.boss ? "the next version can be approved" : "none from this department") },
            { label: "Failed installs", value: Theme.fmt(page.fails), delta: page.fails ? page.behind.filter(function (x) { return x.failures }).map(function (x) { return x.host + " " + (x.failures === 1 ? "once" : x.failures === 2 ? "twice" : x.failures + " times") }).join(", ") : "none" }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            title: "Holding the gate"
            sub: "not yet on " + page.cur + " · click one to see it on the right"
            placeholder: "Filter by machine or department"
            tools: Select {
                visible: Nav.boss
                width: 170
                small: true
                popupWidth: 240
                value: page.dept
                options: [{ value: 0, label: "Every department" }].concat(page.depts.map(function (x) { return { value: x.d.id, label: x.d.name + " · " + Math.round(x.ok / x.n * 100) + "% on " + page.cur } }))
                onPicked: function (v) { page.dept = v }
            }
            rows: page.rows
            rowKey: "host"
            pick: page.m ? page.m.host : null
            onPicked: function (k) { page.sel = k }
            icon: "desktop"
            nameTitle: "Machine"
            nameMono: true
            nameText: function (x) { return x.host }
            nameLine: function (x) { return (x.user || "No one signed in") + " · " + x.deptName }
            cols: [{ title: "Running", width: 100, text: function (x) { return x.ver } },
                   { title: "Failed attempts", width: 160, text: function (x) { return x.failures ? String(x.failures) : "None yet" } },
                   { title: "Next try", width: 180, text: function (x) { return x.online ? "Next idle window" : "When it is back online" } }]
            now: function (x) { return x.escalated ? ["Escalated" + (Nav.boss ? " to you" : ""), "bad"] : !x.online ? ["Offline", "bad"] : ["Retrying", "wait"] }
            showEmpty: Fleet.loaded && page.behind.length === 0
            emptyIcon: "check"
            emptyTitle: "Every machine runs " + page.cur
            emptyText: "Nothing holds the next version back." + (Nav.boss ? " Approve it when it is ready." : "")
        }
        SidePanel {
            width: (parent.width - 14) * 4 / 12
            showEmpty: page.m === null
            emptyIcon: "desktop"
            emptyText: "Pick a machine in the list."
            title: page.m ? page.m.host : ""
            sub: page.m && page.sel === page.m.host ? "the one you picked" : "the first in the list · click another"
            facts: page.m ? [["Running", page.m.ver], ["Should run", page.cur], ["Failed attempts", String(page.m.failures || 0)], ["Escalated", page.m.escalated ? "Yes" + (Nav.boss ? ", to you" : ", to the Super User") : "No", page.m.escalated ? Theme.crit : null],
                             ["Next try", page.m.online ? "Next idle window" : "When it is back online"], ["Department", page.m.deptName]] : []
            actions: [
                Btn { visible: Nav.boss; text: "Leave it out of the gate"; enabled: false; tip: "Leaving a machine out of the gate is not built in the Engine yet" },
                Btn { kind: "primary"; text: "Retry now"; enabled: page.m !== null && page.m.online; onClicked: page.retry(page.m) }
            ]
        }
    }

    Panel {
        width: parent.width
        title: "Machines on " + page.cur
        sub: "by department · the gap to the goal is the machines holding the next version back"
        extra: [
            Txt { visible: !Nav.boss; text: "The Super User approves the next version once every machine runs " + page.cur; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter },
            Field { visible: Nav.boss; width: 120; height: Theme.controlSm; placeholderText: "Next version"; text: page.next; onTextEdited: page.next = text },
            Btn { visible: Nav.boss; small: true; kind: "primary"; text: "Approve"; enabled: page.behind.length === 0 && page.next.trim() !== ""
                  tip: page.behind.length ? "A version is approved only when every machine runs the one before it." : ""; onClicked: page.approve() }
        ]
        Column {
            width: parent.width
            spacing: 12
            Empty { visible: Fleet.machines.length === 0; width: parent.width; h: 160; icon: "cloudupload"; title: "No machines yet"; text: "How many machines run the current version." }
            Row {
                visible: Fleet.machines.length > 0
                width: parent.width
                spacing: 12
                Txt { text: Theme.fmt(page.on); font.pixelSize: 22; font.weight: Font.DemiBold; elide: Text.ElideNone }
                Txt { text: "of " + Theme.fmt(Fleet.machines.length) + " machines on " + page.cur; color: Theme.text3; anchors.baseline: parent.children[0].baseline; elide: Text.ElideNone }
            }
            Bar { visible: Fleet.machines.length > 0; width: parent.width; thickness: 12; v: page.on; max: Math.max(1, Fleet.machines.length); c: Theme.alpha(Theme.ser2, 0.7) }
            Repeater {
                model: page.depts
                Item {
                    required property var modelData
                    width: parent.width; height: 30
                    Txt { width: 200; text: modelData.d.name; anchors.verticalCenter: parent.verticalCenter }
                    Bar { x: 210; width: parent.width - 210 - 260; anchors.verticalCenter: parent.verticalCenter; v: modelData.ok; max: modelData.n; c: modelData.ok === modelData.n ? Theme.ok : Theme.med }
                    Txt { x: parent.width - 240; width: 110; anchors.verticalCenter: parent.verticalCenter; mono: true; text: modelData.ok + " of " + modelData.n
                          color: modelData.ok === modelData.n ? Theme.text2 : Theme.text }
                    Txt { visible: !modelData.d.admins.length; x: parent.width - 120; anchors.verticalCenter: parent.verticalCenter; text: "no Admin"; color: Theme.crit; font.pixelSize: 12 }
                    Btn { visible: Nav.boss && modelData.d.admins.length > 0 && modelData.ok < modelData.n; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; small: true; text: "Prompt"
                          onClicked: falcon.call("updates.prompt_admin", { department_id: modelData.d.id }, function (ok, r) {
                              if (!ok) { Msg.failed(r && r.message ? r.message : "Not sent"); return } Msg.ok("Prompted " + Theme.listNames(modelData.d.admins.map(function (a) { return a.name }))) }) }
                }
            }
            Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                  text: "How adoption climbed day by day needs the version history the Engine keeps, which the console cannot read yet." }
        }
    }
}
