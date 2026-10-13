import QtQuick
import "."

// FLOWS, at both levels. The Super User sees every flow; an Admin's console sees the flows that touch
// the department. The list, the flow beside it, the flow drawn under both, and its sync log. A flow
// waiting on someone's agreement is answered here by the person asked, in a bar above the page.
Page {
    id: page
    objectName: "flowsView"

    property var flows: []
    property string sel: Nav.sub ? String(Nav.sub) : ""
    property var log: []

    function load() { falcon.call("flow.list", {}, function (ok, r) { page.flows = ok ? (r.flows || []) : [] }) }
    Component.onCompleted: load()
    Connections { target: falcon; function onPushReceived(type) { if (/^flow/.test(type)) again.restart() } }
    Timer { id: again; interval: 300; onTriggered: page.load() }

    function folder(p) { var x = String(p || "").replace(/[\\\/]+$/, "").split(/[\\\/]/); return x[x.length - 1] || p }
    // who made it: you, or an Admin this console knows by name (the Engine sends the account, not the name)
    function creator(f) {
        if (f.created_by_account_id === falcon.accountId) return "You"
        return f.created_by_name || Fleet.adminName(f.created_by_account_id) || "—"
    }
    function nameOf(f) { return folder(f.source_path) + "-" + f.id }
    function stateOf(f) {
        var paused = (f.destinations || []).filter(function (d) { return d.paused_reason })
        if (f.consent_status === "pending") return ["Waiting for agreement", "wait", "wait"]
        if (f.status === "inactive") return ["Retired", "wait", "off"]
        if (f.status === "paused" || paused.length) return ["A branch is paused", "bad", "deg"]
        return ["Copying", "good", "act"]
    }
    function lastCopy(f) {
        var m = null
        ;(f.destinations || []).forEach(function (d) { var t = d.last_sync ? Time.ms(d.last_sync.synced_at) : null; if (t && (!m || t > m)) m = t })
        return m
    }
    readonly property var rows: flows.map(function (f) {
        return Object.assign({ key: String(f.id), name: page.nameOf(f), st: page.stateOf(f),
                               path: f.source_hostname + " → " + (f.destinations || []).map(function (d) { return d.destination_hostname || "storage" }).filter(function (v, i, a) { return a.indexOf(v) === i }).join(", ") }, f)
    }).filter(function (f) { return (f.name + " " + f.path).toLowerCase().indexOf(list.query.toLowerCase()) >= 0 })
      .sort(function (a, b) { return (page.lastCopy(b) || 0) - (page.lastCopy(a) || 0) })
    readonly property var cur: { for (var i = 0; i < rows.length; i++) if (rows[i].key === sel) return rows[i]; return rows.length ? rows[0] : null }
    // the steps along the way, read from the Engine's stage tree (Sync.steps): named, and before or after the split
    readonly property var steps: Sync.steps(cur)
    onCurChanged: if (cur) falcon.call("flow.history", { flow_id: cur.id }, function (ok, r) { page.log = ok ? (r.history || []) : [] })
    readonly property var asks: flows.filter(function (f) {
        return f.consent_status === "pending" && (f.destinations || []).some(function (d) { return d.owner_account_id === falcon.accountId })
    })
    readonly property int nAct: flows.filter(function (f) { return page.stateOf(f)[2] === "act" }).length
    readonly property int nDeg: flows.filter(function (f) { return page.stateOf(f)[2] === "deg" }).length
    readonly property int nWait: flows.filter(function (f) { return page.stateOf(f)[2] === "wait" }).length

    // requests other people sent to the person at this console
    Repeater {
        model: page.asks
        Rectangle {
            required property var modelData
            width: page.w
            height: 44
            radius: Theme.radius
            color: Theme.accentSoft
            border.width: 1
            border.color: Theme.mix(Theme.accent, Theme.border, 0.3)
            Row {
                x: 14
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10
                Icon { name: "inbox"; size: 15; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter }
                Txt { anchors.verticalCenter: parent.verticalCenter; width: page.w - 260; textFormat: Text.RichText
                      text: "<b>A flow</b> wants to send you files <span style='color:" + Theme.text3 + "'>from <span style='font-family:" + Theme.mono + "'>" + modelData.source_hostname + " " + modelData.source_path
                            + "</span> · " + Time.atDay(modelData.created_at) + "</span>" }
            }
            Row {
                anchors.right: parent.right
                anchors.rightMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Btn { small: true; text: "Decline"; onClicked: falcon.call("flow.consent", { flow_id: modelData.id, granted: false }, function (ok, r) { if (!ok) { Msg.failed(r.message || "Not answered"); return } Msg.ok("Declined · they are told"); page.load() }) }
                Btn { small: true; kind: "primary"; text: "Accept"; onClicked: falcon.call("flow.consent", { flow_id: modelData.id, granted: true }, function (ok, r) { if (!ok) { Msg.failed(r.message || "Not answered"); return } Msg.ok("Accepted · it starts copying"); page.load() }) }
            }
        }
    }

    Strip {
        width: parent.width
        items: [
            { label: "Flows", value: Theme.fmt(page.flows.length), delta: Theme.fmt(page.flows.filter(function (f) { return f.created_by_account_id === falcon.accountId }).length) + " made by you" },
            { label: "Copying", value: Theme.fmt(page.nAct), unit: "/ " + Theme.fmt(page.flows.length), delta: page.nWait ? Theme.fmt(page.nWait) + " waiting for agreement" : "every flow" },
            { label: "A branch paused", value: Theme.fmt(page.nDeg), delta: page.nDeg ? "files queue until it is fixed" : "none", dc: page.nDeg ? Theme.crit : undefined },
            { label: "Last copy", value: page.flows.length && page.flows.some(page.lastCopy) ? Time.at(Math.max.apply(null, page.flows.map(function (f) { return page.lastCopy(f) || 0 }))) : "—", delta: "by any flow here" }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            title: Nav.boss ? "All flows in the organisation" : "Flows through this department"
            sub: Nav.boss ? "whoever made them · click one to see it on the right" : "made here, or chained to one that is · click one to see it on the right"
            placeholder: "Filter by flow or machine"
            actionLabel: "New flow"
            onAction: Nav.go("flows", "new")
            rows: page.rows
            rowKey: "key"
            pick: page.cur ? page.cur.key : null
            onPicked: function (k) { page.sel = k }
            icon: "branches"
            nameTitle: "Flow"
            nameText: function (r) { return r.name }
            nameLine: function (r) { return r.path }
            cols: [{ title: "Created by", width: 130, text: function (r) { return page.creator(r) } },
                   { title: "Branches", width: 150, text: function (r) { return Theme.many((r.destinations || []).length, "destination") } }]
            now: function (r) { return [r.st[0], r.st[1]] }
            showEmpty: page.flows.length === 0
            emptyIcon: "branches"
            emptyTitle: "No flows yet"
            emptyText: "A flow copies files one way, from one machine to others."
            emptyAct: "New flow"
            onEmptyAction: Nav.go("flows", "new")
        }
        SidePanel {
            width: (parent.width - 14) * 4 / 12
            readonly property var f: page.cur
            readonly property var paused: f ? (f.destinations || []).filter(function (d) { return d.paused_reason }) : []
            showEmpty: f === null
            emptyIcon: "branches"
            emptyText: "Pick a flow in the list."
            title: f ? f.name : ""
            sub: f && page.sel === f.key ? "the one you picked" : "the most recent · click another"
            facts: f ? [["Created by", page.creator(f)],
                        ["Now", f.st[0], f.st[1] === "bad" ? Theme.crit : f.st[1] === "good" ? Theme.ok : Theme.text4, false, true],
                        ["Last copy", page.lastCopy(f) ? Time.atDay(page.lastCopy(f)) : "—"],
                        ["From", f.source_hostname + " " + f.source_path, null, true],
                        ["To", (f.destinations || []).map(function (d) { return (d.destination_hostname || "storage") + " " + d.destination_path }).join("\n"), null, true],
                        ["Along the way", page.steps.length ? page.steps.map(function (s) { return s.op }).join(", ") : "Copied as they are"]] : []
            actions: [
                Btn { text: page.cur && page.cur.status === "paused" ? "Resume" : "Pause"; visible: page.cur !== null && page.cur.status !== "inactive"
                      onClicked: falcon.call(page.cur.status === "paused" ? "flow.resume" : "flow.pause", { flow_id: page.cur.id }, function (ok, r) {
                          if (!ok) { Msg.failed(r.message || "Not changed"); return } Msg.ok(page.cur.status === "paused" ? "Resumed" : "Paused"); page.load() }) },
                Btn { kind: "primary"; iconName: "edit"; text: "Edit"; enabled: page.cur !== null && (Nav.boss || page.cur.created_by_account_id === falcon.accountId)
                      tip: page.cur && !(Nav.boss || page.cur.created_by_account_id === falcon.accountId) ? "Only whoever made it, or the Super User, can change it" : ""
                      onClicked: Nav.go("flows", "edit-" + page.cur.id) }
            ]
            Rectangle {
                visible: page.cur !== null && (page.cur.destinations || []).some(function (d) { return d.paused_reason })
                width: parent.width
                height: pc.height + 24
                radius: Theme.radius
                color: Theme.alpha(Theme.crit, 0.09)
                border.width: 1
                border.color: Theme.alpha(Theme.crit, 0.35)
                Column {
                    id: pc
                    x: 12; y: 12
                    width: parent.width - 24
                    spacing: 8
                    Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; font.pixelSize: 12
                          text: page.cur ? (page.cur.destinations || []).filter(function (d) { return d.paused_reason }).map(function (d) { return d.suggestion || ("The branch to " + d.destination_path + " paused.") }).join(" ") + " Files queue; nothing is lost." : "" }
                    Row { spacing: 6
                          Btn { small: true; text: "Resume the flow"; onClicked: falcon.call("flow.resume", { flow_id: page.cur.id }, function (ok, r) { if (!ok) { Msg.failed(r.message || "Not resumed"); return } Msg.ok("Retrying"); page.load() }) } }
                }
            }
        }
    }

    Panel {
        visible: page.cur !== null
        width: parent.width
        title: page.cur ? page.cur.name : ""
        sub: "the flow drawn · the same flow as on the right"
        Column {
            width: parent.width
            spacing: 8
            FlowPreview {
                width: parent.width
                srcs: page.cur ? [{ host: page.cur.source_hostname, path: page.cur.source_path }] : []
                stages: page.steps
                dests: page.cur ? (page.cur.destinations || []).map(function (d) {
                    return { host: d.destination_hostname || "storage", path: d.destination_path, ask: page.cur.consent_status === "pending", bad: !!d.paused_reason } }) : []
            }
            Row {
                spacing: 14
                Row { spacing: 6; Rectangle { width: 10; height: 2; color: Theme.ser2; anchors.verticalCenter: parent.verticalCenter } Txt { text: "copying"; color: Theme.text3; font.pixelSize: 12 } }
                Txt { text: page.steps.length ? Theme.many(page.steps.length, "step") + " along the way: " + page.steps.map(function (s) { return s.op }).join(", ") : "copied as they are"; color: Theme.text3; font.pixelSize: 12 }
                Row { visible: page.cur !== null && (page.cur.destinations || []).some(function (d) { return d.paused_reason }); spacing: 6
                      Rectangle { width: 10; height: 2; color: Theme.crit; anchors.verticalCenter: parent.verticalCenter } Txt { text: "branch paused"; color: Theme.text3; font.pixelSize: 12 } }
                Row { visible: page.cur !== null && page.cur.consent_status === "pending"; spacing: 6
                      Rectangle { width: 10; height: 2; color: Theme.med; anchors.verticalCenter: parent.verticalCenter } Txt { text: "waiting for someone to agree"; color: Theme.text3; font.pixelSize: 12 } }
            }
        }
    }

    Panel {
        visible: page.cur !== null
        width: parent.width
        flush: true
        title: "Sync log"
        sub: page.cur ? "latest · " + page.cur.name : ""
        Column {
            width: parent.width
            Rectangle {
                width: parent.width; height: 32; color: "transparent"
                Row { x: 14; anchors.verticalCenter: parent.verticalCenter
                      Txt { width: 70; text: "Time"; color: Theme.text3; font.pixelSize: 12; font.weight: Font.Medium }
                      Txt { width: (page.w - 100) * 0.4; text: "File"; color: Theme.text3; font.pixelSize: 12; font.weight: Font.Medium }
                      Txt { width: (page.w - 100) * 0.35; text: "Destination"; color: Theme.text3; font.pixelSize: 12; font.weight: Font.Medium }
                      Txt { width: (page.w - 100) * 0.25; text: "Result"; color: Theme.text3; font.pixelSize: 12; font.weight: Font.Medium } }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
            }
            Txt { visible: page.log.length === 0; x: 14; topPadding: 14; bottomPadding: 14; text: "Nothing copied yet."; color: Theme.text3 }
            Repeater {
                model: page.log.slice(0, 10)
                Rectangle {
                    required property var modelData
                    width: parent.width; height: 36; color: "transparent"
                    Row {
                        x: 14
                        anchors.verticalCenter: parent.verticalCenter
                        Txt { width: 70; text: Time.hhmm(modelData.occurred_at); mono: true; color: Theme.text3 }
                        Txt { width: (page.w - 100) * 0.4; text: modelData.filename || modelData.file_path || modelData.path || "—"; mono: true }
                        Txt { width: (page.w - 100) * 0.35; text: modelData.destination_path || ""; mono: true }
                        Txt { width: (page.w - 100) * 0.25; text: modelData.result || modelData.outcome || modelData.status || ""
                              color: /conflict/i.test(modelData.result || "") ? Theme.med : /queued|fail/i.test(modelData.result || "") ? Theme.crit : Theme.text }
                    }
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                }
            }
        }
    }
}
