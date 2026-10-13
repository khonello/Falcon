import QtQuick
import "."

// ACCOUNTABILITY: where a rule was broken, who it was, and what came of it. One record whole on the right
// (the rule, what it expected and what happened, who, when); the timeline around it and what the record
// shows below the list; the week as bars under both. Falcon does not name a cause: a reason is recorded
// only when a person writes one, and recording outcomes needs the Engine (`cannot`).
Page {
    id: page
    objectName: "accountabilityView"

    readonly property string cannot: "Recording what came of a deviation is not built in the Engine yet"
    property var raw: []
    property var trail: []
    property var kind: null
    property var rule: typeof Nav.sub === "string" && Nav.sub.indexOf("rule:") === 0 ? Nav.sub.slice(5) : null
    property string oc: typeof Nav.sub === "string" && Nav.sub && Nav.sub.indexOf("rule:") !== 0 ? "all" : "open"
    property var day: null
    property var sel: typeof Nav.sub === "string" && Nav.sub && Nav.sub.indexOf("rule:") !== 0 ? Nav.sub : null
    property string outKind: "explained"
    property string note: ""

    function load() {
        if (!falcon.isConnected) return
        falcon.call("audit.deviations", { include_resolved: true }, function (ok, r) { page.raw = ok ? (r.deviations || []) : [] })
        Kinds.load({ limit: 500 }, function (es) { page.trail = es })
    }
    Component.onCompleted: load()
    Connections { target: falcon
                  function onConnected() { page.load() }
                  function onPushReceived(type, payload) { if (type === "audit.event" && String((payload || {}).action || "").indexOf("deviation") === 0) page.load() } }

    readonly property var sevOrd: ({ critical: 0, high: 1, medium: 2, warning: 2, low: 3 })
    function sortKey(a, b) { return page.sevOrd[a.sev] - page.sevOrd[b.sev] || Time.ms(b.at) - Time.ms(a.at) }
    function dayOf(d) { return Math.round((Time.startOfDay(Time.ms(d.at)) - Time.startOfDay(Time.now)) / 86400000) }
    function when(x) { var t = Time.ms(x); return t === null ? "—" : Time.now - t > 7 * 86400000 ? Math.round((Time.now - t) / 86400000) + " days ago" : Time.atDay(x) }

    readonly property var all: raw.map(function (d) { return Rules.devRecord(d) })
    readonly property var week: all.filter(function (d) { return Time.ms(d.at) >= Time.startOfDay(Time.now) - 6 * 86400000 })
    readonly property var broken: Rules.all.map(function (r) { var ds = page.week.filter(function (d) { return d.rule === r.id }); return { r: r, n: ds.length } })
                                           .filter(function (x) { return x.n }).sort(function (a, b) { return b.n - a.n })
    readonly property var list: all.filter(function (d) { return page.day !== null ? page.dayOf(d) === page.day : page.oc === "all" || d.out === "open" })
                                   .filter(function (d) { return (!page.kind || d.kind === page.kind) && (!page.rule || d.rule === page.rule)
                                                              && (d.short + " " + d.who + " " + (d.host || "") + " " + Rules.byId(d.rule).name).toLowerCase().indexOf(lp.query.toLowerCase()) >= 0 })
                                   .sort(sortKey)
    readonly property var dev: { for (var i = 0; i < list.length; i++) if (list[i].id === sel) return list[i]; return list.length ? list[0] : null }
    readonly property var around: !dev || !dev.host ? [] : trail.filter(function (e) { return e.host === page.dev.host && Math.abs(e.t - Time.ms(page.dev.at)) <= 3 * 3600000 })
                                                             .sort(function (a, b) { return a.t - b.t }).slice(0, 10)
    onDevChanged: { outKind = "explained"; note = "" }

    Strip {
        width: parent.width
        on: page.kind
        onPick: function (k) { page.kind = k }
        items: Object.keys(Rules.whoKind).map(function (k) {
            var o = page.all.filter(function (d) { return d.kind === k && d.out === "open" }), hi = o.filter(function (d) { return d.sev === "critical" || d.sev === "high" }).length
            return { key: k, label: Rules.whoKind[k][0] + "s", value: Theme.fmt(o.length), delta: o.length ? (hi ? hi + " critical or high" : "open") : "none open", dc: hi ? Theme.crit : undefined }
        })
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: lp
            width: (parent.width - 14) * 8 / 12
            title: page.day !== null ? "Deviations " + (page.day === 0 ? "today" : page.day === -1 ? "yesterday" : "on " + Time.dayName(Time.now + page.day * 86400000))
                 : page.rule ? Rules.byId(page.rule).name : page.oc === "open" ? "Open deviations" : "Every deviation"
            sub: page.day !== null ? "open and dealt with ·" : page.rule ? "broken this week ·" : "most serious first · click one to see it on the right"
            subLink: page.day !== null ? "every day" : page.rule ? "every rule" : ""
            onSubLinkClicked: { if (page.day !== null) page.day = null; else page.rule = null }
            placeholder: "Filter by person, machine or rule"
            tools: [
                Segmented { visible: page.day === null; value: page.oc; options: [{ value: "open", label: "Open" }, { value: "all", label: "Everything" }]; onPicked: function (v) { page.oc = v } },
                Select { width: 150; small: true; popupWidth: 300; value: page.rule || "all"
                         options: [{ value: "all", label: "Every rule" }].concat(page.broken.map(function (x) { return { value: x.r.id, label: x.r.name + " · " + x.n + " this week" } }))
                         onPicked: function (v) { page.rule = v === "all" ? null : v } }
            ]
            rows: page.list
            pick: page.dev ? page.dev.id : null
            onPicked: function (k) { page.sel = k }
            icon: function (r) { return Rules.whoKind[r.kind][1] }
            nameTitle: "Deviation"
            nameText: function (r) { return r.short }
            nameLine: function (r) { return Rules.byId(r.rule).name }
            cols: [{ title: "Who", text: function (r) { return r.who } },
                   { title: "Severity", width: 110, text: function (r) { return Fleet.sevWord(r.sev) } },
                   { title: "When", width: 120, text: function (r) { return page.when(r.at) } }]
            now: function (r) { return r.out === "open" ? ["Open", "bad"] : r.out === "escalated" ? ["Escalated", "bad"] : r.out === "dismissed" ? ["Dismissed", "wait"] : [Rules.outcomes[r.out][0], "good"] }
            showEmpty: page.all.length === 0
            emptyIcon: "eye"
            emptyTitle: "No deviations yet"
            emptyText: "When a rule is broken, the record appears here: what was expected, what happened, who, when, and what came of it."
            emptyAct: "See the rules →"
            onEmptyAction: Nav.go("rules")
        }
        SidePanel {
            width: (parent.width - 14) * 4 / 12
            showEmpty: page.dev === null
            emptyIcon: "eye"
            emptyText: "Pick a deviation in the list."
            title: page.dev ? page.dev.short : ""
            sub: page.dev && page.sel === page.dev.id ? "the one you picked" : "the most serious · click another"
            factLabelWidth: 118
            // at the list's height, as the concept's: what does not fit scrolls inside it
            facts: page.dev ? [["Deviation", Fleet.sevWord(page.dev.sev) + " · D-" + page.dev.id + " · " + Rules.outcomes[page.dev.out][0], Rules.outcomes[page.dev.out][1], false, true],
                               ["Rule", Rules.byId(page.dev.rule).name + " · built in", null, false, false, "See the rule →"],
                               ["Expected", page.dev.expected], ["What happened", page.dev.happened],
                               ["Who", page.dev.who + (page.dev.whoSub ? " · " + page.dev.whoSub : "")], ["When", page.when(page.dev.at)], ["Kind", Rules.whoKind[page.dev.kind][0]]] : []
            onFactLink: function (label) { if (label === "Rule") Nav.go("rules", page.dev.rule) }
            Column {
                width: parent.width
                spacing: 10
                visible: page.dev !== null
                Txt { text: "WHAT CAME OF IT"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Column {
                    visible: page.dev !== null && page.dev.out === "open"
                    width: parent.width; spacing: 10
                    Segmented { value: page.outKind; options: [{ value: "explained", label: "Explained" }, { value: "accepted", label: "Accepted" }, { value: "escalated", label: "Escalate" }, { value: "dismissed", label: "Dismiss" }]
                                onPicked: function (v) { page.outKind = v } }
                    Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                          text: ({ explained: "Someone gave a reason. It stays on the record with the reason.", accepted: "It was allowed this time. The rule is unchanged.",
                                   escalated: "Flag it for review in the audit log. It stays on the record as escalated.", dismissed: "It was not a real deviation, for example a wrong reading. It is no longer counted." })[page.outKind] }
                    TextArea2 { width: parent.width; text: page.note; onEdited: function (t) { page.note = t }
                                placeholder: ({ explained: "Why did it happen? Recorded with the outcome.", accepted: "Who allowed it, and why? Recorded with the outcome.",
                                                escalated: "What should be looked at? Recorded with the outcome.", dismissed: "Why is it not one? Recorded with the outcome." })[page.outKind] }
                    Item { width: parent.width; height: 30
                           Txt { anchors.verticalCenter: parent.verticalCenter; width: parent.width - rb.width - 10; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                                 text: page.note.trim() ? page.cannot : "Write a line first." }
                           Btn { id: rb; anchors.right: parent.right; kind: "primary"; enabled: false; tip: page.cannot; text: "Record " + Rules.outcomes[page.outKind][0].toLowerCase() } }
                }
                Rectangle {
                    visible: page.dev !== null && page.dev.out !== "open"
                    width: parent.width; height: oc.height + 20; radius: 6
                    color: page.dev ? Theme.alpha(Rules.outcomes[page.dev.out][1], 0.08) : "transparent"
                    border.color: page.dev ? Theme.alpha(Rules.outcomes[page.dev.out][1], 0.35) : "transparent"
                    Column { id: oc; x: 12; y: 10; width: parent.width - 24; spacing: 4
                             Txt { width: parent.width; textFormat: Text.RichText
                                   text: page.dev ? "<b>" + Rules.outcomes[page.dev.out][0] + "</b> <span style='color:" + Theme.text3 + "'>· " + (page.dev.by || "the Engine") + (page.dev.when ? ", " + page.when(page.dev.when) : "") + "</span>" : "" }
                             Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text2
                                   text: page.dev ? (page.dev.note || (page.dev.rule === "B-4" ? "It presented its registered name again." : "No note.")) : "" } }
                }
            }
        }
    }

    Panel {
        visible: page.dev !== null
        width: parent.width
        title: page.dev ? "Around it · " + page.dev.short : ""
        sub: "the same deviation as on the right"
        Row {
            width: parent.width
            spacing: 36
            Column {
                width: (parent.width - 36) / 2
                Txt { text: "THE TIMELINE AROUND IT"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66; bottomPadding: 6 }
                Txt { visible: page.around.length === 0; text: page.dev && page.dev.host ? "Nothing else on " + page.dev.host + " within three hours of it." : "No machine to look around."; color: Theme.text3 }
                Repeater {
                    model: page.around
                    Item {
                        required property var modelData
                        width: parent.width; height: 26
                        Txt { width: 92; anchors.verticalCenter: parent.verticalCenter; text: Time.hhmm(modelData.t); mono: true; color: Theme.text3; font.pixelSize: 12 }
                        Rectangle { x: 92; width: 7; height: 7; radius: 4; anchors.verticalCenter: parent.verticalCenter; color: Kinds.color(modelData.kind) }
                        Txt { x: 108; width: parent.width - 108; anchors.verticalCenter: parent.verticalCenter; textFormat: Text.RichText
                              text: "<span style='font-weight:500'>" + modelData.actor + "</span> <span style='color:" + Theme.text2 + "'>" + modelData.what + "</span>" }
                    }
                }
            }
            Column {
                width: (parent.width - 36) / 2
                spacing: 4
                Txt { text: "WHAT THE RECORD SHOWS"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66; bottomPadding: 2 }
                Repeater {
                    model: page.dev ? [page.dev.host && Fleet.byHost[page.dev.host] && Fleet.byHost[page.dev.host].user ? Fleet.byHost[page.dev.host].user + " is the worker on " + page.dev.host + "." : null,
                                       page.around.some(function (e) { return e.kind === "session" }) ? "Someone signed in or entered " + page.dev.host + " within three hours of it." : null,
                                       page.all.filter(function (x) { return x.host && x.host === page.dev.host }).length > 1 ? "It is not the first on " + page.dev.host + ": " + page.all.filter(function (x) { return x.host === page.dev.host }).length + " on the record." : null]
                                      .filter(function (x) { return x }) : []
                    Row { required property var modelData; width: parent.width; spacing: 8
                          Icon { name: "eye"; size: 14; color: Theme.text3; y: 2 }
                          Txt { width: parent.width - 22; text: modelData; wrapMode: Text.WordWrap; elide: Text.ElideNone } }
                }
                Txt { width: parent.width; topPadding: 4; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                      text: "Evidence only. Falcon does not name a cause; a reason is recorded only when a person writes one." }
            }
        }
    }

    Panel {
        width: parent.width
        title: "Deviations per day"
        sub: "this week · click a day to show only it in the list"
        extra: Btn { visible: page.day !== null; small: true; text: "Every day"; onClicked: page.day = null }
        DevDays { width: parent.width; devs: page.all; day: page.day; onPickDay: function (k) { page.day = k } }
    }
}
