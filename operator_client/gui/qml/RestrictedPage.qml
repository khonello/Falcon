import QtQuick
import "."

// RESTRICTED, at both levels: only what the person at this console marked. A file or folder is marked
// where it already is; nothing is copied into a special place. The mark keeps it to its machine or to
// its exact place, and a copy found anywhere else is an issue. The list, the mark beside it with its
// copies, and where it is drawn under both.
//
// With the Engine's marks (marks.list / marks.get) a mark is the person's own, its copies are issues,
// and a copy is dealt with through that issue's options (issues.get / issues.act). Without them, the
// marks are read from the copies found (resource.violations) and what cannot be done says so.
Page {
    id: page
    objectName: "restrictedView"

    property var vio: []
    property string sel: Nav.sub ? String(Nav.sub) : ""
    property string copy: ""
    property bool onlyCopied: false
    property var acted: ({})
    property bool allowing: false
    property string why: ""

    property var mk: null                 // marks.list, when the Engine has it
    property var msum: null
    property var mdet: null               // marks.get for the mark on the right
    property var cdet: null               // issues.get for the copy opened
    function load() {
        falcon.call("marks.list", {}, function (ok, r) {
            if (ok && r && r.marks) { page.mk = r.marks; page.msum = r.summary || null; page.loadDet(); return }
            page.mk = null
            falcon.call("resource.violations", { include_resolved: false }, function (ok2, r2) { page.vio = ok2 ? (r2.violations || []) : [] })
        })
    }
    function loadDet() {
        if (!cur || cur.mid === undefined) { mdet = null; return }
        var id = cur.mid
        falcon.call("marks.get", { mark_id: id }, function (ok, r) { if (ok && page.cur && page.cur.mid === id) page.mdet = r })
    }
    function loadCopy() {
        cdet = null
        if (!curCopy || curCopy.iid === undefined) return
        var id = curCopy.iid
        falcon.call("issues.get", { issue_id: id }, function (ok, r) { if (ok && page.curCopy && page.curCopy.iid === id) page.cdet = r })
    }
    onCurChanged: { if (!cur || !mdet || !mdet.mark || mdet.mark.id !== cur.mid) { mdet = null; loadDet() } }
    onCurCopyChanged: loadCopy()
    function play(o) {
        var c = curCopy
        var pl = { issue_id: c.iid, key: o.key }
        if (o.need === "reason") pl.reason = why.trim()
        falcon.call("issues.act", pl, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not done"); return }
            var a = Object.assign({}, page.acted); a[c.id] = o.title; page.acted = a
            page.allowing = false; page.why = ""; Msg.ok(o.title + " · recorded"); page.load(); Fleet.refresh()
        })
    }
    function changeKeep() {
        var k = cur, to = k.keep === "path" ? "machine" : "path"
        falcon.call("marks.keep_effect", { mark_id: k.mid, keep: to }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Cannot change it"); return }
            var e = r.effect || {}
            confirm.ask({ title: to === "path" ? "Allow " + k.name + " only where it is?" : "Allow " + k.name + " anywhere on " + k.host + "?",
                          text: (e.would_flag ? Theme.many(e.would_flag, "copy") + " would be caught. " : "") + (e.would_clear ? Theme.many(e.would_clear, "copy") + " would stop being caught. " : "")
                                + (!e.would_flag && !e.would_clear ? "No copy changes either way. " : "") + "Recorded.", ok: "Change it" },
                        function () { falcon.call("marks.change_keep", { mark_id: k.mid, keep: to }, function (ok2, r2) {
                            if (ok2) { Msg.ok("Changed · recorded"); page.load(); Fleet.refresh() } else Msg.failed(r2.message || "Not changed") }) })
        })
    }
    Component.onCompleted: load()
    Connections { target: falcon; function onPushReceived(type) { if (/^resource/.test(type)) page.load() } }

    // a mark per file name copies were found of, worst copy first
    readonly property var marks: mk !== null ? mk.map(function (m) {
        var cs = page.mdet && page.mdet.mark && page.mdet.mark.id === m.id ? page.mdet.copies.map(function (c) {
            return { id: String(c.issue_id), iid: c.issue_id, host: c.host, user: c.signed_in || "", folder: c.folder || c.path || "", file: c.file, at: c.opened_at,
                     sev: c.severity === "medium" ? "warning" : c.severity }
        }) : []
        return { id: String(m.id), mid: m.id, name: m.name, kind: m.kind, host: m.host, path: m.path, keep: m.keep, files: m.files, n: m.copies, copies: cs, versions: m.versions, by: m.by }
    }) : readVio()
    function readVio() {
        var by = {}, out = []
        vio.forEach(function (v) {
            var k = v.filename
            if (!by[k]) { by[k] = { id: k, name: k, kind: /\.[a-z0-9]+$/i.test(k) ? "file" : "folder", host: "", path: "", keep: "machine", files: 1, copies: [] }; out.push(by[k]) }
            var m = Fleet.byPc[v.found_on_pc_id] || { host: v.hostname, user: "" }
            by[k].copies.push({ id: String(v.violation_id), vid: v.violation_id, host: m.host || v.hostname, user: m.user, folder: v.path || "", file: v.filename,
                                at: v.detected_at, sev: v.resource_tag === "restricted" ? "critical" : "high" })
        })
        out.forEach(function (k) { k.copies.sort(function (a, b) { return Fleet.sevOrder[a.sev] - Fleet.sevOrder[b.sev] || Time.ms(b.at) - Time.ms(a.at) }); k.n = k.copies.length })
        return out.sort(function (a, b) { return b.n - a.n })
    }
    readonly property var rows: marks.filter(function (k) { return (!onlyCopied || k.n) && (k.name + " " + k.path).toLowerCase().indexOf(list.query.toLowerCase()) >= 0 })
    readonly property var cur: { for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; return rows.length ? rows[0] : null }
    readonly property var curCopy: { if (!cur) return null; for (var i = 0; i < cur.copies.length; i++) if (cur.copies[i].id === copy) return cur.copies[i]; return null }
    readonly property var allCopies: marks.reduce(function (a, k) { return a.concat(k.copies) }, [])
    readonly property var holders: (mk !== null ? Fleet.issues.filter(function (i) { return i.type === "file" }) : allCopies).map(function (c) { return c.host }).filter(function (h, i, a) { return a.indexOf(h) === i })

    Confirm { id: confirm; page: page }
    readonly property int copiesN: msum ? msum.copies : allCopies.length
    function allow(c) {
        falcon.call("resource.resolve", { violation_id: c.vid, reason: why.trim() }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not allowed"); return }
            var a = Object.assign({}, page.acted); a[c.id] = "Allowed on " + c.host + ": “" + page.why.trim() + "”"; page.acted = a
            page.allowing = false; page.why = ""; Msg.ok("Allowed on " + c.host + " · recorded"); Fleet.refresh()
        })
    }

    Strip {
        width: parent.width
        on: page.onlyCopied ? "copied" : null
        onPick: function (k) { page.onlyCopied = !!k }
        items: [
            { label: "Files and folders marked", value: Theme.fmt(page.marks.length), delta: page.mk !== null ? "by you" : page.marks.length ? "the ones copies were found of" : "", },
            { label: "Files protected in all", value: page.msum ? Theme.fmt(page.msum.files) : "—", delta: "counting what is inside folders" },
            { key: page.copiesN ? "copied" : null, label: "Copies found elsewhere", value: Theme.fmt(page.copiesN),
              delta: page.copiesN ? "click to list only those marks" : "none", dc: page.copiesN ? Theme.crit : undefined },
            { label: "Machines holding a copy", value: Theme.fmt(page.holders.length), unit: "/ " + Theme.fmt(Fleet.machines.length),
              delta: page.holders.length ? Theme.listNames(page.holders, 2) : "none", dc: page.holders.length ? Theme.crit : undefined }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            title: "Marked files"
            sub: "on your PC · click one to see it on the right"
            placeholder: "Filter by name or path"
            actionLabel: "Mark files"
            onAction: Nav.go("restricted", "mark")
            rows: page.rows
            pick: page.cur ? page.cur.id : null
            onPicked: function (k) { page.sel = k; page.copy = "" }
            icon: function (r) { return r.kind === "folder" ? "folder" : "file" }
            nameText: function (r) { return r.name }
            nameLine: function (r) { return r.path || "matched by content" }
            cols: [{ title: "Allowed", text: function (r) { return r.keep === "path" ? "Only in its place" : "Anywhere on the PC" } },
                   { title: "Covers", width: 150, bar: function (r) { return { v: r.files, max: Math.max(1, Math.max.apply(null, page.marks.map(function (k) { return k.files }))), text: r.kind === "folder" ? Theme.fmt(r.files) + " files" : "1 file" } } }]
            now: function (r) { return r.n ? [r.n === 1 ? "A copy elsewhere" : Theme.fmt(r.n) + " copies elsewhere", "bad"] : ["Only where it belongs", "good"] }
            showEmpty: page.marks.length === 0
            emptyIcon: "fileprotect"
            emptyTitle: "No copy of anything you marked has turned up"
            emptyText: "Mark a file or folder on your PC. It stays where it is and you keep using it; a copy anywhere else is caught."
            emptyAct: "Mark files"
            onEmptyAction: Nav.go("restricted", "mark")
        }
        SidePanel {
            width: (parent.width - 14) * 4 / 12
            readonly property var k: page.cur
            showEmpty: k === null
            emptyIcon: "fileprotect"
            emptyText: "Pick a marked file or folder in the list."
            title: k ? k.name : ""
            sub: k && page.sel === k.id ? "the one you picked" : "most copies · click another"
            facts: k ? [["Kind", k.kind === "folder" ? "Folder" : "File"], ["Allowed", k.keep === "path" ? "only in its place" : "anywhere on its PC"],
                        ["Copies", k.n ? k.n + " found elsewhere" : "None, only where it belongs", k.n ? Theme.crit : null]] : []
            actions: Btn { danger: true; text: "Unmark"; enabled: page.cur !== null && page.cur.mid !== undefined; tip: page.cur && page.cur.mid === undefined ? "This Engine cannot unmark" : ""
                           onClicked: { var k = page.cur
                                        confirm.ask({ title: "Unmark " + k.name + "?", text: "It stops being restricted. Its open copies close; the mark and its history are kept.", ok: "Unmark", danger: true },
                                                    function () { falcon.call("marks.unmark", { mark_id: k.mid }, function (ok, r) { if (ok) { Msg.ok(k.name + " unmarked"); page.sel = ""; page.load(); Fleet.refresh() } else Msg.failed(r.message || "Not unmarked") }) }) } }
            Column {
                visible: page.cur !== null && page.cur.n > 0
                width: parent.width
                spacing: 6
                Txt { text: "COPIES ELSEWHERE · CLICK ONE TO DEAL WITH IT"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Repeater {
                    model: page.cur ? page.cur.copies : []
                    Rectangle {
                        id: cc
                        required property var modelData
                        readonly property bool on: page.copy === modelData.id
                        readonly property string done: page.acted[modelData.id] || ""
                        width: parent.width
                        height: ch1.height + (on ? acts.height + 10 : 0) + 14
                        radius: 6
                        color: on ? Theme.surface2 : "transparent"
                        border.width: 1
                        border.color: on ? Theme.borderStrong : Theme.grid
                        Row {
                            id: ch1
                            x: 10; y: 7
                            width: parent.width - 20
                            spacing: 10
                            Rectangle { width: 7; height: 7; radius: 4; color: cc.done ? Theme.ok : Fleet.sevColor(modelData.sev); anchors.verticalCenter: parent.verticalCenter }
                            Column {
                                width: parent.width - 100
                                Txt { text: modelData.host; mono: true; font.weight: Font.Medium; width: parent.width }
                                Txt { text: modelData.folder || modelData.file; mono: true; color: Theme.text3; font.pixelSize: 11; width: parent.width }
                            }
                            Txt { text: cc.done ? "dealt with" : Time.age(modelData.at) + " ago"; mono: true; color: Theme.text3; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
                        }
                        MouseArea { anchors.fill: ch1; cursorShape: Qt.PointingHandCursor; onClicked: { page.copy = cc.on ? "" : modelData.id; page.allowing = false; page.why = "" } }
                        Column {
                            id: acts
                            visible: cc.on
                            x: 27; y: ch1.height + 12
                            width: parent.width - 37
                            spacing: 4
                            Txt { visible: cc.done !== ""; text: "✓ " + cc.done; color: Theme.ok; font.pixelSize: 12; width: parent.width }
                            // the Engine's options for this copy (it is an issue)
                            Column {
                                visible: cc.done === "" && !page.allowing && modelData.iid !== undefined
                                spacing: 4
                                Txt { visible: !page.cdet; text: "Loading what can be done…"; color: Theme.text3; font.pixelSize: 12 }
                                Repeater {
                                    model: page.cdet && page.curCopy && page.curCopy.id === modelData.id ? (page.cdet.options || []) : []
                                    Link { required property var modelData; text: modelData.title; font.pixelSize: 12
                                           onClicked: modelData.need === "reason" ? page.allowing = true : page.play(modelData) }
                                }
                            }
                            Column {
                                visible: cc.done === "" && !page.allowing && modelData.iid === undefined
                                spacing: 4
                                Txt { visible: !!modelData.user; text: "Ask " + modelData.user + " to delete it · not built yet"; color: Theme.text4; font.pixelSize: 12 }
                                Txt { text: "Delete this copy · not built yet"; color: Theme.text4; font.pixelSize: 12 }
                                Link { text: "Allow it on " + modelData.host; font.pixelSize: 12; onClicked: page.allowing = true }
                            }
                            Column {
                                visible: cc.done === "" && page.allowing
                                width: parent.width
                                spacing: 6
                                Field { width: parent.width; height: Theme.controlSm; placeholderText: "Why may it be on " + modelData.host + "? Recorded with it."; text: page.why; onTextEdited: page.why = text }
                                Row {
                                    anchors.right: parent.right
                                    spacing: 6
                                    Btn { small: true; text: "Cancel"; onClicked: { page.allowing = false; page.why = "" } }
                                    Btn { small: true; kind: "primary"; text: "Allow it"; enabled: page.why.trim() !== ""
                                          onClicked: { if (modelData.iid === undefined) { page.allow(modelData); return }
                                                       var o = (page.cdet && page.cdet.options || []).filter(function (x) { return x.need === "reason" })[0]
                                                       if (o) page.play(o) } }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Panel {
        visible: page.cur !== null
        width: parent.width
        title: page.cur ? "Where it is · " + page.cur.name : ""
        sub: page.cur ? (page.cur.n ? page.cur.n + " cop" + (page.cur.n === 1 ? "y" : "ies") + " found elsewhere" : "only where it belongs") + " · the same file as on the right" : ""
        Column {
            width: parent.width
            spacing: 12
            CopyMap {
                width: parent.width
                mark: page.cur
                copies: page.cur ? page.cur.copies : []
                picked: page.copy
                acted: page.acted
                onPick: function (id) { page.copy = id; page.allowing = false }
                onChangeKeep: page.cur && page.cur.mid !== undefined ? page.changeKeep() : Msg.warn("This Engine cannot keep a mark to one place")
            }
            Rectangle { width: parent.width; height: 1; color: Theme.border }
            Row {
                spacing: 18
                Txt { text: "Matched by content"; color: Theme.text3; font.pixelSize: 12 }
                Txt { text: "Every version is remembered, so editing the original never lets an older copy through."; color: Theme.text3; font.pixelSize: 12 }
            }
        }
    }
}
