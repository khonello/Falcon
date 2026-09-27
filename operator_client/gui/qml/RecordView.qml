import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// RECORD (board RC05), the Super User's: past and present, a pair over three.
//
//   top      who was where today -- the day drawn as the Overview and a department draw it (labelled lanes, an
//            hour axis, a legend), with the entries written out beside it as its key
//   bottom   the trail in words (newest first), reports with their Views (who addressed what -- the Super User's
//            alone, never routed), and what is still out of place
//
// Nothing here changes anything: it is what happened.
Item {
    id: root

    property var tree: []
    property var sessions: []
    property var entries: []
    property var reports: []
    property var views: []
    property var violations: []
    property var deviations: []
    property string clock: ""

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function (ok, r) { if (ok) root.tree = r.departments })
        falcon.call("hierarchy.sessions_today", { hours: 24 }, function (ok, r) { if (ok) root.sessions = r.sessions })
        falcon.call("audit.recent", { limit: 200 }, function (ok, r) { if (ok) root.entries = r.entries })
        falcon.call("reports.list", {}, function (ok, r) { if (ok) root.reports = r.reports })
        falcon.call("reports.addressed_view", {}, function (ok, r) { if (ok) root.views = r.addressed })
        falcon.call("resource.violations", {}, function (ok, r) { if (ok) root.violations = r.violations })
        falcon.call("audit.deviations", {}, function (ok, r) { if (ok) root.deviations = r.deviations })
    }
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onPushReceived(type, p) { if (type.indexOf("session.") === 0 || type.indexOf("report.") === 0) root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    onVisibleChanged: if (visible) refresh()

    readonly property int me: falcon ? falcon.accountId : 0
    function timeOf(iso) { return iso ? Qt.formatDateTime(new Date(iso), "HH:mm") : "" }
    function dayTime(iso) {
        if (!iso) return ""
        var d = new Date(iso)
        return d.toDateString() === new Date().toDateString() ? timeOf(iso) : Qt.formatDateTime(d, "ddd HH:mm")
    }
    function minutes(a, b) { return Math.max(1, Math.round((new Date(b || Date.now()) - new Date(a)) / 60000)) }
    function deptName(id) { for (var i = 0; i < tree.length; i++) if (tree[i].department_id === id) return tree[i].name; return "" }

    // --- who was where ------------------------------------------------------------------------------------
    readonly property var lanes: {
        var out = []
        for (var i = 0; i < tree.length; i++)
            for (var j = 0; j < tree[i].workers.length; j++) {
                var w = tree[i].workers[j]
                out.push({ name: w.hostname || w.name, blocks: Day.blocksFor(sessions, w.pc_id) })
            }
        if (out.length <= 9) return out
        // past nine lanes the bars get too thin to read: keep the machines someone else entered, fold the rest
        var entered = out.filter(function (l) { return l.blocks.some(function (b) { return b.state !== "native" }) })
        var rest = out.length - entered.length
        if (entered.length > 9) entered = entered.slice(0, 8)
        if (rest > 0) entered.push({ name: rest + " more", blocks: [], quiet: true })
        return entered
    }
    readonly property int quiet: {
        var n = 0
        for (var i = 0; i < tree.length; i++)
            for (var j = 0; j < tree[i].workers.length; j++) if (Day.blocksFor(sessions, tree[i].workers[j].pc_id).length === 0) n++
        return n
    }
    readonly property real fromHour: {
        var lo = NaN
        for (var i = 0; i < sessions.length; i++) { var h = Day.hoursOf(sessions[i].entered_at); if (!isNaN(h)) lo = isNaN(lo) ? h : Math.min(lo, h) }
        return isNaN(lo) ? Math.max(0, Math.floor(Day.nowHours() - 4)) : Math.max(0, Math.floor(lo))
    }
    readonly property real toHour: Math.min(24, Math.ceil(Day.nowHours() + 0.5))

    // entries: every session that was not someone at their own machine
    readonly property var enteredToday: {
        var out = []
        for (var i = 0; i < sessions.length; i++) {
            var s = sessions[i]
            if (s.occupied_via === "native") continue
            var mine = s.occupant_account_id === me
            // who was at the machine when it was entered: the native session that ended as this one began
            var blocked = sessions.filter(function (o) {
                return o.pc_id === s.pc_id && o.occupied_via === "native" && o.ended_at
                       && Math.abs(new Date(o.ended_at) - new Date(s.entered_at)) < 120000
            })[0]
            var assisted = s.occupied_via === "assisted_access"
            out.push({
                initials: mine ? "SU" : Theme.initials(s.occupant_name || ""),
                title: assisted ? (s.occupant_name || "Someone") + " is helping " + (deptName(s.department_id) || s.hostname)
                                : (mine ? "You" : s.occupant_name || "Someone") + " entered " + s.hostname,
                line: timeOf(s.entered_at) + (s.ended_at ? " – " + timeOf(s.ended_at) : "") + (assisted ? " · by consent"
                      : blocked ? " · " + blocked.occupant_name + " was blocked" : ""),
                word: s.ended_at ? minutes(s.entered_at, s.ended_at) + " min" : "now",
                tone: mine ? "danger" : assisted ? "accent" : "warn",
                at: s.entered_at, open: !s.ended_at, mine: mine
            })
        }
        return out.sort(function (a, b) { return String(b.at).localeCompare(String(a.at)) })
    }
    readonly property int youEntered: enteredToday.filter(function (e) { return e.mine }).length

    // --- the trail, in words ------------------------------------------------------------------------------
    // each kind of entry as [icon, what someone did, what happened when no one did it]
    readonly property var trailWords: ({
        "session.traversed": ["hierarchy", "entered a machine", "A machine was entered"],
        "session.ended": ["lock", "left a machine", "A session ended"],
        "session.extended": ["clock", "stayed longer on a machine", "A session was extended"],
        "resource.violation": ["shield", "found a file out of place", "A file was found out of place"],
        "resource.violation_resolved": ["check", "marked a file as moved", "A file out of place was moved"],
        "resource.tagged": ["folder", "shelved a file", "A file was shelved"],
        "report.addressed": ["check", "addressed a report", "A report was addressed"],
        "assisted_access.accepted": ["assistance", "began helping another department", "Help across departments began"],
        "assisted_access.closed": ["assistance", "finished helping", "Help across departments ended"],
        "task.created": ["tasks", "gave a task", "A task was given"],
        "task.verified": ["check", "verified a task", "A task was verified"],
        "flow.created": ["flows", "set up a flow", "A flow was set up"],
        "flow.failed": ["warn", "saw a flow fail", "A flow failed"],
        "flow.paused": ["pause", "paused a flow", "A flow paused"],
        "update.approved": ["pulse", "approved a version", "A version was approved"],
        "update.rollout": ["pulse", "started a rollout", "A version began rolling out"],
        "account.created": ["user", "made an account", "An account was made"],
        "account.offboarded": ["user", "closed an account", "An account was closed"],
        "pc.registered": ["monitor", "added a machine", "A machine joined"],
        "department.created": ["dept", "made a department", "A department was made"],
        "report_routing.set": ["reports", "changed where reports go", "Report routing changed"],
        "event.created": ["automation", "made an automation", "An automation was made"],
        "audit.reviewed": ["eye", "reviewed someone's trail", "A trail was reviewed"],
        "assistance.channel_opened": ["assistance", "answered a ping", "A ping was answered"]
    })
    readonly property var trail: entries.filter(function (e) { return !!trailWords[e.action_type] })
        .sort(function (a, b) { return String(b.occurred_at).localeCompare(String(a.occurred_at)) })
        .slice(0, 40).map(function (e) {
            var w = trailWords[e.action_type]
            var who = e.actor_account_id === me ? "You" : e.actor_name && e.actor_name !== "engine" ? e.actor_name : ""
            var host = e.detail && e.detail.hostname ? " — " + e.detail.hostname : ""
            return { at: e.occurred_at, icon: w[0], text: (who ? who + " " + w[1] : w[2]) + host,
                     tone: /violation$|failed/.test(e.action_type) ? "danger" : "" }
        })

    // --- reports and their Views --------------------------------------------------------------------------
    readonly property var kindWords: ({ resource_violation: ["shield", "A file out of place"], flow_failure: ["flows", "A flow failed"],
                                        listener_report: ["eye", "A listener was added"], directory_structure_conflict: ["folder", "Two folders disagree"],
                                        cross_department_assistance: ["dept", "Help across departments"], update_status: ["pulse", "An update fell behind"],
                                        deviation: ["warn", "Something unexpected"] })
    readonly property var reportCards: reports.slice(0, 30).map(function (r) {
        var v = views.filter(function (x) { return x.report_id === r.id })[0]
        var k = kindWords[r.category] || ["bell", r.category]
        return { icon: k[0], title: k[1], open: !v,
                 line: v ? (deptName(v.addressed_by_department_id) || "An Admin") + " · addressed " + dayTime(v.addressed_at)
                         : "raised " + dayTime(r.generated_at) + " · not addressed" }
    }).sort(function (a, b) { return (b.open ? 1 : 0) - (a.open ? 1 : 0) })
    readonly property int openReports: reportCards.filter(function (c) { return c.open }).length

    // --- still out of place -------------------------------------------------------------------------------
    readonly property var deviationWords: ({ hostname_did_not_match_certificate: "A hostname did not match",
                                             account_used_from_unbound_pc: "An account signed in from another machine" })
    readonly property var outOfPlace: violations.map(function (v) {
        return { icon: "file", tone: "danger", title: v.filename,
                 line: String(v.expected_tag || "").replace("worker_dept", "workers").replace(/^./, function (c) { return c.toUpperCase() }) + " · on " + v.hostname }
    }).concat(deviations.filter(function (d) { return !d.resolved_at }).map(function (d) {
        return { icon: "warn", tone: "warn", title: root.deviationWords[d.expectation] || String(d.expectation).replace(/_/g, " "),
                 line: (d.hostname || "noticed " + root.dayTime(d.detected_at)) + " · not addressed" }
    }))

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 22
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 16

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Column {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4
                Txt { text: "Record"; color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                Row {
                    spacing: 12
                    Txt { text: "Record"; color: "#ffffff"; font.pixelSize: Theme.fTitle; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                    Txt { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody
                          color: root.outOfPlace.length ? Theme.warn : Qt.rgba(1, 1, 1, 0.55)
                          text: "past and present" + (root.outOfPlace.length === 0 ? "" : " · " + root.outOfPlace.length
                                + (root.outOfPlace.length === 1 ? " thing still out of place" : " things still out of place")) }
                }
            }
            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: root.clock
                  color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 1
            spacing: 20
            GridCell {
                id: dayCell
                objectName: "recordDay"
                Layout.fillWidth: true
                Layout.preferredWidth: 2
                Layout.fillHeight: true
                topAlign: true
                title: "Who was where, today"
                narration: ({ brief: root.youEntered === 0 ? "" : root.youEntered === 1 ? "you entered one machine" : "you entered " + root.youEntered + " machines",
                              tone: "danger", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 12
                    DayTimeline {
                        width: parent.width
                        laneGap: 6
                        laneHeight: Math.max(11, Math.min(20, (dayCell.room - 70) / Math.max(1, root.lanes.length) - laneGap))
                        lanes: root.lanes
                        fromHour: root.fromHour
                        toHour: root.toHour
                    }
                    Legend {
                        items: [{ label: "At the PC", color: Theme.line2, round: false },
                                { label: "An Admin entered", color: Theme.warn, round: false },
                                { label: "You entered", color: Theme.danger, round: false }]
                        note: root.quiet === 0 ? "" : root.quiet + (root.quiet === 1 ? " machine was never signed in today" : " machines were never signed in today")
                    }
                }
            }
            GridCell {
                id: enteredCell
                objectName: "recordEntered"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                topAlign: true
                title: "Entered today"
                narration: ({ brief: root.enteredToday.length ? String(root.enteredToday.length) : "", tone: "danger",
                              state: root.enteredToday.length ? "ok" : "empty", note: "No one entered another machine",
                              sentence: "Everyone stayed at their own machine today." })
                Column {
                    width: parent.width
                    spacing: 10
                    PagedColumn {
                        width: parent.width
                        height: Math.min(root.enteredToday.length * 68, Math.max(68, enteredCell.room - 40))
                        itemHeight: 59
                        model: root.enteredToday
                        delegate: InfoCard {
                            initials: modelData ? modelData.initials : ""
                            title: modelData ? modelData.title : ""
                            line: modelData ? modelData.line : ""
                            stateWord: modelData ? modelData.word : ""
                            stateTone: modelData ? modelData.tone : ""
                        }
                    }
                    Txt { visible: root.enteredToday.length > 0; text: "Everyone else stayed at their own machine."; color: Theme.faint; font.pixelSize: Theme.fMeta }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 1
            spacing: 20
            GridCell {
                id: trailCell
                objectName: "recordTrail"
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "The trail"
                narration: ({ brief: "newest first", state: root.trail.length ? "ok" : "empty", note: "Nothing yet today" })
                PagedColumn {
                    width: parent.width
                    height: Math.max(66, trailCell.room)
                    itemHeight: 30
                    spacing: 3
                    model: root.trail
                    delegate: Item {
                        property var modelData: null
                        property int index: -1
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
                        Txt { id: tAt; width: 60; anchors.verticalCenter: parent.verticalCenter; monospace: true; color: Theme.faint; font.pixelSize: Theme.fMeta
                              text: parent.modelData ? root.dayTime(parent.modelData.at) : "" }
                        Icon { id: tIcon; anchors.left: tAt.right; anchors.verticalCenter: parent.verticalCenter; size: 14
                               name: parent.modelData ? parent.modelData.icon : "bell"
                               color: parent.modelData && parent.modelData.tone ? Theme.tone(parent.modelData.tone) : Theme.dim }
                        Txt { anchors.left: tIcon.right; anchors.leftMargin: 10; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                              elide: Text.ElideRight; color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold
                              text: parent.modelData ? parent.modelData.text : "" }
                    }
                }
            }
            GridCell {
                id: viewsCell
                objectName: "recordViews"
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "Reports and their Views"
                narration: ({ brief: root.openReports === 0 ? "all addressed" : root.openReports === 1 ? "one still open" : root.openReports + " still open",
                              tone: root.openReports ? "warn" : "ok", state: root.reportCards.length ? "ok" : "empty", note: "No reports yet" })
                Column {
                    width: parent.width
                    spacing: 10
                    PagedColumn {
                        width: parent.width
                        height: Math.min(root.reportCards.length * 67, Math.max(67, viewsCell.room - 40))
                        itemHeight: 58
                        model: root.reportCards
                        delegate: InfoCard {
                            iconName: modelData ? modelData.icon : ""; iconTone: modelData && modelData.open ? "danger" : "ok"
                            title: modelData ? modelData.title : ""
                            line: modelData ? modelData.line : ""
                            stateWord: modelData ? (modelData.open ? "open" : "addressed") : ""
                            stateTone: modelData && modelData.open ? "danger" : ""
                        }
                    }
                    Txt { text: "Who addressed what is yours alone; it is never routed."; color: Theme.faint; font.pixelSize: Theme.fMeta }
                }
            }
            GridCell {
                id: placeCell
                objectName: "recordOutOfPlace"
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "Out of place"
                narration: ({ brief: root.outOfPlace.length ? String(root.outOfPlace.length) : "", tone: "warn",
                              state: root.outOfPlace.length ? "ok" : "empty", note: "Everything is in place" })
                Column {
                    width: parent.width
                    spacing: 10
                    Txt { text: root.outOfPlace.length === 1 ? "One thing is out of place right now." : root.outOfPlace.length + " things are out of place right now."
                          color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                    PagedColumn {
                        width: parent.width
                        height: Math.min(root.outOfPlace.length * 67, Math.max(67, placeCell.room - 40))
                        itemHeight: 58
                        model: root.outOfPlace
                        delegate: InfoCard {
                            iconName: modelData ? modelData.icon : ""; iconTone: modelData ? modelData.tone : ""
                            title: modelData ? modelData.title : ""
                            line: modelData ? modelData.line : ""
                        }
                    }
                }
            }
        }
    }
}
