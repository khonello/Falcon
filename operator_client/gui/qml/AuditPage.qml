import QtQuick
import QtQuick.Dialogs
import "."

// THE AUDIT LOG, at both levels: everything that happened, newest first. Four figures, the list (by
// kind, searchable, exported as CSV), the entry beside it, and the events over time under both --
// drag across the chart to narrow the list to a stretch of time.
Page {
    id: page
    objectName: "recordView"

    property var all: []
    property string kind: ""
    property var brush: null
    property string sel: ""

    Component.onCompleted: {
        var p = Nav.take("audit")
        if (p) { if (p.kinds && p.kinds.length === 1) kind = p.kinds[0]; brush = p.brush || null }
        page.reload()
    }
    // Worth a look and All that was done come from one read; Everything reads again with the machinery (the Engine's levels, feed.py)
    function reload() { Kinds.load({ limit: 500, routine: page.show === "all" }, function (es) { page.all = es }) }
    // to the minute: the list hangs off this, and a value that moved every second rebuilt every row every second
    readonly property real since: Math.floor(Time.now / 60000) * 60000 - Time.rangeHours(Nav.range) * 3600000
    readonly property var base: all.filter(function (e) { return e.t >= since })
    readonly property var shown: base.filter(function (e) {
        return (!kind || e.kind === kind) && (!brush || (e.t >= brush[0] && e.t < brush[1]))

    })


    FileDialog {
        id: save
        fileMode: FileDialog.SaveFile
        defaultSuffix: "csv"
        nameFilters: ["CSV (*.csv)"]
        onAccepted: {
            var q = function (s) { return "\"" + String(s === undefined || s === null ? "" : s).replace(/"/g, "\"\"") + "\"" }
            var lines = ["When,Who,What,Machine,Kind"].concat(page.xRows.map(function (x) { return [new Date(x.t).toISOString(), x.actor, x.what, x.host, Kinds.words[x.kind]].map(q).join(",") }))
            var err = falcon.saveText(selectedFile.toString(), lines.join("\r\n") + "\r\n")
            if (err) Msg.failed("Not saved: " + err); else Msg.ok("Exported " + page.xRows.length + " entries as CSV")
        }
    }

    // --- the version 1 concept's layout (docs/design/concepts-admin.html, AdminAuditPage) -------------------------------------------------
    // Worth a look by default: what someone should look at, as the Engine says (a copy caught, a deadline passed, a refusal, a failure) and
    // a visit outside working hours; All that was done adds what people and Falcon did; Everything adds the machinery (connections, each
    // file a flow carried, catch-ups), which the Engine leaves out unless asked.
    property string show: "worth"
    readonly property bool everything: show !== "worth"
    onShowChanged: page.reload()
    property string q: ""
    property int ap: 0
    readonly property int per: 4             // four a page, on every screen (the user, 13 Nov 2026)
    function worth(x) { return x.level === "worth" || (!!x.visit && !!x.odd) }
    readonly property var says: ({ session: "someone went into or out of a machine", action: "an action ran", flow: "a flow moved files", rollout: "an update", update: "an update",
                                   deviation: "an Automation rule saw something it did not expect", violation: "a protected file turned up where it may not be, or someone was refused it",
                                   protected: "a file was kept to its place, made private or watched", task: "a task moved on", issue: "an issue opened, moved or closed",
                                   message: "someone talked or sent a file", detective: "Detective opened a case or suggested a step", admin: "people, machines and settings",
                                   system: "Falcon itself" })
    function dayWord(t) { var d = Math.round((Time.startOfDay(Time.now) - Time.startOfDay(t)) / 86400000); return d === 0 ? "Today" : d === 1 ? "Yesterday" : Time.dayName(t) }
    function whoSay(a) {
        if (a === "System" || a === "Automation") return "Falcon itself"
        if (a === "You") return "you"
        var m = Fleet.machines.filter(function (x) { return x.user === a })[0]
        return m ? "works on " + m.host : Fleet.depts.some(function (d) { return (d.admins || []).some(function (y) { return y.name === a }) }) ? "IT Admin" : "a person"
    }
    function machineSay(h) {
        var m = Fleet.byHost[h]
        if (!m) return ""
        return m.deptName + " · " + (m.online ? "on now" + (m.user ? ", " + m.user + " signed in" : "") : "off, last seen " + Time.dur((Time.now - Time.ms(m.seen)) / 3600000) + " ago")
    }
    function working(t) { var d = new Date(t), h = d.getHours() + d.getMinutes() / 60; return d.getDay() !== 0 && d.getDay() !== 6 && h >= 8 && h < 17.5 }
    // the log as entries, newest first: a visit (entered, then left) is one entry with its length, never an "entered" and a "left"
    readonly property var entries: entriesOf(base)
    function entriesOf(list) {
        var xs = list.slice().sort(function (a, b) { return a.t - b.t }), out = [], used = {}
        xs.forEach(function (e, i) {
            if (used[i]) return
            var m = /^Entered (\S+)( \(outside working hours\))?$/.exec(e.what)
            if (m) {
                var j = -1
                for (var k = i + 1; k < xs.length; k++) if (xs[k].actor === e.actor && (xs[k].what === "Left " + m[1] || /^Entered /.test(xs[k].what))) { j = k; break }
                if (j >= 0 && xs[j].what === "Left " + m[1]) used[j] = true
                out.push(Object.assign({}, e, { visit: true, what: j >= 0 ? "Inside " + m[1] + " for " + Time.dur((xs[j].t - e.t) / 3600000) : "Inside " + m[1] + " now", odd: !!m[2] || !page.working(e.t), end: j >= 0 ? xs[j].t : null }))
                return
            }
            if (/^Left /.test(e.what)) return
            out.push(Object.assign({}, e, { what: e.what.replace(/ \(outside working hours\)$/, ""), odd: /outside working hours/.test(e.what) }))
        })
        return out.reverse()
    }
    readonly property var listed: entries.filter(function (x) {
        return (page.everything || page.worth(x)) && (!page.brush || (x.t >= page.brush[0] && x.t < page.brush[1]))
            && (x.what + " " + x.actor + " " + x.host).toLowerCase().indexOf(page.q.toLowerCase()) >= 0
    })
    readonly property int pages: Math.max(1, Math.ceil(listed.length / per))
    readonly property int pi: Math.min(ap, pages - 1)
    readonly property var pageRows: listed.slice(pi * per, pi * per + per)
    readonly property var days: pageRows.map(function (x) { return Time.startOfDay(x.t) }).filter(function (d, i, a) { return a.indexOf(d) === i })
    readonly property var cur: { for (var i = 0; i < listed.length; i++) if (listed[i].rid === sel) return listed[i]; return listed.length ? listed[0] : null }
    readonly property var kindIcon: ({ session: "login", action: "thunderbolt", flow: "branches", violation: "fileprotect", protected: "lock", deviation: "warn", task: "checksquare",
                                       issue: "alert", message: "message", detective: "filesearch", report: "filetext", admin: "user", system: "gear", rollout: "cloudupload" })
    property string pickedId: ""
    onCurChanged: pickedId = cur ? cur.rid : ""
    situation: {
        if (!base.length) return "Nothing was recorded in this period."
        var w = entries.filter(page.worth), v = entries.filter(function (x) { return x.kind === "violation" }).length, odd = entries.filter(function (x) { return x.visit && x.odd })
        var says = [v ? Theme.fmt(v) + " restricted cop" + (v === 1 ? "y" : "ies") + " found" : "", odd.length ? Theme.fmt(odd.length) + " visit" + (odd.length === 1 ? "" : "s") + " outside working hours (" + Theme.listNames(odd.slice(0, 2).map(function (x) { return x.actor + ", " + x.host }), 2) + ")" : ""].filter(function (s) { return s }).join(", ")
        return Theme.fmt(base.length) + " things recorded in the last " + Nav.range + "; " + Theme.fmt(w.length) + " worth a look. " + (says || "Nothing out of the ordinary") + ". Kept for 90 days."
    }
    situationAt: Time.now

    Row {
        width: parent.width
        spacing: 14
        // --- what happened -------------------------------------------------------------------------------------------------------------
        Box {
            id: listP
            objectName: "auditList"
            width: (parent.width - 14) * 8 / 12
            height: Math.max(implicitHeight, entry.implicitHeight)
            title: "What happened · " + page.listed.length
            sub: "newest first; click one to see it on the right"
            Item {
                width: parent.width
                height: tools.height + 12
                Row {
                    id: tools
                    spacing: 10
                    Segmented { objectName: "auditWorth"; small: true; options: [{ value: "worth", label: "Worth a look" }, { value: "done", label: "All that was done" }, { value: "all", label: "Everything" }]
                                value: page.show; onPicked: function (v) { page.show = v; page.ap = 0 } }
                    Field { width: 280; small: true; iconName: "search"; placeholderText: "Who, what or which machine"; text: page.q; onTextEdited: { page.q = text; page.ap = 0 } }
                    Btn { visible: page.brush !== null; small: true; kind: "text"; iconRight: true; iconName: "close"; text: page.brush ? Time.hhmm(page.brush[0]) + " to " + Time.hhmm(page.brush[1]) : ""; onClicked: page.brush = null }
                }
            }
            Repeater {
                model: page.days
                delegate: Group {
                    id: dg
                    required property var modelData
                    required property int index
                    width: listP.innerW
                    spaced: index > 0
                    cardGap: 5
                    title: page.dayWord(modelData)
                    Repeater {
                        model: page.pageRows.filter(function (x) { return Time.startOfDay(x.t) === dg.modelData })
                        delegate: Card {
                            id: ec
                            required property var modelData
                            width: dg.cardW
                            midW: 260
                            padV: 7
                            icon: page.kindIcon[modelData.kind] || "history"
                            title: modelData.what
                            line: modelData.actor + " · " + (Kinds.words[modelData.kind] || modelData.kind).toLowerCase() + (modelData.odd ? " · outside working hours" : "")
                            picked: page.cur !== null && page.cur.rid === modelData.rid
                            onOpen: page.sel = modelData.rid
                            mid: Row {
                                anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right
                                spacing: 18
                                Txt { text: ec.modelData.host; mono: true; color: Theme.text3; elide: Text.ElideNone }
                                Txt { text: Time.hhmm(ec.modelData.t); mono: true; color: Theme.text3; elide: Text.ElideNone }
                            }
                        }
                    }
                }
            }
            Quiet { visible: page.listed.length === 0; text: page.base.length ? "Nothing matches." : "Nothing recorded in this period." }
            StepPager {
                visible: page.pages > 1
                width: parent.width
                from: page.pi * page.per + 1
                to: Math.min(page.listed.length, page.pi * page.per + page.per)
                total: page.listed.length
                pageNo: page.pi
                pages: page.pages
                onStep: function (d) { page.ap = page.pi + d }
            }
        }
        // --- the entry: the same seven things for every entry ------------------------------------------------------------------------
        Box {
            id: entry
            objectName: "auditEntry"
            width: (parent.width - 14) * 4 / 12
            height: Math.max(implicitHeight, listP.implicitHeight)
            title: page.cur ? "The entry" : "Nothing picked"
            sub: page.cur ? "the same seven things for every entry in the log" : ""
            readonly property var m: page.cur && page.cur.host ? Fleet.byHost[page.cur.host] || null : null
            Quiet { visible: page.cur === null; text: "Pick an entry in the list." }
            Facts {
                visible: page.cur !== null
                rows: !page.cur ? [] : [
                    ["What", page.cur.what, page.says[page.cur.kind] || ""],
                    ["When", page.dayWord(page.cur.t) + " at " + Time.hhmm(page.cur.t), page.cur.odd || !page.working(page.cur.t) ? "outside working hours" : "in working hours"],
                    ["How long", page.cur.visit ? (page.cur.end !== null ? Time.dur((page.cur.end - page.cur.t) / 3600000) : Time.dur((Time.now - page.cur.t) / 3600000) + " so far") : "A moment",
                     page.cur.visit ? (page.cur.end !== null ? "until " + Time.hhmm(page.cur.end) : "still inside") : "it happened once, at that time"],
                    ["Who", page.cur.actor, page.whoSay(page.cur.actor)],
                    ["Machine", page.cur.host, page.machineSay(page.cur.host)],
                    ["Kind", Kinds.words[page.cur.kind] || page.cur.kind, page.worth(page.cur) ? "worth a look" : page.cur.level === "routine" ? "Falcon's own working" : "something that was done"],
                    ["Kept", Math.max(1, Math.ceil(90 - (Time.now - page.cur.t) / 86400000)) + " more days", "every entry is kept for 90 days, then removed"]]
            }
            Pulse { parent: entry; key: page.pickedId || null }
        }
    }

    // --- over the range: drag across it to show only that stretch in the list --------------------------------------------------------
    Box {
        width: parent.width
        title: Nav.range === "7d" ? "Over the week" : "Over the last " + Nav.range
        sub: page.brush ? Time.hhmm(page.brush[0]) + " to " + Time.hhmm(page.brush[1]) + " picked; the list shows only that" : "drag across it to show only that stretch in the list"
        EventHistogram {
            width: parent.width
            height: 150
            entries: page.all
            kinds: Kinds.keys
            calm: page.worth
            range: Nav.range
            brush: page.brush
            onBrushed: function (b) { page.brush = b; page.ap = 0 }
        }
    }

    // how far back an export goes, and what goes in
    property string xr: "7 days"
    readonly property var xRows: { var h = ({ "7 days": 168, "30 days": 720, "90 days": 2160 })[xr]
                                   var from = xr === "Today" ? Time.startOfDay(Time.now) : Time.now - h * 3600000
                                   return page.entriesOf(all.filter(function (e) { return e.t >= from })) }
    Drawer {
        id: xd
        page: page
        width: 460
        title: "Export the log"
        footer: [ Btn { text: "Cancel"; onClicked: xd.close() },
                  Btn { kind: "primary"; iconName: "download"; text: "Download " + Theme.fmt(page.xRows.length) + " entries"; onClicked: { xd.close(); save.open() } } ]
        NfSec { first: true; title: "How far back"
            Segmented { width: parent.width; block: true; small: false; options: ["Today", "7 days", "30 days", "90 days"]; value: page.xr; onPicked: function (v) { page.xr = v } }
            Txt { width: parent.width; text: "Everything in that stretch goes in. A visit is one line with when it started and ended; each line has when, who, the machine, the kind and what happened."; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone } }
    }

    // --- export: a copy for someone outside Falcon ------------------------------------------------------------------------------------
    Box {
        width: parent.width
        accentFoot: true
        title: "Export the log"
        sub: "a copy for someone outside Falcon; the log itself is never changed"
        GiveSteps {
            steps: [["Pick how far back", "today, a week, a month, or all 90 days; everything in it goes in"], ["Download it", "a CSV file; the export itself is recorded in the log"]]
            act: "Export the log"
            onGo: { Kinds.load({ limit: 5000, routine: true }, function (es) { page.all = es }); xd.open() }
        }
    }
}
