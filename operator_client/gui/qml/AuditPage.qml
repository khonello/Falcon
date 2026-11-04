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
        Kinds.load({ limit: 500 }, function (es) { page.all = es })
    }
    readonly property real since: Time.now - Time.rangeHours(Nav.range) * 3600000
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
            var lines = ["When,Who,What,Machine,Kind"].concat(page.listed.map(function (x) { return [new Date(x.t).toISOString(), x.actor, x.what, x.host, Kinds.words[x.kind]].map(q).join(",") }))
            var err = falcon.saveText(selectedFile.toString(), lines.join("\r\n") + "\r\n")
            if (err) Msg.failed("Not saved: " + err); else Msg.ok("Exported " + page.listed.length + " entries as CSV")
        }
    }

    // --- the version 1 concept's layout (docs/design/concepts-admin.html, AdminAuditPage) -------------------------------------------------
    // Worth a look by default: someone going into a machine, a restricted copy, a deviation, an action or a rule; the routine (files synced,
    // people signing in and out) is under Everything.
    property bool everything: false
    property string q: ""
    property int ap: 0
    readonly property int per: 8
    function worth(x) { return x.kind === "violation" || x.kind === "deviation" || !!x.visit || / notified |^Created flow| failed | left for an Admin/.test(x.what) }
    readonly property var says: ({ session: "someone went into or out of a machine", action: "an action ran", flow: "a flow moved files", rollout: "an update", update: "an update",
                                   deviation: "something did not match what it should be", violation: "a restricted file was found where it should not be" })
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
    readonly property var entries: {
        var xs = base.slice().sort(function (a, b) { return a.t - b.t }), out = [], used = {}
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
    readonly property var kindIcon: ({ session: "login", action: "thunderbolt", flow: "branches", violation: "fileprotect", deviation: "warn", task: "checksquare", report: "filetext", admin: "user", system: "gear", rollout: "cloudupload" })
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
                    Segmented { objectName: "auditWorth"; small: true; options: [{ value: "worth", label: "Worth a look" }, { value: "all", label: "Everything" }]; value: page.everything ? "all" : "worth"
                                onPicked: function (v) { page.everything = v === "all"; page.ap = 0 } }
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
                    ["Kind", Kinds.words[page.cur.kind] || page.cur.kind, page.worth(page.cur) ? "worth a look" : "routine"],
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

    // --- export: a copy for someone outside Falcon ------------------------------------------------------------------------------------
    Box {
        width: parent.width
        accentFoot: true
        title: "Export the log"
        sub: "a copy for someone outside Falcon; the log itself is never changed"
        GiveSteps {
            steps: [["Pick how far back", "the range at the top; everything in it goes in"], ["Download it", "a CSV file; the export itself is recorded in the log"]]
            act: "Export the log"
            onGo: save.open()
        }
    }
}
