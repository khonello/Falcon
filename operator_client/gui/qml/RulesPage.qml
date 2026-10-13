import QtQuick
import "."

// RULES: the standard the organisation is measured against. The rules list (or the patterns to start
// one from), the picked one on the right, and its pattern drawn under both. Built-in rules are locked; the
// Super User's organisation-wide rules come from the Engine's rule store (Rules.list), switched on and off
// and edited here, built on rules/new. An Admin reads them.
Page {
    id: page
    objectName: "rulesView"

    property string tab: "rules"
    property var sel: typeof Nav.sub === "string" && Nav.sub ? Nav.sub : null
    property string tp: Rules.templates.length ? Rules.templates[0].id : ""

    Component.onCompleted: Rules.load()
    Connections { target: falcon; function onPushReceived(type, payload) { if (type === "audit.event" && /^(rule|deviation)/.test(String((payload || {}).action || ""))) Rules.load() } }

    readonly property var all: Rules.all
    readonly property int mx: Math.max(1, Math.max.apply(null, all.map(function (r) { return r.n || 0 })))
    readonly property var r: { for (var i = 0; i < all.length; i++) if (all[i].id === sel) return all[i]; return null }
    // the graph shows the rule you opened, else the one set most recently
    readonly property var g: r || all.slice().sort(function (a, b) { return (Time.ms(b.since) || 0) - (Time.ms(a.since) || 0) })[0] || null
    readonly property var t0: { for (var i = 0; i < Rules.templates.length; i++) if (Rules.templates[i].id === tp) return Rules.templates[i]; return Rules.templates[0] || null }
    readonly property int builtIn: all.filter(function (x) { return x.locked }).length
    readonly property int brokenRules: all.filter(function (x) { return x.n }).length
    readonly property int brokenAll: all.reduce(function (t, x) { return t + (x.n || 0) }, 0)
    // a pattern is in use when a rule carries its name
    function useOf(t) { for (var i = 0; i < all.length; i++) if (!all[i].locked && all[i].name === t.name) return all[i]; return null }

    function switchIt(x) {
        falcon.call("rules.switch", { rule_id: x.rid, on: !x.on }, function (ok, res) {
            if (!ok) { Msg.failed(res && res.message ? res.message : "Not changed"); return }
            Msg.ok(x.name + (x.on ? " off. Earlier deviations stay on the record" : " on")); Rules.load()
        })
    }

    Strip {
        width: parent.width
        items: [
            { label: "Rules", value: Theme.fmt(page.all.length), delta: page.builtIn + " built in, " + (page.all.length - page.builtIn) + " set by you" },
            { label: "Switched on", value: Theme.fmt(page.all.filter(function (x) { return x.locked || x.on }).length), unit: "/ " + Theme.fmt(page.all.length), delta: "built-in rules are always on" },
            { label: "Broken this week", value: Theme.fmt(page.brokenRules), delta: Theme.many(page.brokenAll, "deviation"), dc: page.brokenRules ? Theme.crit : undefined },
            { label: "Kept all week", value: Theme.fmt(page.all.length - page.brokenRules) }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: lp
            visible: page.tab === "rules"
            width: (parent.width - 14) * 8 / 12
            title: "Rules"
            sub: "what every deviation is measured against · click one to see it on the right"
            placeholder: "Filter rules"
            tools: Segmented { value: page.tab; options: [{ value: "rules", label: "Rules" }, { value: "tp", label: "Patterns · " + Rules.templates.length }]; onPicked: function (v) { page.tab = v } }
            actionLabel: "New rule"
            actionDisabled: !Rules.canSet
            actionTip: Rules.canSet ? "" : Rules.cannot
            onAction: Nav.go("rules", "new")
            rows: page.all.filter(function (x) { return (x.name + " " + Rules.sentence(x)).toLowerCase().indexOf(lp.query.toLowerCase()) >= 0 })
            pick: page.r ? page.r.id : null
            onPicked: function (k) { page.sel = k }
            icon: function (x) { return Rules.shapes[x.shape].icon }
            nameTitle: "Rule"
            nameText: function (x) { return x.name }
            nameLine: function (x) { return Rules.shapes[x.shape].w }
            cols: [{ title: "Set by", width: 110, text: function (x) { return x.locked ? "Built in" : (x.setBy || "You") } },
                   { title: "Applies to", width: 190, text: function (x) { return Rules.scope(x) } },
                   { title: "This week", width: 150, bar: function (x) { var n = x.n || 0; return { v: n, max: page.mx, text: Theme.fmt(n) + " broken" } } }]
            now: function (x) { return x.locked ? ["Always on", "good"] : x.on ? ["On", "good"] : ["Off", "wait"] }
        }
        ListPanel {
            visible: page.tab === "tp"
            width: (parent.width - 14) * 8 / 12
            title: "Patterns"
            sub: "start a rule from one · click one to see it on the right"
            tools: Segmented { value: page.tab; options: [{ value: "rules", label: "Rules" }, { value: "tp", label: "Patterns · " + Rules.templates.length }]; onPicked: function (v) { page.tab = v } }
            rows: Rules.templates
            pick: page.tp
            onPicked: function (k) { page.tp = k }
            icon: function (t) { return Rules.shapes[t.state.shape].icon }
            nameTitle: "Pattern"
            nameText: function (t) { return t.name }
            nameLine: function (t) { return Rules.shapes[t.state.shape].w }
            cols: [{ title: "What it watches", width: 320, text: function (t) { return t.d } }]
            now: function (t) { var u = page.useOf(t); return u ? ["In use as " + u.id, "good"] : ["Not used yet", "wait"] }
        }
        SidePanel {
            visible: page.tab === "rules"
            width: (parent.width - 14) * 4 / 12
            showEmpty: page.g === null
            emptyIcon: "safety"
            emptyText: "Pick a rule in the list."
            title: page.g ? page.g.name : ""
            sub: page.r ? "the one you picked" : "set most recently · click another"
            readonly property int gn: page.g ? page.g.n || 0 : 0
            facts: page.g ? [["The rule", Rules.sentence(page.g)], ["Applies to", Rules.scope(page.g)],
                             ["Set by", page.g.locked ? "Built into Falcon · always on" : (page.g.setBy || "You") + (page.g.since ? ", " + Time.day(page.g.since) : "") + (page.g.on ? "" : " · switched off")],
                             ["This week", gn ? Theme.many(gn, "deviation") : "Kept", gn ? Theme.crit : null]] : []
            actions: [
                Btn { visible: page.g !== null && !page.g.locked && Rules.canSet; text: page.g && page.g.on ? "Switch off" : "Switch on"; onClicked: page.switchIt(page.g) },
                Btn { visible: page.g !== null && !page.g.locked && Rules.canSet; iconName: "edit"; text: "Edit"; onClicked: Nav.go("rules", "edit-" + page.g.id) },
                Btn { kind: "primary"; enabled: page.g !== null && (page.g.n || 0) > 0; text: "See its deviations →"; onClicked: Nav.go("accountability", "rule:" + page.g.id) }
            ]
            Row {
                visible: page.g !== null && page.g.locked
                width: parent.width; spacing: 8
                Icon { name: "lock"; size: 14; color: Theme.text3; y: 2 }
                Txt { width: parent.width - 22; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                      text: "Built in · read only. Built-in rules are listed so every deviation points to a rule; they cannot be changed or switched off." }
            }
        }
        SidePanel {
            visible: page.tab === "tp"
            width: (parent.width - 14) * 4 / 12
            showEmpty: page.t0 === null
            title: page.t0 ? page.t0.name : ""
            sub: "a pattern · the dashed branch below is where a deviation is noted"
            readonly property var used: page.t0 ? page.useOf(page.t0) : null
            facts: page.t0 ? [["Shape", Rules.shapes[page.t0.state.shape].w], ["What it watches", page.t0.d], ["In use", used ? used.name : "Not yet"]] : []
            actions: [
                Btn { visible: parent.used !== null; text: "See the rule"; onClicked: { page.tab = "rules"; page.sel = parent.used.id } },
                Btn { visible: parent.used === null; kind: "primary"; iconName: "plus"; enabled: Rules.canSet; tip: Rules.canSet ? "" : Rules.cannot; text: "Build a rule from it"
                      onClicked: Nav.go("rules", "from-" + page.t0.id) }
            ]
        }
    }

    Panel {
        visible: page.tab === "tp" ? page.t0 !== null : page.g !== null
        width: parent.width
        title: page.tab === "tp" ? "The pattern · " + (page.t0 ? page.t0.name : "") : "The pattern · " + (page.g ? page.g.name : "")
        sub: page.tab === "tp" ? "the same pattern as on the right" : "the same rule as on the right · the dashed branch is where a deviation is noted"
        PatternGraph { width: parent.width; s: page.tab === "tp" ? (page.t0 ? Object.assign(Rules.blank(), page.t0.state, { resp: Object.assign(Rules.blank().resp, page.t0.state.resp || {}) }) : Rules.blank())
                                                              : (page.g ? Rules.toPattern(page.g) : Rules.blank()) }
    }
}
