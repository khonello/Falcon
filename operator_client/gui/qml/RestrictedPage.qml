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
    property string sel: { var a = Nav.takeArrive("restricted"); return a !== null ? String(a) : Nav.sub ? String(Nav.sub) : "" }
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
    onCurChanged: { if (!cur || !mdet || !mdet.mark || mdet.mark.id !== cur.mid) { mdet = null; loadDet() }; pickedKey = cur ? cur.id + ":" + copy : ""; loading = true; ldT.restart() }
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
        return { id: String(m.id), mid: m.id, name: m.name, kind: m.kind, host: m.host, pc: m.pc_id, path: m.path, keep: m.keep, files: m.files, n: m.copies, copies: cs,
                 tracked: m.tracked, generated: m.generated || 0, carried: m.carried_by || [], versions: m.versions, by: m.by, at: m.created_at }
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
    readonly property var rows: marks
    readonly property var cur: { for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; return rows.length ? rows[0] : null }
    readonly property var curCopy: { if (!cur) return null; for (var i = 0; i < cur.copies.length; i++) if (cur.copies[i].id === copy) return cur.copies[i]; return null }
    readonly property var allCopies: marks.reduce(function (a, k) { return a.concat(k.copies) }, [])
    readonly property var holders: (mk !== null ? Fleet.issues.filter(function (i) { return i.type === "file" }) : allCopies).map(function (c) { return c.host }).filter(function (h, i, a) { return a.indexOf(h) === i })

    Confirm { id: confirm; page: page }
    readonly property int copiesN: msum ? msum.copies : allCopies.length
    // this console's own PC, by name: where its marks are
    readonly property string myHost: { for (var i = 0; i < marks.length; i++) if (marks[i].pc === falcon.pcId) return marks[i].host
                                       var m = Fleet.byPc[falcon.pcId]; return m ? m.host : "" }
    readonly property int nFolders: marks.filter(function (k) { return k.kind === "folder" }).length
    readonly property int leaked: marks.filter(function (k) { return k.n > 0 }).length
    function where(k) { return k.kind === "folder" ? k.path : String(k.path || "").replace(/[^\\/]+$/, "") }
    function marked(k) { return (k.at ? Time.day(k.at) : "—") + " by " + (!k.by || k.by.you ? "you" : k.by.name || "someone") }
    function allow(c) {
        falcon.call("resource.resolve", { violation_id: c.vid, reason: why.trim() }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not allowed"); return }
            var a = Object.assign({}, page.acted); a[c.id] = "Allowed on " + c.host + ": “" + page.why.trim() + "”"; page.acted = a
            page.allowing = false; page.why = ""; Msg.ok("Allowed on " + c.host + " · recorded"); Fleet.refresh()
        })
    }

    // --- the version 1 concept's layout (docs/design/concepts-admin.html, AdminRestrictedPage) ----------------------------
    property string exp: ""
    property var det: ({})                // mark id -> marks.get, for every mark: its copies and the copies allowed
    property var cdets: ({})              // issue id -> issues.get, for the copies listed
    property string allowingId: ""
    function loadAll() {
        (mk || []).forEach(function (m) {
            falcon.call("marks.get", { mark_id: m.id }, function (ok, r) {
                if (!ok) return
                var d = Object.assign({}, page.det); d[m.id] = r; page.det = d
                ;(r.copies || []).forEach(function (c) {
                    falcon.call("issues.get", { issue_id: c.issue_id }, function (ok2, r2) { if (ok2) { var x = Object.assign({}, page.cdets); x[c.issue_id] = r2; page.cdets = x } })
                })
            })
        })
    }
    onMkChanged: loadAll()
    readonly property var allCopyRows: {
        var out = []
        marks.forEach(function (k) {
            var d = k.mid !== undefined ? page.det[k.mid] : null
            ;((d && d.copies) || []).forEach(function (c) { out.push({ k: k, c: c, id: String(c.issue_id) }) })
        })
        return out.sort(function (a, b) { return Fleet.sevOrder[a.c.severity === "medium" ? "warning" : a.c.severity] - Fleet.sevOrder[b.c.severity === "medium" ? "warning" : b.c.severity] || Time.ms(b.c.opened_at) - Time.ms(a.c.opened_at) })
    }
    readonly property var allowedRows: {
        var out = []
        marks.forEach(function (k) {
            var d = k.mid !== undefined ? page.det[k.mid] : null
            ;((d && d.resolved_copies) || []).forEach(function (c) { out.push({ k: k, c: c }) })
        })
        return out
    }
    readonly property var carrying: { var out = []; marks.forEach(function (k) { (k.carried || []).forEach(function (f) { out.push({ k: k, f: f }) }) }); return out }
    function hostsHit() { return allCopyRows.map(function (r) { return r.c.host }).filter(function (h, i, a) { return a.indexOf(h) === i }) }
    function ruleOf(k) { return k.keep === "machine" ? "may be anywhere on " + k.host + ", nowhere else" : "may be only in " + page.where(k) + " on " + k.host }
    function act(row, key, reason) {
        var pl = { issue_id: row.c.issue_id, key: key }
        if (reason) pl.reason = reason
        falcon.call("issues.act", pl, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not done"); return }
            var a = Object.assign({}, page.acted); a[row.id] = key === "ask" ? "Asked " + (row.c.signed_in || "them") + "; closes when the copy is gone" : key === "delete" ? "Deleted" : "Allowed there"; page.acted = a
            page.allowingId = ""; page.why = ""; Msg.ok(a[row.id] + " · recorded"); page.load(); Fleet.refresh()
        })
    }
    function option(row, key) {
        var d = page.cdets[row.c.issue_id]
        if (!d || !d.options) return null
        for (var i = 0; i < d.options.length; i++) if (d.options[i].key === key) return d.options[i]
        return null
    }
    function unmark(k) {
        confirm.ask({ title: "Stop restricting " + k.name + "?", text: "Copies of it are no longer looked for, and flows may carry it. " + (k.n ? "The copies already caught stay listed until you deal with them. " : "") + "The audit log records that you did it.",
                      ok: "Stop restricting", danger: true },
                    function () { falcon.call("marks.unmark", { mark_id: k.mid }, function (ok, r) {
                        if (!ok) { Msg.failed(r && r.message ? r.message : "Not changed"); return }
                        Msg.ok(k.name + " is no longer restricted · recorded"); page.load() }) })
    }
    property bool loading: false
    property string pickedKey: ""
    Timer { id: ldT; interval: Theme.loadMs; onTriggered: page.loading = false }

    situation: {
        if (!marks.length) return "You have not restricted anything yet. Restrict a file or folder below; it stays where it is and a copy anywhere else is caught."
        var hosts = marks.map(function (k) { return k.host }).filter(function (h, i, a) { return a.indexOf(h) === i }), hit = hostsHit()
        return "You restricted " + Theme.many(marks.length, "thing") + " on " + Theme.many(hosts.length, "machine") + ". "
               + (allCopyRows.length ? Theme.many(allCopyRows.length, "copy", "copies") + " turned up elsewhere, on " + Theme.listNames(hit, 2) + "." : "No copy is anywhere else.")
               + (allowedRows.length ? " " + Theme.many(allowedRows.length, "copy", "copies") + (allowedRows.length === 1 ? " is" : " are") + " allowed elsewhere." : "")
               + (carrying.length ? " " + Theme.listNames(carrying.map(function (c) { return c.f.name || ("flow " + c.f.flow_id) }), 2) + " carries something of yours." : "")
    }
    situationAt: Time.now

    // a copy's trail (rs-trail): where it was, how it went, where it was found, and who is there
    component Trail: Item {
        id: tr
        property string fromHost: ""
        property string fromName: ""
        property string how: ""
        property string toHost: ""
        property string toPath: ""
        property bool hot: false
        property string who: ""
        property string whoLine: ""
        property bool whyStyle: false
        readonly property real unit: (width - 150 - 120 - 30) / 2.4
        height: Math.max(a.height, c.height, d.height)
        Rectangle {
            id: a
            width: tr.unit; height: ac.height + 10; radius: Theme.radius; color: Theme.surface2
            anchors.verticalCenter: parent.verticalCenter
            Column { id: ac; x: 9; y: 5; width: parent.width - 18; spacing: 1
                Txt { width: parent.width; text: tr.fromHost; mono: true; font.pixelSize: 13; font.weight: Font.DemiBold }
                Txt { width: parent.width; text: tr.fromName; mono: true; font.pixelSize: 13; color: Theme.text3 } }
        }
        Item {
            x: tr.unit + 10; width: 150; height: parent.height
            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6
                Dash { width: (150 - hw.implicitWidth - 12) / 2; c: Theme.text4; anchors.verticalCenter: parent.verticalCenter }
                Txt { id: hw; text: tr.how; font.pixelSize: 12; color: Theme.text3; elide: Text.ElideNone }
                Dash { width: (150 - hw.implicitWidth - 12) / 2; c: Theme.text4; anchors.verticalCenter: parent.verticalCenter }
            }
        }
        Rectangle {
            id: c
            x: tr.unit + 10 + 150 + 10
            width: tr.unit * 1.4; height: cc.height + 10; radius: Theme.radius
            color: tr.hot ? Theme.mix(Theme.crit, Theme.surface2, 0.14) : Theme.surface2
            anchors.verticalCenter: parent.verticalCenter
            Column { id: cc; x: 9; y: 5; width: parent.width - 18; spacing: 1
                Txt { width: parent.width; text: tr.toHost; mono: true; font.pixelSize: 13; font.weight: Font.DemiBold; color: tr.hot ? Theme.crit : Theme.text }
                Txt { width: parent.width; text: tr.toPath; mono: true; font.pixelSize: 13 } }
        }
        Column {
            id: d
            x: tr.unit * 2.4 + 10 + 150 + 10 + 10
            width: 120
            anchors.verticalCenter: parent.verticalCenter
            Txt { width: parent.width; text: tr.who; font.pixelSize: 12; color: tr.whyStyle ? Theme.text2 : Theme.text; font.italic: tr.whyStyle }
            Txt { width: parent.width; text: tr.whoLine; font.pixelSize: 12; color: Theme.text3 }
        }
    }

    Row {
        width: parent.width
        spacing: 14
        // --- what you restricted, by the machine it lives on --------------------------------------------------
        Box {
            id: markP
            objectName: "markCards"
            width: (parent.width - 14) * 8 / 12
            height: Math.max(implicitHeight, mapP.implicitHeight)
            title: "What you restricted"
            sub: "everything you marked restricted, by the machine it lives on; click one to see it on the right, expand it for its rule and what happened to it"
            Repeater {
                model: page.marks.map(function (k) { return k.host }).filter(function (h, i, a) { return a.indexOf(h) === i }).sort(function (a, b) { return (b === page.myHost) - (a === page.myHost) || a.localeCompare(b) })
                delegate: Group {
                    id: hg
                    required property var modelData
                    required property int index
                    readonly property var xs: page.marks.filter(function (k) { return k.host === modelData }).sort(function (a, b) { return a.name.localeCompare(b.name) })
                    width: markP.innerW
                    spaced: index > 0
                    cardGap: 5
                    title: modelData + " · " + xs.length
                    sub: modelData === page.myHost ? "yours" : (Fleet.byHost[modelData] || {}).user || "nobody signed in"
                    Repeater {
                        model: hg.xs
                        delegate: Card {
                            id: kc
                            required property var modelData
                            objectName: "mark_" + modelData.id
                            width: hg.cardW
                            midW: 200
                            actW: 150
                            padV: 7
                            icon: modelData.kind === "folder" ? "folder" : "file"
                            title: modelData.name
                            tag: modelData.kind === "folder" ? Theme.many(modelData.files || 0, "file") : "file"
                            line: modelData.path
                            picked: page.cur !== null && page.cur.id === modelData.id
                            expandable: true
                            expanded: page.exp === modelData.id
                            onOpen: { page.sel = modelData.id; page.copy = "" }
                            onToggle: { page.sel = modelData.id; page.exp = expanded ? "" : modelData.id }
                            mid: Row {
                                anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right
                                spacing: 14
                                Txt { text: kc.modelData.keep === "machine" ? "anywhere on " + kc.modelData.host : "only where it is"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                                Txt { text: kc.modelData.at ? "since " + Time.day(kc.modelData.at) : ""; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                            }
                            // opened: its rule, what happened to it lately, and Stop restricting
                            Column {
                                width: parent.width
                                spacing: 10
                                Column {
                                    y: 2
                                    width: Math.min(parent.width, 420)
                                    Repeater {
                                        model: [["Where", kc.modelData.host + " " + kc.modelData.path], ["Rule", "It " + page.ruleOf(kc.modelData)],
                                                ["Covers", kc.modelData.kind === "folder" ? Theme.many(kc.modelData.files || 0, "file") + ", and any added later" : "1 file"],
                                                ["Restricted", page.marked(kc.modelData)], ["Recognised by", "content" + (kc.modelData.versions ? ", " + Theme.many(kc.modelData.versions, "version") + " remembered" : "")]]
                                        delegate: Item {
                                            required property var modelData
                                            required property int index
                                            width: parent.width
                                            height: fv.height + 10
                                            Txt { y: 5; width: 120; text: modelData[0]; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                                            Txt { id: fv; x: 132; y: 5; width: parent.width - 132; text: modelData[1]; font.pixelSize: 13; mono: index === 0; wrapMode: Text.WrapAnywhere; elide: Text.ElideNone }
                                            Rectangle { visible: index < 4; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                                        }
                                    }
                                }
                                Column {
                                    width: parent.width
                                    readonly property var log: page.det[kc.modelData.mid] && page.det[kc.modelData.mid].events ? page.det[kc.modelData.mid].events : []
                                    Txt { topPadding: 4; text: "Lately"; color: Theme.text3; font.pixelSize: 12 }
                                    Repeater {
                                        model: parent.log
                                        delegate: Item {
                                            required property var modelData
                                            width: parent.width; height: lv.height + 10
                                            Txt { y: 5; width: 90; text: Time.ago(modelData.at); color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                                            Txt { id: lv; x: 100; y: 5; width: parent.width - 100; textFormat: Text.StyledText; font.pixelSize: 13; text: "<b>" + (modelData.who || "") + "</b> " + (modelData.what || "") }
                                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                                        }
                                    }
                                    Txt { visible: parent.log.length === 0; text: "Nothing has happened to it since you restricted it."; color: Theme.text3; font.pixelSize: 13 }
                                }
                                Rectangle { width: parent.width; height: 1; color: Theme.border }
                                Btn { anchors.right: parent.right; small: true; danger: true; iconName: "stop"; text: "Stop restricting"; onClicked: page.unmark(kc.modelData) }
                            }
                        }
                    }
                }
            }
            Quiet { visible: page.marks.length === 0; text: "Nothing restricted yet. Restrict something below." }
        }
        // --- where it is, across every machine -----------------------------------------------------------------
        Box {
            id: mapP
            objectName: "markMap"
            width: (parent.width - 14) * 4 / 12
            height: Math.max(implicitHeight, markP.implicitHeight)
            title: "Where it is, across every machine"
            readonly property var copies: page.cur && page.cur.mid !== undefined && page.det[page.cur.mid] ? page.det[page.cur.mid].copies || [] : []
            readonly property var allowedHere: page.cur && page.cur.mid !== undefined && page.det[page.cur.mid] ? page.det[page.cur.mid].resolved_copies || [] : []
            sub: page.cur ? page.cur.name + " · " + (copies.length ? Theme.many(copies.length, "copy", "copies") + " away from home" : "only at home") : "pick something on the left"
            Column {
                width: parent.width
                spacing: 0
                opacity: page.loading ? 0 : 1
                readonly property var others: Fleet.machines.map(function (m) { return m.host }).sort()
                readonly property var admins: page.marks.map(function (k) { return k.host }).filter(function (h, i, a) { return a.indexOf(h) === i && Fleet.byHost[h] === undefined })
                Repeater {
                    model: [["ADMIN PCS", parent.admins], ["OTHER MACHINES", parent.others]]
                    delegate: Column {
                        required property var modelData
                        required property int index
                        visible: modelData[1].length > 0
                        width: mapP.innerW
                        spacing: 8
                        topPadding: index > 0 ? 14 : 0
                        bottomPadding: 10
                        Txt { text: modelData[0]; color: Theme.text4; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                        Flow {
                            width: parent.width
                            spacing: 10
                            Repeater {
                                model: parent.parent.modelData[1]
                                delegate: Rectangle {
                                    required property var modelData
                                    readonly property bool home: page.cur !== null && page.cur.host === modelData
                                    readonly property var cp: mapP.copies.filter(function (c) { return c.host === modelData })[0] || null
                                    readonly property bool ok: mapP.allowedHere.some(function (c) { return c.host === modelData })
                                    width: 42; height: 42; radius: 7
                                    color: home ? Theme.mix(Theme.accent, Theme.surface3, 0.28) : cp ? Theme.mix(Theme.crit, Theme.surface3, 0.28) : ok ? Theme.mix(Theme.ok, Theme.surface3, 0.26) : Theme.surface3
                                    border.width: cp && page.copy === String(cp.issue_id) ? 1.5 : 0
                                    border.color: Theme.crit
                                    Txt { anchors.centerIn: parent; width: parent.width - 4; horizontalAlignment: Text.AlignHCenter; text: modelData.replace(/^WS-[A-Z]+-/, "").replace(/^[A-Z]+-/, ""); mono: true; font.pixelSize: 11
                                          font.weight: parent.home || parent.cp || parent.ok ? Font.DemiBold : Font.Normal
                                          color: parent.home ? Theme.accent : parent.cp ? Theme.crit : parent.ok ? Theme.ok : Theme.text3 }
                                    MouseArea { anchors.fill: parent; cursorShape: parent.cp ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: if (parent.cp) page.copy = String(parent.cp.issue_id) }
                                    Tip { text: modelData + (parent.home ? " · its home" : parent.cp ? " · a copy" : parent.ok ? " · a copy you allowed" : "") }
                                }
                            }
                        }
                    }
                }
                Row {
                    spacing: 16
                    topPadding: 4
                    Repeater {
                        model: [["its home", Theme.mix(Theme.accent, Theme.surface3, 0.28)], ["a copy caught", Theme.mix(Theme.crit, Theme.surface3, 0.28)], ["a copy you allowed", Theme.mix(Theme.ok, Theme.surface3, 0.26)]]
                        delegate: Row { required property var modelData; spacing: 6
                            Rectangle { width: 11; height: 11; radius: 3; color: modelData[1]; anchors.verticalCenter: parent.verticalCenter }
                            Txt { text: modelData[0]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
                    }
                }
            }
            Loading { parent: mapP; on: page.loading && page.cur !== null; under: mapP.headerHeight }
            Pulse { parent: mapP; key: page.loading ? null : page.pickedKey || null }
        }
    }

    // --- copies on other machines --------------------------------------------------------------------------
    Box {
        objectName: "copiesElsewhere"
        width: parent.width
        title: "Copies on other machines"
        sub: page.allCopyRows.length ? "worst first; where it was, how it went, where it was found; click one to see it on the machines" : "no copy of anything you restricted is anywhere else"
        Column {
            width: parent.width
            spacing: 4
            Repeater {
                model: page.allCopyRows
                delegate: Rectangle {
                    id: cr
                    required property var modelData
                    readonly property string done: page.acted[modelData.id] || ""
                    width: parent.width
                    height: (page.allowingId === modelData.id ? Math.max(trl.height, 24) : Math.max(trl.height, acts.height)) + 16
                    radius: Theme.radiusLg
                    color: page.copy === modelData.id ? Theme.surface3 : "transparent"
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { page.sel = cr.modelData.k.id; page.copy = cr.modelData.id } }
                    Trail {
                        id: trl
                        x: 10; y: 8
                        width: parent.width - 20 - acts.width - 14
                        opacity: cr.done !== "" ? 0.55 : 1
                        fromHost: cr.modelData.k.host; fromName: cr.modelData.k.name
                        how: cr.modelData.c.how || "copied"
                        toHost: cr.modelData.c.host; toPath: (cr.modelData.c.folder || cr.modelData.c.path || "") + (cr.modelData.c.file ? "\\" + cr.modelData.c.file : "")
                        hot: cr.done === ""
                        who: cr.modelData.c.signed_in || "nobody signed in"; whoLine: Time.ago(cr.modelData.c.opened_at)
                    }
                    Row {
                        id: acts
                        anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                        spacing: 6
                        Row {
                            visible: cr.done !== ""; spacing: 6
                            Icon { name: "check"; size: 12; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                            Txt { text: cr.done; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                        }
                        Field { visible: cr.done === "" && page.allowingId === cr.modelData.id; small: true; width: 240; placeholderText: "Why may it stay on " + cr.modelData.c.host + "?"; text: page.why; onTextEdited: page.why = text }
                        Btn { visible: cr.done === "" && page.allowingId === cr.modelData.id; small: true; text: "Cancel"; onClicked: { page.allowingId = ""; page.why = "" } }
                        Btn { visible: cr.done === "" && page.allowingId === cr.modelData.id; small: true; kind: "primary"; text: "Allow it"; enabled: page.why.trim() !== ""; onClicked: page.act(cr.modelData, "allow", page.why.trim()) }
                        Repeater {
                            model: cr.done !== "" || page.allowingId === cr.modelData.id ? [] : [["ask", "Ask " + (cr.modelData.c.signed_in || "them") + " to delete it", false], ["delete", "Delete the copy", true], ["allow", "Allow it there", false]]
                            delegate: Btn {
                                required property var modelData
                                readonly property var o: page.option(cr.modelData, modelData[0])
                                small: true; danger: modelData[2]; text: modelData[1]
                                enabled: o !== null && !o.cannot
                                tip: o === null ? (modelData[0] === "ask" ? "Nobody is signed in to ask" : "Not offered for this copy") : o.cannot ? o.cannot : ""
                                onClicked: modelData[0] === "allow" ? (page.allowingId = cr.modelData.id, page.why = "")
                                         : modelData[0] === "delete" ? confirm.ask({ title: "Delete the copy on " + cr.modelData.c.host + "?", text: "Only " + cr.modelData.c.file + " on " + cr.modelData.c.host + " is deleted. What you restricted is not touched.", ok: "Delete the copy", danger: true },
                                                                                   function () { page.act(cr.modelData, "delete", "") })
                                         : page.act(cr.modelData, "ask", "")
                            }
                        }
                    }
                }
            }
            Quiet { visible: page.allCopyRows.length === 0; icon: "check"; text: "Nothing you restricted has been found anywhere else." }
        }
    }

    // --- allowed copies --------------------------------------------------------------------------------------
    Box {
        objectName: "allowedCopies"
        width: parent.width
        title: "Allowed copies"
        sub: "copies found away from home that you let stay, newest first, each with the reason you gave; they are not caught again unless you take it back"
        Column {
            width: parent.width
            spacing: 4
            Repeater {
                model: page.allowedRows
                delegate: Item {
                    required property var modelData
                    width: parent.width
                    height: Math.max(at.height, 24) + 16
                    Trail {
                        id: at
                        x: 10; y: 8
                        width: parent.width - 20 - tb.width - 14
                        fromHost: modelData.k.host; fromName: modelData.k.name
                        how: "allowed" + (modelData.c.allowed_at ? " " + Time.atDay(modelData.c.allowed_at) : "")
                        toHost: modelData.c.host; toPath: (modelData.c.folder || modelData.c.path || "") + (modelData.c.file ? "\\" + modelData.c.file : "")
                        who: modelData.c.reason ? "“" + modelData.c.reason + "”" : ""; whoLine: modelData.c.signed_in || ""
                        whyStyle: true
                    }
                    Btn { id: tb; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; small: true; text: "Take it back"; enabled: false; tip: "The Engine cannot take an allowance back yet" }
                }
            }
            Quiet { visible: page.allowedRows.length === 0; text: "You have not allowed a copy anywhere else." }
        }
    }

    // --- flows carrying what you restricted (rs-fl) ------------------------------------------------------------
    Box {
        objectName: "flowsCarrying"
        width: parent.width
        title: "Flows carrying what you restricted"
        sub: "right now; a flow held at something of yours waits for you to allow it, for that flow only"
        Column {
            width: parent.width
            Repeater {
                model: page.carrying
                delegate: Item {
                    required property var modelData
                    required property int index
                    width: parent.width
                    height: Math.max(34, lt.height) + 18
                    Rectangle { x: 4; width: 34; height: 34; radius: 17; color: Theme.surface3; anchors.verticalCenter: parent.verticalCenter
                                Icon { anchors.centerIn: parent; name: "branches"; size: 15; color: Theme.text2 } }
                    Column {
                        id: lt
                        x: 50; anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 50 - 150 - 12 - ob.width - 16
                        spacing: 2
                        Txt { width: parent.width; textFormat: Text.StyledText; font.pixelSize: 13; text: "<b>" + (modelData.f.name || "flow " + modelData.f.flow_id) + "</b> carries <b>" + modelData.k.name + "</b>" }
                        Txt { width: parent.width; mono: true; color: Theme.text3; font.pixelSize: 12; text: modelData.k.host + " " + modelData.k.path }
                    }
                    Column {
                        x: parent.width - 150 - 12 - ob.width - 4; width: 150
                        anchors.verticalCenter: parent.verticalCenter
                        Txt { width: parent.width; horizontalAlignment: Text.AlignRight; text: "allowed"; font.pixelSize: 12; font.weight: Font.DemiBold }
                    }
                    Btn { id: ob; anchors.right: parent.right; anchors.rightMargin: 4; anchors.verticalCenter: parent.verticalCenter; small: true; text: "Open in Flows"
                          onClicked: Nav.goAsk("flows", null, "Flows opens with this flow picked.", String(modelData.f.flow_id || modelData.f.id)) }
                    Rectangle { visible: index < page.carrying.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                }
            }
            Quiet { visible: page.carrying.length === 0; text: "No flow carries anything you restricted." }
        }
    }

    // --- restrict something: a few careful steps, so it has its own page ---------------------------------------
    Box {
        objectName: "restrictSomething"
        width: parent.width
        accentFoot: true
        title: "Restrict something"
        sub: "it stays where it is and you keep using it; a copy anywhere else is caught"
        GiveSteps {
            steps: [["Pick what to restrict", "a file or a folder on this PC, found by a search or picked in Explorer"], ["Say where it may be", "only exactly where it is, or anywhere on this PC"], ["Check and restrict", "copies already elsewhere are found and listed straight away"]]
            act: "Restrict something"
            onGo: Nav.go("restricted", "mark")
        }
    }
}
