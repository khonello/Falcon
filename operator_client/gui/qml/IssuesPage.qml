import QtQuick
import "."

// ISSUES (an Admin's console). Typed: a type fixes the possible resolutions, the issue's own details
// fill them in, and a few options appear only in certain situations (an offline machine, nobody
// signed in). The list worst first; the issue beside it with "What to do"; its timeline under both.
//
// When the Engine keeps issues (issues.list), an issue's meaning, facts, options and timeline are its answer
// to issues.get, and a choice is issues.act; without it, they are read here and a choice it cannot make
// says so on the button.
Page {
    id: page
    objectName: "issuesView"

    readonly property var preset0: Nav.take("issues")
    property string tf: preset0 && preset0.type ? preset0.type : "all"
    property string hf: preset0 && preset0.host ? preset0.host : ""
    property string sel: Nav.sub ? String(Nav.sub) : ""
    property var pick: ({})
    property var input: ({})
    property var done: ({})
    property string tab: "tl"
    property var audit: []
    property var det: null                 // issues.get for the issue on the right
    property string pv: ""                 // the pick, for an option that needs one

    function loadDet() {
        if (!it || it.iid === undefined) { det = null; return }
        var id = it.iid
        falcon.call("issues.get", { issue_id: id }, function (ok, r) { if (ok && page.it && page.it.iid === id) page.det = r })
    }
    onItChanged: { pv = ""; if (!it || !det || !det.issue || det.issue.id !== it.iid) { det = null; loadDet() } }
    readonly property var keyIcon: ({ ask: "message", "delete": "delete", allow: "safety", idle: "clock", now: "reload", wait: "clock", exclude: "stop",
                                      accept: "checkcircle", reverse: "undo", remind: "bell", dest: "branches", withdraw: "close", enter: "login", look: "login" })

    Component.onCompleted: Kinds.load({ limit: 500 }, function (es) { page.audit = es })

    readonly property var types: ({
        file: { label: "Restricted file", icon: "fileprotect", from: "File index" },
        offline: { label: "Not checking in", icon: "disconnect", from: "Connections" },
        help: { label: "Help request", icon: "bell", from: "Assistance" },
        deviation: { label: "Deviation", icon: "warn", from: "Deviation log" },
        update: { label: "Stuck update", icon: "cloudsync", from: "Rollout" },
        flow: { label: "Flow blocked", icon: "branches", from: "Flows" }
    })
    readonly property var rows: Fleet.issues.filter(function (i) {
        return (tf === "all" || i.type === tf) && (hf === "" || i.host === hf)
            && (i.title + " " + i.subject + " " + i.host).toLowerCase().indexOf(list.query.toLowerCase()) >= 0
    })
    readonly property var it: { for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; return rows.length ? rows[0] : null }
    readonly property var m: it ? Fleet.byHost[it.host] : null
    readonly property var play: !it ? null : it.iid === undefined ? build(it, m)
        : det && det.issue && det.issue.id === it.iid ? { lead: det.lead, facts: det.facts || [], why: det.why || [],
              options: (det.options || []).map(function (o) { return Object.assign({ icon: page.keyIcon[o.key] || "right", waits: o.done === "Waiting" }, o) }) } : null
    readonly property var opt: {
        if (!play) return null
        var k = pick[it.id]
        for (var i = 0; i < play.options.length; i++) if (play.options[i].key === k) return play.options[i]
        return play.options[0]
    }
    readonly property string val: it && opt ? (input[it.id + opt.key] || "") : ""
    readonly property string missing: !opt ? "" : opt.cannot ? "" : (opt.need === "reason" || opt.need === "message") && val.trim() === ""
                                      ? (opt.need === "reason" ? "Write a reason first." : "Write a message first.")
                                      : opt.need === "pick" && pv === "" ? (opt.hint || "Pick one first.") : ""
    function late(i) { if (i.past !== undefined) return i.past; return i.at && (Time.now - Time.ms(i.at)) / 3600000 > (i.type === "file" ? 1 : i.type === "help" ? 1 : 24) }

    // what can be done, by type and situation
    function build(i, mm) {
        var online = mm && mm.online, user = mm ? mm.user : ""
        if (i.type === "file") return {
            lead: "A copy of a file marked restricted is on " + i.host + ". It may only be where it was marked, so nowhere else may have it.",
            facts: [["File", i.subject], ["Found on", i.host], ["Found", Time.atDay(i.at)], ["Severity", Fleet.sevWord(i.sev)]],
            why: user ? [] : ["Nobody is signed in, so there is nobody to tell."],
            options: (user && online ? [{ key: "ask", icon: "message", title: "Ask " + user + " to delete it", desc: user + " sees which file and why. The issue closes on its own when the copy is gone.", verb: "Ask", cannot: "The Engine cannot send this request yet" }] : [])
                .concat([{ key: "delete", icon: "delete", title: "Delete this copy", desc: "Deletes it from " + i.host + " only. The original is not touched.", verb: "Delete copy", danger: true, cannot: "The Engine cannot delete a copy yet" },
                         { key: "allow", icon: "safety", title: "Allow it on " + i.host + " too", desc: "Marks it dealt with. If the copy is still there, the next file event flags it again.", verb: "Allow it", need: "reason" }])
        }
        if (i.type === "help") return {
            lead: (user || "Someone") + " asked for help and nobody has answered. A ping carries no message; answering opens a channel.",
            facts: [["From", (user || "Someone") + " on " + i.host], ["Pinged", i.subject], ["Waiting", Time.age(i.at)]],
            why: online ? [] : [i.host + " is offline, so you cannot enter it."],
            options: [{ key: "answer", icon: "message", title: "Answer " + (user || "them"), desc: "Opens a message channel. Only you can close it.", verb: "Send", need: "message" }]
                .concat(online ? [{ key: "enter", icon: "login", title: "Enter " + i.host + " and look yourself", desc: (user || "Whoever is signed in") + " is locked out while you are in. You get 30 minutes.", verb: "Enter " + i.host }] : [])
                .concat([{ key: "handoff", icon: "team", title: "Ask an Admin from another department", desc: "Help across departments. " + (user || "They") + " has to accept it before they can see anything.", verb: "Ask", cannot: "Not from here yet: the worker asks for assisted access" }])
        }
        if (i.type === "deviation") return {
            lead: i.host + " presented something that does not match what it was registered with.",
            facts: [["What", i.title], ["Seen", Time.atDay(i.at)]].concat(i.ref && i.ref.detail ? [["Registered as", i.ref.detail.expected || "—"], ["Presented", i.ref.detail.presented || "—"]] : []),
            why: online ? [] : [i.host + " is offline, so you cannot look into it from inside."],
            options: (online ? [{ key: "look", icon: "login", title: "Look into it first", desc: "Enter " + i.host + " and check who changed it." + (user ? " " + user + " is locked out while you are in." : ""), verb: "Enter " + i.host }] : [])
                .concat([{ key: "accept", icon: "checkcircle", title: "Accept what it presented", desc: "Registers the machine with its new name and pins its certificate.", verb: "Accept", cannot: "The Engine cannot accept a deviation yet" },
                         { key: "reverse", icon: "undo", title: "Put it back", desc: "A new certificate is sent the next time the machine checks in.", verb: "Put it back", cannot: "The Engine cannot do this yet" }])
        }
        return {
            lead: i.host + " is on " + i.subject.split(" → ")[0] + " and should be on " + (Fleet.version || "the current version") + ".",
            facts: [["Running", i.ref && i.ref.version ? i.ref.version : "an older version"], ["Should run", Fleet.version || "—"],
                    ["Attempts", i.ref ? String(i.ref.failures || 0) + (i.ref.last_attempt_at ? ", last " + Time.atDay(i.ref.last_attempt_at) : "") : "—"]]
                    .concat(!online ? [["Offline since", mm && mm.seen ? Time.atDay(mm.seen) : "—"]] : []),
            why: online ? [] : [i.host + " is offline, so it can only retry when it is back."],
            options: (online ? [{ key: "idle", icon: "clock", title: "Retry when it is idle", desc: "The default. The next idle window is usually after the working day.", verb: "Keep this", waits: true },
                                { key: "now", icon: "reload", title: "Retry now", desc: (user || "Whoever is signed in") + " may see a restart prompt.", verb: "Retry now", cannot: "The Engine retries on its own schedule; it cannot be told to now" }]
                             : [{ key: "wait", icon: "clock", title: "Retry when it is back online", desc: "The update runs as soon as " + i.host + " checks in again.", verb: "Keep waiting", waits: true }])
                .concat([{ key: "exclude", icon: "stop", title: "Leave it out of the next version's gate", desc: "Only the Super User approves versions, so this asks them.", verb: "Ask them", need: "reason", cannot: "The Engine has no request for this yet" }])
        }
    }

    Confirm { id: confirm; page: page }
    function act() {
        var i = it, o = opt, v = val.trim()
        if (i.iid !== undefined) {
            var pl = { issue_id: i.iid, key: o.key }
            if (o.need === "reason") pl.reason = v
            if (o.need === "message") pl.message = v
            if (o.need === "pick") pl.pick = pv
            falcon.call("issues.act", pl, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Not done"); return }
                Msg.ok((r.issue && r.issue.state === "resolved" ? "Resolved" : "Waiting") + " · recorded"); page.det = null; page.loadDet(); Fleet.refresh()
            })
            return
        }
        if (o.key === "enter" || o.key === "look") {
            confirm.ask({ title: "Enter " + i.host + "?", text: (m && m.user ? m.user + " is signed in and is locked out while you are in. " : "") + "You get 30 minutes, and can extend them.", ok: "Enter" },
                        function () { falcon.call("hierarchy.traverse", { pc_id: i.pc_id, force: false }, function (ok, r) {
                            if (!ok) { Msg.failed(r && r.message ? r.message : "Could not enter"); return }
                            page.mark(i, "Open", "Entered " + i.host); Msg.ok("You are in " + i.host)
                        }) })
            return
        }
        if (o.key === "allow")
            falcon.call("resource.resolve", { violation_id: i.ref.violation_id, reason: v }, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Not done"); return }
                page.mark(i, "Resolved", "Allowed " + i.subject + " on " + i.host + ": “" + v + "”"); Fleet.refresh(); Msg.ok("Allowed · recorded")
            })
        else if (o.key === "answer")
            falcon.call("assistance.respond", { ping_id: i.ref.id }, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Not answered"); return }
                falcon.call("assistance.message", { channel_id: r.channel_id, text: v }, function (ok2, r2) {
                    page.mark(i, "Resolved", "Answered; channel open")
                    Msg.ok(ok2 ? "Answered · the channel is open" : "The channel is open · it is their turn to write first")
                    Fleet.refresh()
                })
            })
        else if (o.waits) { page.mark(i, "Waiting", o.title); Msg.ok("Left to retry") }
    }
    function mark(i, status, how) { var d = Object.assign({}, done); d[i.id] = { status: status, how: how, at: Date.now() }; done = d }

    Strip {
        width: parent.width
        items: [
            { label: "Open", value: Theme.fmt(Fleet.issues.length), delta: Fleet.issues.some(function (i) { return i.sev === "critical" }) ? Fleet.issues.filter(function (i) { return i.sev === "critical" }).length + " critical" : "nothing critical",
              dc: Fleet.issues.some(function (i) { return i.sev === "critical" }) ? Theme.crit : undefined },
            { label: "Waiting", value: Fleet.summary ? Theme.fmt(Fleet.summary.waiting) : Theme.fmt(Object.keys(page.done).filter(function (k) { return page.done[k].status === "Waiting" }).length), delta: "on a step already taken" },
            { label: "Past target", value: Theme.fmt(Fleet.issues.filter(page.late).length), delta: Fleet.issues.some(page.late) ? "older than the time they should take" : "all within their target",
              dc: Fleet.issues.some(page.late) ? Theme.crit : undefined },
            { label: "Done today", value: Fleet.summary ? Theme.fmt(Fleet.summary.done_today) : Theme.fmt(Object.keys(page.done).filter(function (k) { return page.done[k].status === "Resolved" }).length), delta: "resolved here today" }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            title: "Open issues"
            sub: page.tf !== "all" || page.hf !== "" ? Theme.fmt(page.rows.length) + (page.tf !== "all" ? " · " + page.types[page.tf].label.toLowerCase() : "") + (page.hf ? " · on " + page.hf : "")
                                                     : "worst first · click one to see it on the right"
            subLink: page.tf !== "all" || page.hf !== "" ? "every open issue" : ""
            onSubLinkClicked: { page.tf = "all"; page.hf = "" }
            placeholder: "Find an issue, file or machine"
            tools: Select {
                width: 150
                small: true
                popupWidth: 200
                value: page.tf
                options: [{ value: "all", label: "Every type" }].concat(Object.keys(page.types).map(function (k) {
                    return { value: k, label: page.types[k].label + " · " + Fleet.issues.filter(function (i) { return i.type === k }).length }
                }))
                onPicked: function (v) { page.tf = v }
            }
            rows: page.rows
            pick: page.it ? page.it.id : null
            onPicked: function (k) { page.sel = k }
            icon: function (i) { return page.types[i.type] ? page.types[i.type].icon : "alert" }
            nameTitle: "Issue"
            nameText: function (i) { return i.title }
            nameLine: function (i) { return (i.subject ? i.subject + " · " : "") + i.host }
            cols: [
                { title: "Severity", width: 100, text: function (i) { return Fleet.sevWord(i.sev) } },
                { title: "Owner", width: 110, text: function (i) { return i.owner ? (i.owner.you ? "You" : i.owner.name) : i.escalated ? "Super User" : "Nobody" } },
                { title: "Age", width: 90, text: function (i) { return i.at ? Time.age(i.at) : "—" } }
            ]
            now: function (i) {
                var d = page.done[i.id]
                if (i.state === "waiting") return [i.label || "Waiting", "wait"]
                return d ? (d.status === "Resolved" ? ["Done", "good"] : ["Waiting", "wait"]) : page.late(i) ? ["Past its target", "bad"] : ["Open", "wait"]
            }
            showEmpty: Fleet.loaded && Fleet.issues.length === 0
            emptyIcon: "check"
            emptyTitle: "Nothing is open in this department"
            emptyText: "Restricted copies, unanswered pings, deviations and stuck updates appear here, worst first."
        }
        SidePanel {
            id: side
            width: (parent.width - 14) * 4 / 12
            showEmpty: page.it === null
            emptyIcon: "check"
            emptyTitle: "Nothing open"
            emptyText: "Pick an issue in the list."
            title: page.it ? page.it.title : ""
            sub: page.it && page.sel === page.it.id ? "the one you picked" : "the worst open · click another"
            actions: [
                Btn { visible: page.it !== null && page.it.iid !== undefined && falcon.role === "admin" && !page.it.escalated; text: "Send it up"
                      onClicked: falcon.call("issues.escalate", { issue_id: page.it.iid }, function (ok, r) { if (ok) { Msg.ok("Sent up to the Super User"); Fleet.refresh(); page.loadDet() } else Msg.failed(r.message || "Not sent") }) },
                Btn { text: page.it ? "Open " + page.it.host + "'s page →" : ""; onClicked: Nav.go("machines", page.it.host) }
            ]

            Column {
                width: parent.width
                spacing: 8
                visible: page.it !== null
                Row {
                    spacing: 8
                    St { square: true; text: page.it ? Fleet.sevWord(page.it.sev) : ""; c: page.it ? Fleet.sevColor(page.it.sev) : Theme.text4 }
                    Tag { text: page.it ? page.types[page.it.type].label : ""; iconName: page.it ? page.types[page.it.type].icon : "" }
                    St { readonly property var d: page.it ? page.done[page.it.id] : null
                         text: page.it && page.it.label ? page.it.label : d ? d.status : "Open"
                         c: page.it && page.it.state === "waiting" ? Theme.ser1 : d ? (d.status === "Resolved" ? Theme.ok : Theme.ser1) : Theme.text2 }
                }
                Txt {
                    width: parent.width
                    color: Theme.text2
                    textFormat: Text.RichText
                    wrapMode: Text.WordWrap
                    text: page.it ? "<span style='font-family:" + Theme.mono + "'>" + (page.it.subject || "") + "</span> on <span style='font-family:" + Theme.mono + "'>" + page.it.host + "</span>"
                                    + "<span style='color:" + Theme.text3 + "'> · " + (page.it.at ? Time.age(page.it.at) + " old" : "") + "</span>"
                                    + (page.late(page.it) ? "<span style='color:" + Theme.crit + "'> · past its target</span>" : "") : ""
                }
                // who has it: take it, give it to another Admin of the department, or hand it back (issues.assign)
                Row {
                    visible: page.it !== null && page.it.iid !== undefined
                    spacing: 8
                    Txt { text: "Owner"; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
                    Select {
                        width: 170; small: true
                        enabled: !(page.it && page.it.escalated)
                        value: page.it && page.it.owner ? page.it.owner.account_id : 0
                        options: [{ value: 0, label: page.it && page.it.escalated ? "The Super User" : "Nobody yet" }].concat(
                                 (Fleet.dept(falcon.departmentId) || { admins: [] }).admins.map(function (a) { return { value: a.account_id, label: a.account_id === falcon.accountId ? "You" : a.name } }))
                        onPicked: function (v) {
                            var pl = { issue_id: page.it.iid }; pl.account_id = v === 0 ? null : v
                            falcon.call("issues.assign", pl, function (ok, r) {
                                if (!ok) { Msg.failed(r && r.message ? r.message : "Not changed"); return }
                                Msg.ok(v === 0 ? "Handed back" : v === falcon.accountId ? "It is yours" : "Given to " + Fleet.adminName(v)); Fleet.refresh(); page.loadDet()
                            })
                        }
                    }
                }
            }

            // resolved: what was done, and Reopen
            Rectangle {
                readonly property var d: page.it ? page.done[page.it.id] : null
                visible: d !== null && d !== undefined && d.status === "Resolved"
                width: parent.width
                height: visible ? 52 : 0
                radius: Theme.radius
                color: Theme.mix(Theme.ok, Theme.surface, 0.08)
                Row {
                    x: 12
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    Icon { name: "checkcircle"; size: 18; color: Theme.ok; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: "Resolved by you"; font.weight: Font.DemiBold; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: parent.parent.d ? "· " + parent.parent.d.how : ""; color: Theme.text2; width: side.width - 260; anchors.verticalCenter: parent.verticalCenter }
                }
                Btn { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; small: true; text: "Reopen"
                      onClicked: { var x = Object.assign({}, page.done); delete x[page.it.id]; page.done = x } }
            }

            // what to do
            Column {
                readonly property var d: page.it ? page.done[page.it.id] : null
                visible: page.it !== null && !(!!d && d.status === "Resolved")
                width: parent.width
                spacing: 14
                Txt { text: "WHAT TO DO"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Txt { visible: !!parent.d && parent.d.status === "Waiting"; text: "Waiting on the last step you took; you can still change course."; color: Theme.ser1; font.pixelSize: 12 }
                Txt { width: parent.width; text: page.play ? page.play.lead : ""; color: Theme.text2; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                Grid {
                    width: parent.width
                    columns: 2
                    columnSpacing: 20
                    rowSpacing: 10
                    Repeater {
                        model: page.play ? page.play.facts : []
                        Column {
                            required property var modelData
                            width: (side.width - 52) / 2
                            Txt { text: modelData[0]; color: Theme.text3; font.pixelSize: 12 }
                            Txt { text: modelData[1]; font.weight: Font.Medium; font.pixelSize: 12; width: parent.width; wrapMode: Text.Wrap; elide: Text.ElideNone }
                        }
                    }
                }
                Column {
                    width: parent.width
                    spacing: 8
                    Repeater {
                        model: page.play ? page.play.options : []
                        Choice {
                            required property var modelData
                            width: parent.width
                            on: page.opt !== null && modelData.key === page.opt.key
                            icon: modelData.icon
                            title: modelData.title
                            desc: modelData.desc
                            onClicked: { var p = Object.assign({}, page.pick); p[page.it.id] = modelData.key; page.pick = p }
                        }
                    }
                }
                Txt { visible: page.play !== null && page.play.why.length > 0; text: page.play ? page.play.why.join(" ") : ""; color: Theme.text3; font.pixelSize: 12; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                Select {
                    visible: page.opt !== null && page.opt.need === "pick"
                    width: parent.width
                    placeholder: page.opt && page.opt.hint ? page.opt.hint : "Pick one"
                    value: page.pv === "" ? null : page.pv
                    options: page.opt && page.opt.pick ? page.opt.pick : []
                    onPicked: function (v) { page.pv = String(v) }
                }
                TextArea2 {
                    visible: page.opt !== null && (page.opt.need === "reason" || page.opt.need === "message") && !page.opt.cannot
                    width: parent.width
                    placeholder: page.opt && page.opt.need === "message" ? "Write to " + (page.m && page.m.user ? page.m.user : "them") : "Why? This is recorded with the decision."
                    text: page.val
                    onEdited: function (t) { var x = Object.assign({}, page.input); x[page.it.id + page.opt.key] = t; page.input = x }
                }
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Item {
                    width: parent.width
                    height: 30
                    Txt {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - go.width - 12
                        color: Theme.text3
                        font.pixelSize: 12
                        text: !page.opt ? "" : page.opt.cannot ? page.opt.cannot + "." : page.missing !== "" ? page.missing
                              : page.opt.waits ? "The issue waits until this finishes." : "This resolves the issue."
                    }
                    Btn {
                        id: go
                        anchors.right: parent.right
                        kind: "primary"
                        danger: page.opt !== null && !!page.opt.danger
                        text: page.opt ? page.opt.verb : ""
                        enabled: page.opt !== null && !page.opt.cannot && page.missing === ""
                        onClicked: page.act()
                    }
                }
            }
        }
    }

    Panel {
        visible: page.it !== null
        width: parent.width
        title: page.it ? page.it.title : ""
        sub: "its timeline and details · the same issue as on the right"
        Column {
            width: parent.width
            spacing: 10
            Tabs { width: parent.width; tabs: [{ key: "tl", label: "Timeline" }, { key: "dt", label: "Details" }]; current: page.tab; onPicked: function (k) { page.tab = k } }
            Column {
                visible: page.tab === "tl"
                width: parent.width
                readonly property var evs: page.det && page.det.timeline ? page.det.timeline.map(function (e) { return { t: Time.ms(e.at), actor: e.who, what: e.what, kind: e.kind } })
                                         : page.it ? page.audit.filter(function (e) { return e.host === page.it.host && Math.abs(e.t - Time.ms(page.it.at)) < 2 * 3600000 }).slice(0, 6).reverse() : []
                Txt { visible: parent.evs.length === 0; text: page.it ? "Nothing recorded on " + page.it.host + " around it yet." : ""; color: Theme.text3; font.pixelSize: 12; topPadding: 6 }
                Repeater {
                    model: parent.evs
                    Item {
                        required property var modelData
                        width: parent.width; height: 28
                        Txt { width: 62; anchors.verticalCenter: parent.verticalCenter; mono: true; color: Theme.text3; font.pixelSize: 12; text: Time.hhmm(modelData.t) }
                        Rectangle { x: 66; width: 7; height: 7; radius: 4; color: Kinds.color(modelData.kind); anchors.verticalCenter: parent.verticalCenter }
                        Txt { x: 82; width: parent.width - 82; anchors.verticalCenter: parent.verticalCenter; textFormat: Text.RichText
                              text: "<span style='font-weight:500'>" + modelData.actor + "</span> <span style='color:" + Theme.text2 + "'>" + modelData.what + "</span>" }
                    }
                }
            }
            Grid {
                visible: page.tab === "dt"
                width: parent.width
                columns: Math.max(1, Math.floor(width / 170))
                columnSpacing: 20
                rowSpacing: 12
                Repeater {
                    model: page.it ? [["Detected", Time.atDay(page.it.at)], ["Department", page.m ? page.m.deptName : "—"], ["Type", page.types[page.it.type].label],
                                      ["Comes from", page.types[page.it.type].from], ["ID", page.it.id]] : []
                    Column {
                        required property var modelData
                        width: 150
                        Txt { text: modelData[0]; color: Theme.text3; font.pixelSize: 12 }
                        Txt { text: modelData[1]; font.weight: Font.Medium; width: parent.width }
                    }
                }
            }
        }
    }
}
