import QtQuick
import "."

// REPORTS, at both levels. Every report is written once and the Super User always receives it; a kind
// routed to a department is theirs to address. The Super User's page: the reports (waiting on you
// first), the report beside them, and under it where that kind goes -- read as a sentence, changed in
// place. An Admin's page: only what is routed to the department, never a report about an Admin.
Page {
    id: page
    objectName: "reportsView"

    property var reports: []
    property var routing: []                 // [{category, routed_department_id, department_name}]
    property var fixed: ["about_admin"]
    property var addressedBy: ({})           // report id -> {by, at}
    property string view: ""
    property string cat: ""
    property var sel: Nav.sub && !isNaN(Number(Nav.sub)) ? Number(Nav.sub) : null
    property string kc: ""                   // the kind picked in the routing panel
    property bool editing: false
    property var editOn: []
    property bool moveOld: true

    readonly property var words: ({ resource_violation: "Restricted file", flow_failure: "Flow failed", listener_report: "Listener report",
                                    update_status: "Update stuck", deviation: "Deviation", about_admin: "About an Admin",
                                    directory_structure_conflict: "Folder conflict", cross_department_assistance: "Help across departments" })
    readonly property var icons: ({ resource_violation: "fileprotect", flow_failure: "branches", listener_report: "message", update_status: "cloudsync",
                                    deviation: "warn", about_admin: "eye", directory_structure_conflict: "folder", cross_department_assistance: "team" })
    readonly property var writes: ({ resource_violation: "A copy of a marked file turned up somewhere it is not allowed.", flow_failure: "A flow stopped copying, or one of its branches paused.",
                                     listener_report: "Something a listener on a help channel wrote down.", update_status: "A machine failed to update and went past the retry limit.",
                                     deviation: "A machine showed something it was not registered with, like another name.", about_admin: "An Admin's own conduct, such as entering machines at night.",
                                     directory_structure_conflict: "Two flows or tiers disagree about a folder.", cross_department_assistance: "An Admin helped a worker in another department." })
    function word(c) { return words[c] || String(c).replace(/_/g, " ") }

    function load() {
        falcon.call("reports.list", {}, function (ok, r) { page.reports = ok ? (r.reports || []) : [] })
        if (Nav.boss) {
            falcon.call("reports.routing_get", {}, function (ok, r) { if (ok) { page.routing = r.routing || []; page.fixed = r.fixed || ["about_admin"] } })
            falcon.call("reports.addressed_view", {}, function (ok, r) {
                var m = {}
                if (ok) (r.addressed || r.views || []).forEach(function (v) { m[v.report_id] = { by: v.addressed_by_name, at: v.addressed_at, dept: v.department_name } })
                page.addressedBy = m
            })
        }
    }
    Component.onCompleted: load()
    Connections { target: falcon; function onPushReceived(type) { if (/^report/.test(type)) page.load() } }

    function routedTo(c) { return routing.filter(function (x) { return x.category === c }) }
    function state(r) { return r.addressed_at ? "done" : Nav.boss ? (fixed.indexOf(r.category) < 0 && routedTo(r.category).length ? "dept" : "you") : "wait" }
    function took(r) { return r.addressed_at ? (Time.ms(r.addressed_at) - Time.ms(r.generated_at)) / 60000 : null }
    readonly property var cats: reports.map(function (r) { return r.category }).filter(function (v, i, a) { return a.indexOf(v) === i })
    readonly property var rows: reports.filter(function (r) {
        return (view === "" || page.state(r) === view) && (cat === "" || r.category === cat)
            && (page.word(r.category) + " " + (r.summary || "")).toLowerCase().indexOf(list.query.toLowerCase()) >= 0
    }).map(function (r) { return Object.assign({ st: page.state(r) }, r) })
      .sort(function (a, b) { var o = { you: 0, wait: 0, dept: 1, done: 2 }; return o[a.st] - o[b.st] || Time.ms(b.generated_at) - Time.ms(a.generated_at) })
    readonly property var r: { for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; return rows.length ? rows[0] : null }
    readonly property var med: { var t = reports.map(page.took).filter(function (x) { return x !== null }).sort(function (a, b) { return a - b }); return t.length ? t[t.length >> 1] : null }
    function n(k) { return reports.filter(function (x) { return page.state(x) === k }).length }

    // the routing panel's kind: the picked one, else the kind of the report above
    readonly property string kind: kc !== "" ? kc : r ? r.category : "resource_violation"
    readonly property bool kindFixed: fixed.indexOf(kind) >= 0
    readonly property var saved: routedTo(kind).map(function (x) { return x.routed_department_id })
    readonly property bool changed: editing && (editOn.length !== saved.length || editOn.some(function (x) { return saved.indexOf(x) < 0 }))
    readonly property var waitingKind: reports.filter(function (x) { return x.category === page.kind && !x.addressed_at })

    function mark(x) {
        falcon.call("reports.mark", { report_id: x.id }, function (ok, res) {
            if (!ok) { Msg.failed(res && res.message ? res.message : "Not marked"); return }
            Msg.ok("Marked addressed · recorded with your name"); page.load()
        })
    }
    Confirm { id: confirm; page: page }
    function saveRouting() {
        var add = editOn.filter(function (x) { return page.saved.indexOf(x) < 0 }), drop = saved.filter(function (x) { return page.editOn.indexOf(x) < 0 })
        var nm = function (ids) { return Theme.listNames(ids.map(function (id) { return Fleet.deptName(id) })) }
        confirm.ask({ title: "Change where " + word(kind).toLowerCase() + " reports go?", ok: "Save", cancel: "Keep editing",
                      text: [add.length ? nm(add) + (add.length === 1 ? " starts" : " start") + " getting them" + (page.moveOld ? ", with those already waiting." : ".") : "",
                             drop.length ? nm(drop) + (drop.length === 1 ? " stops" : " stop") + " getting them." : "", "Recorded in the audit log."].filter(function (s) { return s }).join(" ") },
                    function () { falcon.call("reports.routing_set", { category: page.kind, department_ids: page.editOn, include_earlier: page.moveOld }, function (ok, res) {
                        if (!ok) { Msg.failed(res && res.message ? res.message : "Not saved"); return }
                        Msg.ok(page.word(page.kind) + " routing saved · recorded in the audit log"); page.editing = false; page.load() }) })
    }

    Strip {
        width: parent.width
        on: page.view === "" ? null : page.view
        onPick: function (k) { page.view = k === null ? "" : k }
        items: Nav.boss ? [
            { key: "you", label: "Waiting on you", value: Theme.fmt(page.n("you")), delta: "nobody below you can take them", dc: page.n("you") ? Theme.crit : undefined },
            { key: "dept", label: "Waiting in departments", value: Theme.fmt(page.n("dept")), delta: "their Admins address them" },
            { key: "done", label: "Addressed", value: Theme.fmt(page.n("done")), delta: "this week" },
            { label: "Typical time to address", value: page.med === null ? "—" : Time.mins(Math.round(page.med)), delta: "target 1 hour", dc: page.med > 60 ? Theme.med : undefined }
        ] : [
            { key: "wait", label: "Waiting in your department", value: Theme.fmt(page.n("wait")), delta: "you or another Admin here addresses them", dc: page.n("wait") ? Theme.crit : undefined },
            { label: "Gone to the Super User", value: "—", delta: "not routed here · only they see them" },
            { key: "done", label: "Addressed", value: Theme.fmt(page.n("done")), delta: "this week" },
            { label: "Typical time to address", value: page.med === null ? "—" : Time.mins(Math.round(page.med)), delta: "target 1 hour", dc: page.med > 60 ? Theme.med : undefined }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            title: Nav.boss ? "Reports" : "Reports routed here"
            sub: page.view || page.cat ? Theme.fmt(page.rows.length) + (page.cat ? " · " + page.word(page.cat).toLowerCase() : "") : (Nav.boss ? "waiting on you first" : "waiting first") + " · click one to see it on the right"
            subLink: page.view || page.cat ? "every report" : ""
            onSubLinkClicked: { page.view = ""; page.cat = "" }
            placeholder: "Filter by kind or words"
            tools: Select {
                width: 160; small: true; popupWidth: 240
                value: page.cat
                options: [{ value: "", label: "Every kind" }].concat(page.cats.map(function (c) { return { value: c, label: page.word(c) + " · " + page.reports.filter(function (x) { return x.category === c && !x.addressed_at }).length } }))
                onPicked: function (v) { page.cat = v }
            }
            rows: page.rows
            pick: page.r ? page.r.id : null
            onPicked: function (k) { page.sel = k; page.kc = ""; page.editing = false }
            icon: function (x) { return page.icons[x.category] || "filetext" }
            nameTitle: "Report"
            nameText: function (x) { return page.word(x.category) }
            nameLine: function (x) { return "R-" + x.id + (x.summary ? " · " + x.summary : "") }
            cols: Nav.boss ? [{ title: "Goes to", width: 190, text: function (x) { var d = page.routedTo(x.category).map(function (y) { return y.department_name }); return page.fixed.indexOf(x.category) >= 0 || !d.length ? "You only" : "You and " + Theme.listNames(d) } },
                              { title: "Written", width: 110, text: function (x) { return Time.at(x.generated_at) } }]
                           : [{ title: "Written", width: 120, text: function (x) { return Time.at(x.generated_at) } }]
            now: function (x) {
                return x.st === "done" ? ["Addressed" + (page.addressedBy[x.id] ? " · " + page.addressedBy[x.id].by : ""), "good"]
                     : x.st === "dept" ? ["With the department", "wait"] : x.st === "you" ? ["Waiting on you", "bad"] : ["Waiting", "bad"]
            }
            showEmpty: page.reports.length === 0
            emptyIcon: "filetext"
            emptyTitle: Nav.boss ? "No reports yet" : "Nothing is routed here yet"
            emptyText: Nav.boss ? "The system writes a report when something needs a person. Each one, where it went and how fast it was dealt with appears here."
                                : "The Super User decides which kinds of report reach this department. Those that do appear here, for any Admin here to address."
        }
        Column {
            width: (parent.width - 14) * 4 / 12
            spacing: 14
            SidePanel {
                width: parent.width
                fixed: !Nav.boss
                showEmpty: page.r === null
                emptyIcon: "filetext"
                emptyText: "Pick a report in the list."
                title: page.r ? page.word(page.r.category) : ""
                sub: page.r && page.sel === page.r.id ? "the one you picked" : "the first in the list · click another"
                facts: page.r ? [["What", page.r.summary || "—"], ["Written", Time.atDay(page.r.generated_at)],
                                 ["Goes to", Nav.boss ? (page.fixed.indexOf(page.r.category) >= 0 ? "You only · never routed, it is about an Admin"
                                                         : page.routedTo(page.r.category).length ? "You and " + Theme.listNames(page.routedTo(page.r.category).map(function (y) { return y.department_name }))
                                                         : "You only · not routed to a department") : "The Super User and this department"],
                                 ["Addressed", page.r.addressed_at ? (page.addressedBy[page.r.id] ? page.addressedBy[page.r.id].by + " · " : "") + "took " + Time.mins(Math.round(page.took(page.r))) : "Not yet"]] : []
                actions: Btn { visible: page.r !== null && !page.r.addressed_at; kind: "primary"; text: "Mark addressed"; onClicked: page.mark(page.r) }
            }
            // where this kind goes, under the report (the Super User's)
            SidePanel {
                visible: Nav.boss
                width: parent.width
                fixed: false
                title: "Where this kind goes"
                sub: page.editing ? (page.changed ? "changed, not saved yet" : "changing") : page.kc === "" ? "the kind of the report above" : "the kind you picked"
                facts: [["What writes it", page.writes[page.kind] || ""], ["This week", Theme.many(page.reports.filter(function (x) { return x.category === page.kind }).length, "report")]]
                       .concat(page.editing ? [] : [["Goes to", page.kindFixed ? "You only, always" : page.saved.length ? "You and " + Theme.listNames(page.saved.map(function (id) { return Fleet.deptName(id) }), 3) : "You only"]])
                       .concat([["Waiting on you", page.waitingKind.length ? String(page.waitingKind.length) : "None", page.waitingKind.length ? Theme.crit : null]])
                extra: Select {
                    width: 170; small: true; popupWidth: 230
                    enabled: !page.changed
                    value: page.kind
                    options: Object.keys(page.words).map(function (c) { return { value: c, label: page.word(c) } })
                    onPicked: function (v) { page.kc = v; page.editing = false }
                }
                actions: [
                    Btn { visible: !page.kindFixed && page.editing; text: "Cancel"; onClicked: page.editing = false },
                    Btn { visible: !page.kindFixed && page.editing; kind: "primary"; text: "Save"; enabled: page.changed; onClicked: page.saveRouting() },
                    Btn { visible: !page.kindFixed && !page.editing; iconName: "edit"; text: "Change who gets it"; onClicked: { page.editOn = page.saved.slice(); page.moveOld = true; page.editing = true } }
                ]
                Txt {
                    visible: page.kindFixed || !page.editing
                    width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                    text: page.kindFixed ? "Never shared: a department would be judging its own Admin."
                          : page.saved.length ? "Every new " + page.word(page.kind).toLowerCase() + " report reaches you and " + Theme.listNames(page.saved.map(function (id) { return Fleet.deptName(id) }), 3) + " as it is written; their Admins can address it."
                          : "Every " + page.word(page.kind).toLowerCase() + " report comes only to you."
                }
                Column {
                    visible: page.editing
                    width: parent.width
                    spacing: 8
                    Txt { text: "GOES TO"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                    Txt { text: "You, always, and the Admins of:"; color: Theme.text2 }
                    Select { width: parent.width; multiple: true; search: true; placeholder: "no department yet, only you"; values: page.editOn
                             options: Fleet.depts.map(function (d) { return { value: d.id, label: d.admins.length ? d.name : d.name + " · no Admin" } })
                             onPicked: function (v) { page.editOn = v } }
                    Link { visible: page.editOn.length < Fleet.depts.length; text: "every department"; font.pixelSize: 12; onClicked: page.editOn = Fleet.depts.map(function (d) { return d.id }) }
                    Txt { readonly property var dead: page.editOn.filter(function (id) { var d = Fleet.dept(id); return d && !d.admins.length })
                          visible: dead.length > 0; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.med; font.pixelSize: 12
                          text: Theme.listNames(dead.map(function (id) { return Fleet.deptName(id) })) + (dead.length === 1 ? " has" : " have") + " no Admin, so its reports of this kind still come only to you." }
                    Check { visible: page.waitingKind.length > 0; controlled: true; checked: page.moveOld; text: "Also send the ones already waiting"; onToggled: function (on) { page.moveOld = on } }
                    Txt { visible: page.waitingKind.length > 0; leftPadding: 24; color: Theme.text3; font.pixelSize: 12
                          text: page.moveOld ? "They stop waiting on you; you still see them." : "They stay with you; only new ones go." }
                }
            }
        }
    }
}
