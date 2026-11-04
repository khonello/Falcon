import QtQuick
import "."

// ISSUES, as the version 1 concept draws it (docs/design/concepts-admin.html, AdminIssuesPage). The situation in a sentence;
// on the left To do (the next step is yours) and Done (you have done your part; each card says what happens next), one card
// per issue, several of one kind under a heading, never inside another card; under them the picked issue's story. On the
// right the picked issue: the same fields for every issue, then what to do.
// Every issue reaches every Admin and is any Admin's to act on: nobody owns one (the user, 2 Nov 2026).
//
// When the Engine keeps issues (issues.list), an issue's meaning, facts, options and timeline are its answer to issues.get,
// and a choice is issues.act; without it, they are read here and a choice it cannot make says so on the button.
Page {
    id: page
    objectName: "issuesView"

    property string sel: { var a = Nav.takeArrive("issues"); return a !== null ? String(a) : Nav.sub ? String(Nav.sub) : "" }
    property var pick: ({})
    property var input: ({})
    property var done: ({})
    property var more: ({})
    property var audit: []
    property var det: null                 // issues.get for the issue on the right
    property string pv: ""                 // the pick, for an option that needs one
    property bool loading: false

    function loadDet() {
        if (!it || it.iid === undefined) { det = null; return }
        var id = it.iid
        falcon.call("issues.get", { issue_id: id }, function (ok, r) { if (ok && page.it && page.it.iid === id) page.det = r })
    }
    // a pick asks the Engine for the issue's story: the story says so for a moment, then pulses once it is there
    onItChanged: { pv = ""; loading = true; ldT.restart(); if (!it || !det || !det.issue || det.issue.id !== it.iid) { det = null; loadDet() } }
    Timer { id: ldT; interval: Theme.loadMs; onTriggered: page.loading = false }
    readonly property var keyIcon: ({ ask: "message", "delete": "delete", allow: "safety", idle: "clock", now: "reload", wait: "clock", exclude: "stop",
                                      accept: "checkcircle", reverse: "undo", remind: "bell", dest: "branches", withdraw: "close", enter: "login", look: "login", answer: "message" })

    Component.onCompleted: Kinds.load({ limit: 500 }, function (es) { page.audit = es })

    readonly property var types: ({
        file: { label: "Restricted file", plural: "Restricted copies", icon: "fileprotect" },
        offline: { label: "Not checking in", plural: "Machines not checking in", icon: "disconnect" },
        help: { label: "Request to talk", plural: "Requests to talk", icon: "message" },
        deviation: { label: "Deviation", plural: "Certificate mismatches", icon: "warn" },
        update: { label: "Stuck update", plural: "Machines behind on the version", icon: "cloudsync" },
        flow: { label: "Flow blocked", plural: "Flows waiting", icon: "branches" },
        component: { label: "Part of the Worker", plural: "Parts of the Worker", icon: "warn" }
    })
    readonly property var all: Fleet.issues
    function late(i) { if (i.past !== undefined) return i.past; return i.at && (Time.now - Time.ms(i.at)) / 3600000 > (i.type === "file" ? 1 : i.type === "help" ? 1 : 24) }
    function isDone(i) { return i.state === "waiting" || i.state === "resolved" || !!done[i.id] }
    // To do: the next step is yours. Done: you have done your part, or it is resolved; once you have acted it is done for
    // you, never "waiting" (the user, 1 Nov 2026).
    readonly property var todo: all.filter(function (i) { return !isDone(i) })
    readonly property var later: all.filter(function (i) { return isDone(i) })
    readonly property var rows: todo.concat(later)          // every issue on the page, in order (what the tests read)
    readonly property var it: {
        var xs = todo.concat(later).concat(all)
        for (var i = 0; i < xs.length; i++) if (xs[i].id === sel) return xs[i]
        return todo.length ? todo[0] : later.length ? later[0] : null
    }
    readonly property var m: it ? Fleet.byHost[it.host] : null
    readonly property var play: !it ? null : it.iid === undefined ? build(it, m)
        : det && det.issue && det.issue.id === it.iid ? { lead: det.lead, facts: det.facts || [], why: det.why || [],
              options: page.withRule(page.withLook((det.options || []).filter(function (o) { return o.key !== "ask" }))      // the concept offers no Ask
                  .map(function (o) { return Object.assign({ icon: page.keyIcon[o.key] || "right", waits: o.done === "Waiting" }, o) })) } : null
    // a deviation can be looked into first, from inside: the concept's first choice
    function withLook(os) {
        if (!it || it.type !== "deviation" || !m || !m.online) return os
        return [{ key: "look", title: "Look into it first", desc: "Enter " + it.host + " and check who changed it." + (m.user ? " " + m.user + " is locked out while you are in." : ""), verb: "Enter " + it.host, done: "Open" }].concat(os)
    }
    // the fix on a card: Delete copy, else the first choice that needs nothing more, else the first
    function primaryOf(os) { return os.filter(function (o) { return o.key === "delete" })[0] || os.filter(function (o) { return !o.need && !o.cannot })[0] || os[0] }
    // where Falcon can do the fix alone, it can be made a rule (issues.act "rule")
    function withRule(os) {
        var p = primaryOf(os)
        if (!p || p.key !== "delete") return os
        return os.concat([{ key: "rule", title: "Delete this every time from now on", verb: "Delete copy, every time",
                            desc: "When a restricted file is copied on any of your machines, Falcon will delete the copy and tell whoever is signed in. This one is fixed now too; you can change or stop it in Automation." }])
    }
    readonly property var opt: {
        if (!play) return null
        var k = pick[it.id]
        for (var i = 0; i < play.options.length; i++) if (play.options[i].key === k) return play.options[i]
        return primaryOf(play.options)
    }
    readonly property string val: it && opt ? (input[it.id + opt.key] || "") : ""
    readonly property string missing: !opt ? "" : opt.cannot ? "" : (opt.need === "reason" || opt.need === "message") && val.trim() === ""
                                      ? (opt.need === "reason" ? "Write a reason first." : "Write a message first.")
                                      : opt.need === "pick" && pv === "" ? (opt.hint || "Pick one first.") : ""

    situation: {
        if (!todo.length && !later.length) return "Nothing is open on your machines."
        var open = all.filter(function (i) { return i.state !== "resolved" && !(page.done[i.id] && page.done[i.id].status === "Resolved") })
        var now = todo.filter(function (i) { return i.sev === "critical" || page.late(i) }), lateN = open.filter(page.late).length
        var worst = now[0] || todo[0]
        return Theme.fmt(open.length) + " open on your machines; " + (now.length ? Theme.fmt(now.length) + " to act on now" : "nothing urgent")
               + (lateN ? ", " + Theme.fmt(lateN) + " past " + (lateN === 1 ? "its" : "their") + " time" : "") + "."
               + (worst ? " The worst: " + (worst.subject || worst.title) + " on " + worst.host + (page.late(worst) ? ", " + (worst.at ? Time.waitLen((Time.now - Time.ms(worst.at)) / 3600000 - (worst.type === "file" || worst.type === "help" ? 1 : 24)) + " " : "") + "past its time." : ", " + Fleet.sevWord(worst.sev).toLowerCase() + ".") : "")
    }
    situationAt: Time.now

    // what can be done, by type and situation
    function build(i, mm) {
        var online = mm && mm.online, user = mm ? mm.user : ""
        if (i.type === "file") return {
            lead: "A copy of a file marked restricted is on " + i.host + ". It may only be where it was marked, so nowhere else may have it.",
            facts: [["File", i.subject], ["Found", Time.atDay(i.at)]],
            why: user ? [] : ["Nobody is signed in, so there is nobody to tell."],
            options: (user && online ? [{ key: "ask", icon: "message", title: "Ask " + user + " to delete it", desc: user + " sees which file and why. The issue closes on its own when the copy is gone.", verb: "Ask", cannot: "The Engine cannot send this request yet" }] : [])
                .concat([{ key: "delete", icon: "delete", title: "Delete this copy", desc: "Deletes it from " + i.host + " only. The original is not touched.", verb: "Delete copy", danger: true, cannot: "The Engine cannot delete a copy yet" },
                         { key: "allow", icon: "safety", title: "Allow it on " + i.host + " too", desc: "Marks it dealt with. If the copy is still there, the next file event flags it again.", verb: "Allow it", need: "reason" }])
        }
        if (i.type === "help") return {
            lead: (user || "Someone") + " asked to talk and no Admin has accepted yet. A request carries one line; accepting opens the conversation.",
            facts: [["From", (user || "Someone") + " on " + i.host], ["Asked", i.subject], ["Waiting", Time.age(i.at)]],
            why: online ? [] : [i.host + " is offline, so you cannot enter it."],
            options: [{ key: "answer", icon: "message", title: "Accept and answer " + (user || "them"), desc: "Opens your conversation with their line in it. The other Admins see it is answered.", verb: "Send", need: "message" }]
                .concat(online ? [{ key: "enter", icon: "login", title: "Enter " + i.host + " and look yourself", desc: (user || "Whoever is signed in") + " cannot use it while you are in. You get 30 minutes.", verb: "Enter " + i.host }] : [])
        }
        if (i.type === "deviation") return {
            lead: i.host + " presented something that does not match what it was registered with.",
            facts: [["What", i.title], ["Seen", Time.atDay(i.at)]].concat(i.ref && i.ref.detail ? [["Registered as", i.ref.detail.expected || "—"], ["Presented", i.ref.detail.presented || "—"]] : []),
            why: online ? [] : [i.host + " is offline, so you cannot look into it from inside."],
            options: (online ? [{ key: "look", icon: "login", title: "Look into it first", desc: "Enter " + i.host + " and check who changed it." + (user ? " " + user + " cannot use it while you are in." : ""), verb: "Enter " + i.host }] : [])
                .concat([{ key: "accept", icon: "checkcircle", title: "Accept what it presented", desc: "Registers the machine with its new name and pins its certificate.", verb: "Accept", cannot: "The Engine cannot accept a deviation yet" },
                         { key: "reverse", icon: "undo", title: "Put it back", desc: "A new certificate is sent the next time the machine checks in.", verb: "Put it back", cannot: "The Engine cannot do this yet" }])
        }
        return {
            lead: i.host + " is on " + String(i.subject).split(" → ")[0] + " and should be on " + (Fleet.version || "the current version") + ".",
            facts: [["Running", i.ref && i.ref.version ? i.ref.version : "an older version"], ["Should run", Fleet.version || "—"],
                    ["Attempts", i.ref ? String(i.ref.failures || 0) + (i.ref.last_attempt_at ? ", last " + Time.atDay(i.ref.last_attempt_at) : "") : "—"]],
            why: online ? [] : [i.host + " is offline, so it can only retry when it is back."],
            options: (online ? [{ key: "idle", icon: "clock", title: "Retry when it is idle", desc: "The default. The next idle window is usually after the working day.", verb: "Keep this", waits: true },
                                { key: "now", icon: "reload", title: "Retry now", desc: (user || "Whoever is signed in") + " may see a restart prompt.", verb: "Retry now", cannot: "The Engine retries on its own schedule; it cannot be told to now" }]
                             : [{ key: "wait", icon: "clock", title: "Retry when it is back online", desc: "The update runs as soon as " + i.host + " checks in again.", verb: "Keep waiting", waits: true }])
        }
    }

    Confirm { id: confirm; page: page }
    function enter(i, after) {
        // two Admins are never on one machine at once, and nobody is pushed out (docs/design/v1-it-admin.md)
        if (m && m.held && m.held !== Nav.me) {
            confirm.ask({ title: m.held + " is in " + i.host, text: m.held + " is inside now. Two Admins are never on one machine at once, and nobody is pushed out. Send them a message on Messages, or enter when they have left.", ok: "OK" }, null)
            return
        }
        confirm.ask({ title: "Enter " + i.host + "?", text: (m && m.user ? m.user + " is signed in and cannot use it while you are in. " : "") + "You get 30 minutes, and can extend them.", ok: "Enter" },
                    function () { falcon.call("hierarchy.traverse", { pc_id: i.pc_id }, function (ok, r) {
                        if (!ok) { Msg.failed(r && r.message ? r.message : "Could not enter"); return }
                        if (after) after(); Msg.ok("You are in " + i.host)
                    }) })
    }
    function act() {
        var i = it, o = opt, v = val.trim()
        if (i.iid !== undefined && o.key !== "enter" && o.key !== "look") {
            var pl = { issue_id: i.iid, key: o.key }
            if (o.need === "reason") pl.reason = v
            if (o.need === "message") pl.message = v
            if (o.need === "pick") pl.pick = pv
            falcon.call("issues.act", pl, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Not done"); return }
                Msg.ok((r.issue && r.issue.state === "resolved" ? "Resolved" : "Done, your part") + " · recorded"); page.det = null; page.loadDet(); Fleet.refresh()
            })
            return
        }
        if (o.key === "enter" || o.key === "look") { enter(i, function () { page.mark(i, "Open", "Entered " + i.host) }); return }
        if (o.key === "allow")
            falcon.call("resource.resolve", { violation_id: i.ref.violation_id, reason: v }, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Not done"); return }
                page.mark(i, "Resolved", "Allowed " + i.subject + " on " + i.host + ": “" + v + "”"); Fleet.refresh(); Msg.ok("Allowed · recorded")
            })
        else if (o.waits) { page.mark(i, "Waiting", o.title); Msg.ok("Done, your part · it retries by itself") }
    }
    function mark(i, status, how) { var d = Object.assign({}, done); d[i.id] = { status: status, how: how, at: Date.now() }; done = d }

    // what a card says under its name
    function whenSay(x) { var t = Time.ms(x), d = Math.round((new Date(Time.now).setHours(0, 0, 0, 0) - new Date(t).setHours(0, 0, 0, 0)) / 86400000)
                          return (d === 0 ? "Today" : d === 1 ? "Yesterday" : Time.dayName(t)) + " at " + Time.hhmm(t) }
    function cardLine(i) {
        var d = done[i.id]
        if (d) return d.status === "Resolved" ? d.how : "Waits on the step you took: " + d.how.charAt(0).toLowerCase() + d.how.slice(1)
        if (i.state === "waiting") {
            var mm = Fleet.byHost[i.host]
            if (i.type === "update") return mm && !mm.online ? "Waits for " + i.host + " to come online; the update retries then" : "Retries when " + i.host + " is idle"
            if (i.type === "flow") return "Waits for " + (String(i.subject || "").split(" → ")[1] || "them") + " to pick a folder"
            return "Waits on the step already taken"
        }
        if (i.state === "resolved") return "Resolved"
        var dt = i.ref && i.ref.detail ? i.ref.detail : null        // the folder comes with issues.list once the Engine sends it there (ENGINE-GAPS #23)
        return (i.type === "file" && dt && dt.folder ? "in " + dt.folder : i.title) + (i.sev === "critical" ? " · critical" : "")
    }

    // one heading per kind, the kind with the most pressing issue first; its worst three, the rest a click away. Groups
    // stand 16px further apart than the box's own gap (iqp .iq-grp + .iq-grp)
    readonly property var plural: ({ file: "Restricted copies", update: "Machines behind on the version", deviation: "Certificate mismatches", flow: "Flows waiting for a folder" })
    component KindGroups: Column {
        id: kg
        property string list: ""
        property var xs: []
        width: parent.width
        spacing: 26
        readonly property var groups: {
            var gs = []
            xs.forEach(function (i) { var g = gs.filter(function (x) { return x.ty === i.type })[0]; if (g) g.xs.push(i); else gs.push({ ty: i.type, xs: [i] }) })
            return gs
        }
        Repeater {
            model: kg.groups
            delegate: Group {
                id: grp
                required property var modelData
                readonly property string key: kg.list + modelData.ty
                readonly property bool open: !!page.more[key]
                readonly property var hosts: modelData.xs.map(function (x) { return x.host }).filter(function (h, k, a) { return a.indexOf(h) === k })
                readonly property int crit: modelData.xs.filter(function (x) { return x.sev === "critical" }).length
                width: kg.width
                title: (page.plural[modelData.ty] || (page.types[modelData.ty] || { plural: modelData.ty }).plural) + " · " + modelData.xs.length
                sub: "on " + Theme.listNames(grp.hosts, 3) + (grp.crit ? ", " + Theme.fmt(grp.crit) + " critical" : "")
                Repeater {
                    model: grp.open ? grp.modelData.xs : grp.modelData.xs.slice(0, 3)
                    delegate: Card {
                        required property var modelData
                        readonly property bool fin: page.isDone(modelData)
                        readonly property bool crit: !fin && modelData.sev === "critical"
                        objectName: "issue_" + modelData.id
                        width: grp.cardW
                        actW: 0
                        midW: 150
                        padV: 8
                        icon: (page.types[modelData.type] || { icon: "alert" }).icon
                        hot: crit
                        dim: !!(fin && (modelData.state === "resolved" || (page.done[modelData.id] && page.done[modelData.id].status === "Resolved")))
                        title: modelData.subject || modelData.title
                        line: page.cardLine(modelData)
                        lineHot: crit
                        picked: page.it !== null && page.it.id === modelData.id
                        onOpen: page.sel = modelData.id
                        mid: Row {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 14
                            Txt { text: modelData.host; mono: true; color: Theme.text3; elide: Text.ElideNone }
                            Txt { text: modelData.at ? (Time.sameDay(Time.ms(modelData.at), Time.now) ? Time.hhmm(modelData.at) : Time.dayName(Time.ms(modelData.at))) : ""; mono: true; color: Theme.text3; elide: Text.ElideNone }
                        }
                    }
                }
                Txt {
                    visible: grp.modelData.xs.length > 3
                    text: grp.open ? "Show fewer" : "and " + Theme.fmt(grp.modelData.xs.length - 3) + " more"
                    color: mA.containsMouse ? Theme.accent : Theme.text3
                    font.pixelSize: 13
                    MouseArea { id: mA; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: { var x = Object.assign({}, page.more); x[grp.key] = !grp.open; page.more = x } }
                }
            }
        }
    }

    Row {
        width: parent.width
        spacing: 14
        // --- the lists, and the picked one's story (the left column; the story fills what is left of it) -------
        Column {
            id: left
            width: (parent.width - 14) * 8 / 12
            spacing: 14
            Box {
                id: todoB
                objectName: "issuesTodo"
                width: parent.width
                title: "To do · " + page.todo.length
                sub: "the next step is yours, by kind; the kind with the most pressing issue first, critical and late first within it"
                KindGroups { visible: page.todo.length > 0; list: "todo"; xs: page.todo }
                Quiet { visible: page.todo.length === 0; icon: "check"; text: "Nothing for you to do." }
            }
            Box {
                id: doneB
                objectName: "issuesDone"
                width: parent.width
                title: "Done · " + page.later.length
                sub: "you have done your part; each says what happens next, and stays here until tomorrow"
                KindGroups { visible: page.later.length > 0; list: "later"; xs: page.later }
                Quiet { visible: page.later.length === 0; text: "Nothing done today yet." }
            }
            Box {
                id: story
                objectName: "issueStory"
                visible: page.it !== null
                width: parent.width
                height: Math.max(implicitHeight, fix.implicitHeight - todoB.implicitHeight - doneB.implicitHeight - 28)
                title: "Its story"
                sub: page.it ? (page.it.subject || page.it.title) + " on " + page.it.host : ""
                readonly property var evs: page.det && page.det.timeline ? page.det.timeline.map(function (e) { return { t: Time.ms(e.at), actor: e.who, what: e.what, kind: e.kind } })
                                         : page.it ? page.audit.filter(function (e) { return e.host === page.it.host && Math.abs(e.t - Time.ms(page.it.at)) < 2 * 3600000 }).slice(0, 6).reverse() : []
                Column {
                    width: parent.width
                    spacing: 0
                    opacity: page.loading ? 0 : 1
                    Txt { width: parent.width; bottomPadding: 6.5 - topPadding; text: "The story of this issue, oldest first. Whatever you choose on the right is added here, with the time."; color: Theme.text3; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                    Txt { visible: story.evs.length === 0; text: page.it ? "Nothing recorded on " + page.it.host + " around it yet. What you do here is added as you go." : ""; color: Theme.text3; font.pixelSize: 13 }
                    Column {
                        width: parent.width
                        Repeater {
                            model: story.evs
                            Item {
                                required property var modelData
                                width: parent.width
                                height: el.height + 13
                                Txt { y: 6 + el.baselineOffset - baselineOffset; width: 44; mono: true; color: Theme.text3; elide: Text.ElideNone
                                      text: Time.sameDay(modelData.t, Time.now) ? Time.hhmm(modelData.t) : Time.dayName(modelData.t) + " " + Time.hhmm(modelData.t) }
                                Rectangle { x: 52; y: 6 + el.height / 2 - 3.5; width: 7; height: 7; radius: 3.5; color: Kinds.color(modelData.kind) }
                                Txt { id: el; x: 70; y: 6; width: parent.width - 70; textFormat: Text.StyledText
                                      text: "<span style='font-weight:500'>" + modelData.actor + "</span> <font color='" + Theme.text2 + "'>" + modelData.what + "</font>" }
                                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                            }
                        }
                    }
                    Item {
                        visible: page.it !== null && !page.isDone(page.it)
                        width: parent.width
                        height: nx.height + 10
                        Dash { c: Theme.borderStrong }
                        Txt { id: nx; y: 8; width: parent.width; text: "Next: what you do on the right will appear here."; color: Theme.text3; font.pixelSize: 13 }
                    }
                }
                Loading { parent: story; on: page.loading; under: 44; text: "Loading" }
                Pulse { parent: story; key: page.loading ? null : (page.it ? page.it.id : null) }
            }
        }

        // --- the picked issue ------------------------------------------------------------------------------
        Box {
            id: fix
            objectName: "issueFix"
            visible: page.it !== null
            width: (parent.width - 14) * 4 / 12
            title: "The issue"
            sub: "the same fields for every issue, then what to do"
            gap: 12
            Pulse { parent: fix; key: page.it ? page.it.id : null }
            Facts {
                labelW: 104
                rows: !page.it ? [] : [["What", page.it.subject || page.it.title, ((page.types[page.it.type] || { label: "" }).label + " · " + Fleet.sevWord(page.it.sev)).toLowerCase()],
                                        ["Where", page.it.host, page.m ? page.m.deptName + " · " + (page.m.user ? page.m.user + " signed in" : "nobody signed in") : ""],
                                        ["When", page.whenSay(page.it.at), page.isDone(page.it) ? "done, your part" : "open"]]
                                        .concat(page.play && !page.isDone(page.it) ? page.play.facts.filter(function (f) { return !/^(File|Machine|Found on|Severity|Signed in)$/.test(f[0]) }).map(function (f) { return [f[0], f[1], ""] }) : [])
            }
            // resolved: what was done, and Reopen
            Rectangle {
                readonly property var d: page.it ? page.done[page.it.id] : null
                visible: !!d && d.status === "Resolved"
                width: parent.width
                height: visible ? 48 : 0
                radius: Theme.radiusLg
                color: Theme.mix(Theme.ok, Theme.surface, 0.08)
                Row {
                    x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                    Icon { name: "checkcircle"; size: 16; color: Theme.ok; anchors.verticalCenter: parent.verticalCenter }
                    Txt { textFormat: Text.StyledText; text: "<b>Resolved</b> · " + (parent.parent.d ? parent.parent.d.how : ""); width: fix.innerW - 120; anchors.verticalCenter: parent.verticalCenter }
                }
                Txt { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: "Reopen"; color: Theme.accent; elide: Text.ElideNone
                      MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { var x = Object.assign({}, page.done); delete x[page.it.id]; page.done = x } } }
            }
            // what to do
            Column {
                readonly property var d: page.it ? page.done[page.it.id] : null
                visible: page.it !== null && !(!!d && d.status === "Resolved")
                width: parent.width
                spacing: 12
                Txt { width: parent.width; text: page.play ? page.play.lead : ""; color: Theme.text2; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                Txt { visible: page.it !== null && page.isDone(page.it); width: parent.width; text: page.it ? page.cardLine(page.it) + ". You can still change course." : ""; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                Column {
                    width: parent.width
                    spacing: 6
                    Item { width: parent.width; height: wt.height + 12; Txt { id: wt; y: 10; text: "What to do"; font.pixelSize: 12; font.weight: Font.DemiBold; color: Theme.text2; elide: Text.ElideNone } }
                    Repeater {
                        model: page.play ? page.play.options : []
                        delegate: Opt {
                            required property var modelData
                            required property int index
                            on: page.opt !== null && modelData.key === page.opt.key
                            title: modelData.title
                            desc: modelData.desc || ""
                            recommended: page.play !== null && modelData.key === page.primaryOf(page.play.options).key
                            onClicked: { var p = Object.assign({}, page.pick); p[page.it.id] = modelData.key; page.pick = p }
                        }
                    }
                }
                Row {
                    visible: page.play !== null && page.play.why.length > 0
                    width: parent.width
                    spacing: 6
                    Icon { name: "info"; size: 12; color: Theme.text3; y: 4 }
                    Txt { width: parent.width - 18; text: page.play ? page.play.why.join(" ") : ""; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                }
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
                Item {
                    width: parent.width
                    height: 30
                    Txt {
                        anchors.right: go.left
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.min(implicitWidth, parent.width - go.width - 8)
                        horizontalAlignment: Text.AlignRight
                        color: Theme.text3
                        font.pixelSize: 12
                        text: !page.opt ? "" : page.opt.cannot ? page.opt.cannot + "." : page.missing
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
    Quiet { visible: Fleet.loaded && page.all.length === 0; icon: "check"; text: "Nothing is open on your machines." }
}
