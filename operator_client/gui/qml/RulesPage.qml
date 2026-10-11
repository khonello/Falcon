import QtQuick
import "."

// RULES: the standard the organisation is measured against. The rules list (or the patterns to start
// one from), the picked one on the right, and its pattern drawn under both. Built-in rules are what
// Falcon enforces today, locked; rules you set wait on the Engine's rule store (Rules.cannot).
Page {
    id: page
    objectName: "rulesView"

    property string tab: "rules"
    property var sel: typeof Nav.sub === "string" && Nav.sub ? Nav.sub : null
    property string tp: Rules.templates[0].id
    property var devs: []

    function load() { if (falcon.isConnected) falcon.call("audit.deviations", { include_resolved: true }, function (ok, r) { page.devs = ok ? (r.deviations || []).map(function (d) { return Rules.devRecord(d) }) : [] }) }
    Component.onCompleted: load()
    Connections { target: falcon; function onConnected() { page.load() } }

    function weekOf(id) { return devs.filter(function (d) { return d.rule === id && Time.ms(d.at) >= Time.now - 7 * 86400000 }) }
    readonly property var all: Rules.all
    readonly property int mx: Math.max(1, Math.max.apply(null, all.map(function (r) { return page.weekOf(r.id).length })))
    readonly property var r: { for (var i = 0; i < all.length; i++) if (all[i].id === sel) return all[i]; return null }
    readonly property var g: r || all[all.length - 1]
    readonly property var t0: { for (var i = 0; i < Rules.templates.length; i++) if (Rules.templates[i].id === tp) return Rules.templates[i]; return Rules.templates[0] }
    readonly property int brokenRules: all.filter(function (x) { return page.weekOf(x.id).length }).length
    readonly property int brokenAll: all.reduce(function (t, x) { return t + page.weekOf(x.id).length }, 0)

    Strip {
        width: parent.width
        items: [
            { label: "Rules", value: Theme.fmt(page.all.length), delta: Rules.builtin.length + " built in, 0 set by you" },
            { label: "Switched on", value: Theme.fmt(page.all.length), unit: "/ " + Theme.fmt(page.all.length), delta: "built-in rules are always on" },
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
            onAction: Nav.go("rules", "new")
            rows: page.all.filter(function (x) { return (x.name + " " + Rules.sentence(x)).toLowerCase().indexOf(lp.query.toLowerCase()) >= 0 })
            pick: page.r ? page.r.id : null
            onPicked: function (k) { page.sel = k }
            icon: function (x) { return Rules.shapes[x.shape].icon }
            nameTitle: "Rule"
            nameText: function (x) { return x.name }
            nameLine: function (x) { return Rules.shapes[x.shape].w }
            cols: [{ title: "Set by", width: 110, text: function (x) { return x.locked ? "Built in" : "You" } },
                   { title: "Applies to", width: 190, text: function (x) { return Rules.scope(x) } },
                   { title: "This week", width: 150, bar: function (x) { var n = page.weekOf(x.id).length; return { v: n, max: page.mx, text: Theme.fmt(n) + " broken" } } }]
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
            now: function (t) { return ["Not used yet", "wait"] }
        }
        SidePanel {
            visible: page.tab === "rules"
            width: (parent.width - 14) * 4 / 12
            title: page.g.name
            sub: page.r ? "the one you picked" : "click another"
            readonly property int gn: page.weekOf(page.g.id).length
            facts: [["The rule", Rules.sentence(page.g)], ["Applies to", Rules.scope(page.g)], ["Set by", page.g.locked ? "Built into Falcon · always on" : "You"],
                    ["This week", gn ? Theme.many(gn, "deviation") : "Kept", gn ? Theme.crit : null]]
            actions: Btn { kind: "primary"; enabled: page.weekOf(page.g.id).length > 0; text: "See its deviations →"; onClicked: Nav.go("accountability", "rule:" + page.g.id) }
            Row {
                visible: page.g.locked
                width: parent.width; spacing: 8
                Icon { name: "lock"; size: 14; color: Theme.text3; y: 2 }
                Txt { width: parent.width - 22; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                      text: "Built in · read only. Built-in rules are listed so every deviation points to a rule; they cannot be changed or switched off." }
            }
        }
        SidePanel {
            visible: page.tab === "tp"
            width: (parent.width - 14) * 4 / 12
            title: page.t0.name
            sub: "a pattern · the dashed branch below is where a deviation is noted"
            facts: [["Shape", Rules.shapes[page.t0.state.shape].w], ["What it watches", page.t0.d], ["In use", "Not yet"]]
            actions: Btn { kind: "primary"; iconName: "plus"; enabled: Rules.canSet; tip: Rules.cannot; text: "Build a rule from it"; onClicked: Nav.go("rules", "from-" + page.t0.id) }
            Txt { visible: !Rules.canSet; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12; text: Rules.cannot + "." }
        }
    }

    Panel {
        width: parent.width
        title: page.tab === "tp" ? "The pattern · " + page.t0.name : "The pattern · " + page.g.name
        sub: page.tab === "tp" ? "the same pattern as on the right" : "the same rule as on the right · the dashed branch is where a deviation is noted"
        PatternGraph { width: parent.width; s: page.tab === "tp" ? Object.assign(Rules.blank(), page.t0.state) : Rules.toPattern(page.g) }
    }
}
