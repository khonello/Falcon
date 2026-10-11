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
            && (e.what + " " + e.actor + " " + e.host).toLowerCase().indexOf(list.query.toLowerCase()) >= 0
    })
    readonly property var e: { for (var i = 0; i < shown.length; i++) if (shown[i].rid === sel) return shown[i]; return shown.length ? shown[0] : null }

    FileDialog {
        id: save
        fileMode: FileDialog.SaveFile
        defaultSuffix: "csv"
        nameFilters: ["CSV (*.csv)"]
        onAccepted: {
            var q = function (s) { return "\"" + String(s === undefined || s === null ? "" : s).replace(/"/g, "\"\"") + "\"" }
            var lines = ["When,Who,What,Machine,Kind"].concat(page.shown.map(function (x) { return [new Date(x.t).toISOString(), x.actor, x.what, x.host, Kinds.words[x.kind]].map(q).join(",") }))
            var err = falcon.saveText(selectedFile.toString(), lines.join("\r\n") + "\r\n")
            if (err) Msg.failed("Not saved: " + err); else Msg.ok("Exported " + page.shown.length + " entries as CSV")
        }
    }

    Strip {
        width: parent.width
        items: [
            { label: "Events", value: Theme.fmt(page.base.length), delta: "in the last " + Nav.range },
            { label: "People and systems acting", value: Theme.fmt(page.base.map(function (x) { return x.actor }).filter(function (v, i, a) { return a.indexOf(v) === i }).length) },
            { label: "Violations", value: Theme.fmt(page.base.filter(function (x) { return x.kind === "violation" }).length), delta: "restricted files found elsewhere",
              dc: page.base.some(function (x) { return x.kind === "violation" }) ? Theme.crit : undefined },
            { label: "Kept for", value: "90", unit: "days", delta: "the oldest go first" }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            title: page.kind ? Kinds.words[page.kind] : "Everything that happened"
            sub: Theme.fmt(page.shown.length) + " · newest first · click one to see it on the right"
            placeholder: "Filter by what, who or machine"
            tools: Select {
                width: 130
                small: true
                popupWidth: 200
                value: page.kind
                options: [{ value: "", label: "Every kind" }].concat(Kinds.keys.map(function (k) { return { value: k, label: Kinds.words[k] + " · " + page.base.filter(function (x) { return x.kind === k }).length } }))
                onPicked: function (v) { page.kind = v }
            }
            actionLabel: "Export"
            actionIcon: "download"
            actionPlain: true
            onAction: save.open()
            rows: page.shown
            rowKey: "rid"
            pick: page.e ? page.e.rid : null
            onPicked: function (k) { page.sel = k }
            icon: "history"
            nameTitle: "What happened"
            nameText: function (x) { return x.what }
            nameLine: function (x) { return x.actor + (x.host ? " · " + x.host : "") }
            cols: [{ title: "When", width: 120, text: function (x) { return Time.at(x.t) } }]
            nowTitle: "Kind"
            now: function (x) { return [Kinds.words[x.kind], Kinds.color(x.kind)] }
            showEmpty: page.base.length === 0
            emptyIcon: "history"
            emptyTitle: "Nothing recorded in this period"
            emptyText: "Everything the system records lands here: sessions, actions, flows, pings, updates, deviations and violations."
        }
        SidePanel {
            width: (parent.width - 14) * 4 / 12
            showEmpty: page.e === null
            emptyIcon: "history"
            emptyText: "Pick an event in the list."
            title: page.e ? page.e.what : ""
            sub: page.e && page.sel === page.e.rid ? "the one you picked" : "the first in the list · click another"
            facts: page.e ? [["When", Time.atDay(page.e.t)], ["Who", page.e.actor], ["Machine", page.e.host || "—", null, true], ["Kind", Kinds.words[page.e.kind]],
                             ["Recorded as", String(page.e.raw.action || ""), null, true]] : []
            actions: Btn {
                visible: page.e !== null && !!Fleet.byHost[page.e.host]
                text: page.e ? (Nav.boss ? "See it in Registry →" : "Open " + page.e.host + "'s page →") : ""
                onClicked: Nav.go("machines", page.e.host)
            }
        }
    }

    Panel {
        width: parent.width
        title: "Events over time"
        sub: page.brush ? "selected " + Time.hhmm(page.brush[0]) + " – " + Time.hhmm(page.brush[1]) : "drag across the chart to narrow the list"
        extra: Btn { visible: page.brush !== null; small: true; text: "Clear selection"; onClicked: page.brush = null }
        EventHistogram {
            width: parent.width
            height: 150
            entries: page.all
            kinds: page.kind ? [page.kind] : Kinds.keys
            range: Nav.range
            brush: page.brush
            onBrushed: function (b) { page.brush = b }
        }
    }
}
