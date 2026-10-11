import QtQuick
import "."

// SESSIONS (an Admin's console) and ACCESS (the Super User's): who is inside someone else's machine,
// who was let in, and the day's occupancy under both. A session here is only seen, never blocked or
// ended -- that is the step before entering (Session Blocking) and lives in the entering confirmation.
// Your own session you can leave.
Page {
    id: page
    objectName: Nav.boss ? "accessView" : "sessionsView"

    property string tab: "sessions"
    property string sel: Nav.sub ? String(Nav.sub) : ""
    property string aSel: ""

    function isNight(s) { var h = new Date(Time.ms(s.entered_at)).getHours(); return h < 6 || h >= 18 }
    readonly property var all: Fleet.sessionsToday.filter(function (s) { return s.occupied_via !== "native" })
        .map(function (s) { return Object.assign({ id: String(s.session_id), night: page.isNight(s), now: !s.ended_at }, s) })
    readonly property var rows: all.filter(function (x) { return (x.hostname + " " + x.occupant_name).toLowerCase().indexOf(list.query.toLowerCase()) >= 0 })
        .sort(function (a, b) { return (b.now ? 1 : 0) - (a.now ? 1 : 0) || Time.ms(b.entered_at) - Time.ms(a.entered_at) })
    readonly property var assist: all.filter(function (x) { return x.occupied_via === "assisted" })
    readonly property var nights: all.filter(function (x) { return x.night })
    readonly property var cur: { for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; return rows.length ? rows[0] : null }
    readonly property var aCur: { for (var i = 0; i < assist.length; i++) if (assist[i].id === aSel) return assist[i]; return assist.length ? assist[0] : null }
    function ownerOf(host) { var m = Fleet.byHost[host]; return m && m.user ? m.user : "nobody" }
    function kindWord(v, who) { return v === "assisted" ? "Assisted access" : who === "You" ? "Your session" : "Admin session" }

    Strip {
        width: parent.width
        items: [
            { label: "Inside a machine now", value: Theme.fmt(page.all.filter(function (x) { return x.now }).length),
              delta: page.all.filter(function (x) { return x.now }).slice(0, 2).map(function (x) { return (x.occupant_name === "You" ? "you" : x.occupant_name) + " on " + x.hostname }).join(" · ") },
            { label: "Non-owner sessions today", value: Theme.fmt(page.all.length) },
            { label: "At night, today", value: Theme.fmt(page.nights.length),
              delta: page.nights.length ? page.nights.map(function (x) { return x.occupant_name }).filter(function (v, i, a) { return a.indexOf(v) === i }).join(", ") : "nobody went in after hours",
              dc: page.nights.length ? Theme.crit : undefined },
            { label: "Assisted access, today", value: Theme.fmt(page.assist.length), delta: page.assist.length ? "let in by the worker" : "nobody was let in" }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            visible: page.tab === "sessions"
            width: (parent.width - 14) * 8 / 12
            title: "Sessions today"
            sub: "inside someone else's machine · click one to see it on the right"
            placeholder: "Filter by machine or person"
            tools: Segmented {
                options: [{ value: "sessions", label: "Sessions" }, { value: "assist", label: "Assisted access · " + page.assist.length }]
                value: page.tab
                onPicked: function (v) { page.tab = v }
            }
            rows: page.rows
            pick: page.cur ? page.cur.id : null
            onPicked: function (k) { page.sel = k }
            icon: "login"
            nameTitle: "Session"
            nameText: function (x) { return x.occupant_name + " on " + x.hostname }
            nameLine: function (x) { return page.kindWord(x.occupied_via, x.occupant_name) + " · " + (Fleet.byHost[x.hostname] ? Fleet.byHost[x.hostname].deptName : "") }
            cols: [
                { title: "Owner locked out", text: function (x) { return page.ownerOf(x.hostname) } },
                { title: "Started", width: 100, text: function (x) { return Time.hhmm(x.entered_at) } },
                { title: "Length", width: 100, text: function (x) { return Time.dur(((x.ended_at ? Time.ms(x.ended_at) : Time.now) - Time.ms(x.entered_at)) / 3600000) } }
            ]
            now: function (x) { return x.night ? [x.now ? "Inside now · at night" : "Ended · at night", "bad"] : x.now ? ["Inside now", "good"] : ["Ended", "wait"] }
            showEmpty: Fleet.loaded && page.all.length === 0
            emptyIcon: "login"
            emptyTitle: "Nobody else has been inside a machine today"
            emptyText: "When an Admin enters a machine or someone is let in, the session appears here."
        }
        ListPanel {
            visible: page.tab === "assist"
            width: (parent.width - 14) * 8 / 12
            title: "Assisted access"
            sub: Nav.boss ? "who was let in, and who asked · click one to see it on the right" : "let in here, or helping elsewhere · click one to see it on the right"
            tools: Segmented {
                options: [{ value: "sessions", label: "Sessions" }, { value: "assist", label: "Assisted access · " + page.assist.length }]
                value: page.tab
                onPicked: function (v) { page.tab = v }
            }
            rows: page.assist
            pick: page.aCur ? page.aCur.id : null
            onPicked: function (k) { page.aSel = k }
            icon: "team"
            nameTitle: "Who helped"
            nameText: function (a) { return a.occupant_name + " on " + a.hostname }
            nameLine: function (a) { return page.ownerOf(a.hostname) + " let them in" }
            cols: [{ title: "When", width: 120, text: function (a) { return Time.hhmm(a.entered_at) } }]
            nowTitle: "How it ended"
            now: function (a) { return [a.now ? "Still helping" : "Ended", "wait"] }
            showEmpty: page.assist.length === 0
            emptyIcon: "team"
            emptyTitle: "Nobody has been let in"
            emptyText: "When a worker accepts help from an Admin, it appears here."
        }
        SidePanel {
            visible: page.tab === "sessions"
            width: (parent.width - 14) * 4 / 12
            readonly property var ss: page.cur
            showEmpty: ss === null
            emptyIcon: "login"
            emptyText: "Pick a session in the list."
            title: ss ? ss.occupant_name + " on " + ss.hostname : ""
            sub: ss && page.sel === ss.id ? "the one you picked" : "the first in the list · click another"
            facts: ss ? [["Kind", page.kindWord(ss.occupied_via, ss.occupant_name)], ["From", Time.hhmm(ss.entered_at)], ["Until", ss.ended_at ? Time.hhmm(ss.ended_at) : "now"],
                        ["Owner locked out", page.ownerOf(ss.hostname)], ["Department", Fleet.byHost[ss.hostname] ? Fleet.byHost[ss.hostname].deptName : "—"]]
                        .concat(ss.night ? [["Flag", "Outside working hours", Theme.crit]] : []) : []
            actions: [
                Btn {
                    visible: page.cur !== null && page.cur.now && page.cur.occupant_name === "You"
                    text: "Leave the session"
                    onClicked: falcon.call("hierarchy.end_session", { session_id: page.cur.session_id }, function (ok, r) {
                        if (!ok) { Msg.failed(r && r.message ? r.message : "Still inside"); return }
                        Msg.ok("Left " + page.cur.hostname); Fleet.refresh()
                    })
                },
                Btn {
                    text: Nav.boss ? "See it in Registry →" : "Open " + (page.cur ? page.cur.hostname : "") + "'s page →"
                    onClicked: Nav.go("machines", page.cur.hostname)
                }
            ]
        }
        SidePanel {
            visible: page.tab === "assist"
            width: (parent.width - 14) * 4 / 12
            readonly property var a: page.aCur
            showEmpty: a === null
            emptyIcon: "team"
            emptyText: "Pick an assisted session in the list."
            title: a ? a.occupant_name + " on " + a.hostname : ""
            sub: "assisted access · let in by the worker"
            facts: a ? [["Helper", a.occupant_name], ["Asked by", page.ownerOf(a.hostname)], ["Machine", a.hostname, null, true], ["From", Time.hhmm(a.entered_at)],
                        ["Until", a.ended_at ? Time.hhmm(a.ended_at) : "now"]] : []
            actions: Btn { text: Nav.boss ? "See it in Registry →" : "Open its page →"; onClicked: Nav.go("machines", page.aCur.hostname) }
        }
    }

    Occupancy { width: parent.width }
}
