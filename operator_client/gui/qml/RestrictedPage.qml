import QtQuick
import "."

// PROTECTED FILES (the page's key stays "restricted", so every link to it still lands here; the user, 10 Nov 2026). A file or folder is
// marked where it already is; nothing is copied into a special place. A mark is one of the Engine's three tags (marks.*'s protection):
//   Restricted  kept to its machine or its exact place; a copy found anywhere else is an issue, and no flow carries it unallowed
//   Private     only the people named may open it; Windows refuses anyone else, and each refusal is noted (marks.readers changes who)
//   Watch       nothing is refused; every change, copy and move is noted under it
// The list, the mark beside it with its copies, and where it is drawn under both. Copies, allowed copies and flows are Restricted's alone.
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
        falcon.call("marks.list", { scope: "all" }, function (ok, r) {
            if (ok && r && r.marks) {
                page.mk = r.marks; page.msum = r.summary || null; page.loadDet()
                falcon.call("flow.restricted_waiting", {}, function (ok2, r2) { page.heldFlows = ok2 ? (r2.waiting || []) : [] })
                return
            }
            page.mk = null
            page.heldFlows = []
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
    Connections { target: falcon; function onPushReceived(type) { if (/^resource|^private\.|^mark\./.test(type)) page.load() } }

    // a mark per file name copies were found of, worst copy first
    readonly property var marks: mk !== null ? mk.map(function (m) {
        var cs = page.mdet && page.mdet.mark && page.mdet.mark.id === m.id ? page.mdet.copies.map(function (c) {
            return { id: String(c.issue_id), iid: c.issue_id, host: c.host, user: c.signed_in || "", folder: c.folder || c.path || "", file: c.file, at: c.opened_at,
                     sev: c.severity === "medium" ? "warning" : c.severity }
        }) : []
        return { id: String(m.id), mid: m.id, name: m.name, kind: m.kind, host: m.host, pc: m.pc_id, path: m.path, keep: m.keep, files: m.files, n: m.copies, copies: cs,
                 tracked: m.tracked, generated: m.generated || 0, carried: m.carried_by || [], versions: m.versions, by: m.by, at: m.created_at,
                 prot: m.protection || "restricted", readers: m.readers || [], refusals: m.refusals || [], applied: m.applied || null, allowSystem: m.allow_system !== false }
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
    // what only a Restricted mark has: copies looked for, copies allowed, flows held
    readonly property var rmarks: marks.filter(function (k) { return !k.prot || k.prot === "restricted" })
    function countOf(p) { return marks.filter(function (k) { return (k.prot || "restricted") === p }).length }
    // the list's filter: every tag, or one
    // always one kind on screen, never a mix (the user, 11 Nov 2026): its list, its panel on the right and its sections under them. It opens
    // on Restricted, or on the first kind that has anything; a mark arrived at from elsewhere brings its own kind.
    property string show: "restricted"
    readonly property var shownMarks: marks.filter(function (k) { return (k.prot || "restricted") === show })
    function syncShow() {
        for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) { show = rows[i].prot || "restricted"; return }
        if (countOf(show) === 0) { var k = ["restricted", "private", "watch"].filter(function (x) { return page.countOf(x) > 0 })[0]; if (k) show = k }
    }
    onSelChanged: syncShow()
    readonly property var protWords: ({ restricted: ["Restricted", "stop"], "private": ["Private", "lock"], watch: ["Watch", "eye"] })
    function protWord(k) { return (protWords[k.prot || "restricted"] || protWords.restricted)[0] }
    function protIcon(k) { return (protWords[k.prot || "restricted"] || protWords.restricted)[1] }
    function readerNames(k) { return (k.readers || []).map(function (r) { return r.account_id === falcon.accountId ? "you" : r.name || "account " + r.account_id }) }
    // what the mark's machine did with a Private mark (marks.list's applied)
    function appliedWord(k) {
        var a = k.applied
        if (!a) return "being set on " + k.host
        if (a.waiting) return "waiting: " + a.waiting
        if (!a.ok) return "not set on " + k.host + (a.error ? ": " + a.error : "")
        return "set on " + k.host + (a.at ? " " + page.agoWord(a.at) : "") + (a.missing && a.missing.length ? "; " + Theme.many(a.missing.length, "person", "people") + " left out until their Windows name is known" : "")
    }
    // across the marks of a kind: what was refused (Private) and what happened (Watch), newest first, each with its mark
    readonly property var allRefusals: marks.filter(function (k) { return k.prot === "private" }).reduce(function (o, k) {
        return o.concat((k.refusals || []).map(function (r) { return { k: k, r: r } })) }, []).sort(function (a, b) { return Time.ms(b.r.at) - Time.ms(a.r.at) })
    readonly property var watchLately: marks.filter(function (k) { return k.prot === "watch" }).reduce(function (o, k) {
        var d = k.mid !== undefined ? page.det[k.mid] : null
        return o.concat(((d && d.lately) || []).map(function (e) { return { k: k, e: e } })) }, []).sort(function (a, b) { return Time.ms(b.e.at) - Time.ms(a.e.at) })
    // what happened to a protected file, in words (the user, 12 Nov 2026: "I can't deduce what each entry means"): the file and what
    // happened to it, then who was signed in on the machine at the time -- Falcon knows who was signed in, not whose hand it was, so it
    // says so -- when, and where. `e` is one of marks.get's lately: {what, path, at, who, where}; `k` the mark it belongs to.
    function happened(e, k) {
        var f = e.path ? String(e.path).replace(/[\\/]+$/, "").replace(/^.*[\\/]/, "") : (k ? k.name : "it")
        var w = String(e.what || "")
        var head = w === "changed" ? f + " was changed"
                 : w === "copied" ? "A copy of " + f + " was made"
                 : w === "moved or renamed" ? f + " was moved or renamed"
                 : w === "deleted" ? f + " was deleted"
                 : w === "a file added" ? f + " was added" + (k && k.kind === "folder" && f !== k.name ? " to " + k.name : "")
                 : w === "a flow held at it" ? "A flow stopped at it, to wait for an Admin to allow it"
                 : f + " " + w
        var who = e.who ? (e.who === Nav.myName ? "while you were signed in" : "while " + e.who + " was signed in") : e.path ? "nobody was signed in" : ""
        var place = (k && k.kind === "folder" && f !== k.name ? "in " + k.name + " " : "") + "on " + (e.where || (k ? k.host : "its machine"))
        return { head: head, who: who, place: place, when: page.agoWord(e.at) }       // a file's name is said as it is spelled, never capitalised
    }
    function latelyOf(k) { var d = k && k.mid !== undefined ? page.det[k.mid] : null; return (d && d.lately) || [] }
    function showing(kind) { return page.show === kind }
    function recentRefusals() { var wk = Time.now - 7 * 86400000; return marks.reduce(function (n, k) { return n + (k.refusals || []).filter(function (r) { return Time.ms(r.at) >= wk }).length }, 0) }
    // opens on what has the most copies away from home
    readonly property var byCopies: marks.slice().sort(function (a, b) { return b.n - a.n || a.name.localeCompare(b.name) })
    readonly property var cur: { var xs = byCopies.filter(function (k) { return (k.prot || "restricted") === page.show })
                                 for (var i = 0; i < xs.length; i++) if (xs[i].id === sel) return xs[i]; return xs.length ? xs[0] : null }
    readonly property var curCopy: { if (!cur) return null; for (var i = 0; i < cur.copies.length; i++) if (cur.copies[i].id === copy) return cur.copies[i]; return null }
    readonly property var allCopies: marks.reduce(function (a, k) { return a.concat(k.copies) }, [])
    readonly property var holders: (mk !== null ? Fleet.issues.filter(function (i) { return i.type === "file" }) : allCopies).map(function (c) { return c.host }).filter(function (h, i, a) { return a.indexOf(h) === i })

    Confirm { id: confirm; page: page }
    readonly property int copiesN: msum ? msum.copies : allCopies.length
    // this console's own PC, by name: where its marks are
    readonly property string myHost: { for (var i = 0; i < marks.length; i++) if (marks[i].pc === falcon.pcId) return marks[i].host
                                       var m = Fleet.byPc[falcon.pcId]; return m ? m.host : "" }
    readonly property int nFolders: marks.filter(function (k) { return k.kind === "folder" }).length
    readonly property int leaked: rmarks.filter(function (k) { return k.n > 0 }).length
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
    onMkChanged: { loadAll(); syncShow() }
    readonly property var allCopyRows: {
        var out = []
        rmarks.forEach(function (k) {
            var d = k.mid !== undefined ? page.det[k.mid] : null
            ;((d && d.copies) || []).forEach(function (c) { out.push({ k: k, c: c, id: String(c.issue_id) }) })
        })
        return out.sort(function (a, b) { return Fleet.sevOrder[a.c.severity === "medium" ? "warning" : a.c.severity] - Fleet.sevOrder[b.c.severity === "medium" ? "warning" : b.c.severity] || Time.ms(b.c.opened_at) - Time.ms(a.c.opened_at) })
    }
    readonly property var allowedRows: {
        var out = []
        rmarks.forEach(function (k) {
            var d = k.mid !== undefined ? page.det[k.mid] : null
            ;((d && d.allowed) || []).forEach(function (c) { out.push({ k: k, c: c }) })
        })
        return out.sort(function (a, b) { return Time.ms(b.c.at) - Time.ms(a.c.at) })
    }
    // flows you let carry something of yours, then the ones held at it, waiting for you
    property var heldFlows: []
    readonly property var carrying: {
        var out = []
        rmarks.forEach(function (k) {
            var d = k.mid !== undefined ? page.det[k.mid] : null
            ;((d && d.flows_allowed) || []).forEach(function (f) { out.push({ k: k, f: f, held: false }) })
        })
        return out.concat(heldFlows.map(function (f) { return { k: null, f: f, held: true } }))
    }
    // every machine: the Admins' own apart at the top, then everyone else's by department, as the Departments page draws a machine
    readonly property var admTiles: Fleet.depts.reduce(function (o, d) { return o.concat((d.admins || []).filter(function (a) { return a.hostname }).map(function (a) { return { h: a.hostname, who: a.account_id === falcon.accountId ? "you" : a.name } })) }, [])
    readonly property var mapDepts: {
        var seen = {}, adm = admTiles.map(function (x) { return x.h })
        adm.forEach(function (h) { seen[h] = true })
        var out = [{ name: "Admins", hs: adm }].concat(Fleet.depts.map(function (d) {
            var hs = (d.machines || []).map(function (m) { return m.host }).filter(function (h) { return !seen[h] })
            hs.forEach(function (h) { seen[h] = true })
            return { name: d.name, hs: hs }
        }))
        out.push({ name: "In no department", hs: Fleet.machines.map(function (m) { return m.host }).filter(function (h) { return !seen[h] }) })
        return out.filter(function (g) { return g.hs.length > 0 })
    }
    function ownerOf(h) { return h === myHost ? "you" : (admTiles.filter(function (x) { return x.h === h })[0] || {}).who || (Fleet.byHost[h] || {}).user || "nobody signed in" }
    // what is listed, five marks a page, by the machine they live on (your own first)
    property int pg: 0
    readonly property var hostOrder: shownMarks.map(function (k) { return k.host }).filter(function (h, i, a) { return a.indexOf(h) === i }).sort(function (a, b) { return (b === page.myHost) - (a === page.myHost) || a.localeCompare(b) })
    readonly property var ordered: hostOrder.reduce(function (o, h) { return o.concat(shownMarks.filter(function (k) { return k.host === h }).sort(function (a, b) { return a.name.localeCompare(b.name) })) }, [])
    // page sizes follow the screen (Theme.viewScale; the user, 11 Nov 2026): five marks and eight copies on the design's 900-high window
    readonly property int perM: Math.max(2, Math.round(5 * Theme.viewScale))
    readonly property int perC: Math.max(2, Math.round(8 * Theme.viewScale))
    readonly property int pages: Math.max(1, Math.ceil(ordered.length / perM))
    readonly property int pi: Math.min(pg, pages - 1)
    readonly property var markPage: ordered.slice(pi * perM, pi * perM + perM)
    property int pgC: 0
    property int pgA: 0
    readonly property int pagesC: Math.max(1, Math.ceil(allCopyRows.length / perC))
    readonly property int pagesA: Math.max(1, Math.ceil(allowedRows.length / perC))
    readonly property int piC: Math.min(pgC, pagesC - 1)
    readonly property int piA: Math.min(pgA, pagesA - 1)
    function hostsHit() { return allCopyRows.map(function (r) { return r.c.host }).filter(function (h, i, a) { return a.indexOf(h) === i }) }
    // when something happened: how long ago today, else the day and the time
    function agoWord(x) { var h = (Time.now - Time.ms(x)) / 3600000; return h < 24 ? Time.dur(h) + " ago" : Time.dayName(x) + " " + Time.hhmm(x) }
    // how a copy got there, in a few words between the boxes (the user, 12 Nov 2026: the sentence ran over them); the Engine's whole
    // sentence (came_by.said: "copied over the network from \FS-01\share") is on hover
    readonly property var howWords: ({ flow: "by a flow", usb: "from a USB drive", network: "over the network", conversation: "in a conversation",
                                       email_or_download: "email or download", on_machine: "on the machine" })
    function howOf(c) { return c.came_by && howWords[c.came_by.how] || "copied" }
    function howSaid(c) { return c.came_by && c.came_by.said && c.came_by.said !== "not known" ? c.came_by.said : "" }
    function allowedSince(x) { return Time.sameDay(Time.ms(x), Time.now) ? "today " + Time.hhmm(x) : Time.day(x) }
    function pickCopy(r) { page.sel = r.k.id; page.copy = r.id }
    function letFlow(c) {
        falcon.call("flow.restricted_consent", { consent_id: c.f.id, grant: true }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not done"); return }
            Msg.ok(c.f.name + " may carry " + c.f.what + "; it goes on now"); page.load()
        })
    }
    function takeBack(r) {
        confirm.ask({ title: "Take back the allowance on " + r.c.host + "?", text: "The copy on " + r.c.host + " is caught again and listed under Copies on other machines.", ok: "Take it back", danger: true },
                    function () { falcon.call("marks.allow_revoke", { mark_id: r.k.mid, allowance_id: r.c.allowance_id }, function (ok, res) {
                        if (!ok) { Msg.failed(res && res.message ? res.message : "Not done"); return }
                        Msg.ok("Taken back; the copy on " + r.c.host + " is caught again"); page.load() }) })
    }
    function ruleOf(k) { return k.keep === "machine" ? "may be anywhere on " + k.host + ", nowhere else" : "may be only in " + page.where(k) + " on " + k.host }
    function act(row, key, reason) {
        var pl = { issue_id: row.c.issue_id, key: key }
        if (reason) pl.reason = reason
        falcon.call("issues.act", pl, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not done"); return }
            var a = Object.assign({}, page.acted); a[row.id] = key === "delete" ? "Deleted" : "Allowed there"; page.acted = a
            page.allowingId = ""; page.why = ""; Msg.ok(a[row.id] + " · recorded"); page.load(); Fleet.refresh()
        })
    }
    function option(row, key) {
        var d = page.cdets[row.c.issue_id]
        if (!d || !d.options) return null
        for (var i = 0; i < d.options.length; i++) if (d.options[i].key === key) return d.options[i]
        return null
    }
    function stopWord(k) { return k.prot === "private" ? "Stop keeping it private" : k.prot === "watch" ? "Stop watching" : "Stop restricting" }
    function unmark(k) {
        var say = k.prot === "private" ? ["Stop keeping " + k.name + " private?", "Its machine puts back the permissions it had before, so whoever could open it then can open it again. "]
                : k.prot === "watch" ? ["Stop watching " + k.name + "?", "What happens to it is no longer noted. What was noted stays in the audit log. "]
                : ["Stop restricting " + k.name + "?", "Copies of it are no longer looked for, and flows may carry it. " + (k.n ? "The copies already caught stay listed until you deal with them. " : "")]
        confirm.ask({ title: say[0], text: say[1] + "The audit log records that you did it.", ok: page.stopWord(k), danger: true },
                    function () { falcon.call("marks.unmark", { mark_id: k.mid }, function (ok, r) {
                        if (!ok) { Msg.failed(r && r.message ? r.message : "Not changed"); return }
                        Msg.ok(k.name + (k.prot === "private" ? " is no longer private" : k.prot === "watch" ? " is no longer watched" : " is no longer restricted") + " · recorded"); page.load() }) })
    }
    // Private: who may open it, changed in place (marks.readers); the Engine adds whoever changes it
    property var people: []
    property var readersOf: null
    property var readersPick: []
    property bool readersSystem: true
    property bool readersBusy: false
    function changeReaders(k) {
        readersOf = k
        readersPick = (k.readers || []).map(function (r) { return r.account_id }).filter(function (a) { return a !== falcon.accountId })
        readersSystem = k.allowSystem
        if (!people.length) falcon.call("chat.people", {}, function (ok, r) { page.people = ok && r ? r.people || [] : [] })
        readersM.open()
    }
    function saveReaders() {
        var k = readersOf
        if (!k || readersBusy) return
        readersBusy = true
        falcon.call("marks.readers", { mark_id: k.mid, readers: readersPick, allow_system: readersSystem }, function (ok, r) {
            page.readersBusy = false
            if (!ok) { Msg.failed(r && r.message ? r.message.charAt(0).toUpperCase() + r.message.slice(1) : "Not changed"); return }
            readersM.close()
            Msg.ok("Who may open " + k.name + " is changed" + (r.applied_now ? "" : "; " + k.host + " is told when it connects") + " · recorded")
            page.load()
        })
    }
    Modal {
        id: readersM
        objectName: "readersModal"
        page: page
        title: page.readersOf ? "Who may open " + page.readersOf.name : "Who may open it"
        subtitle: page.readersOf ? page.readersOf.host + " " + page.readersOf.path : ""
        Column {
            width: readersM.width - 2 * readersM.pad
            spacing: 12
            bottomPadding: 6
            ReadersPick { people: page.people; picked: page.readersPick; onChanged: function (ids) { page.readersPick = ids } }
            Check { controlled: true; checked: page.readersSystem; text: "Let backup and antivirus open it too (the machine's system account)"; onToggled: function (v) { page.readersSystem = v } }
        }
        footer: Row { spacing: 8
            Btn { text: "Cancel"; onClicked: readersM.close() }
            Btn { objectName: "readersSave"; kind: "primary"; text: "Save who may open it"; loading: page.readersBusy; enabled: !page.readersBusy; onClicked: page.saveReaders() } }
    }
    property bool loading: false
    property string pickedKey: ""
    Timer { id: ldT; interval: Theme.loadMs; onTriggered: page.loading = false }

    situation: {
        if (!marks.length) return "Nothing is protected yet. Protect a file or folder below; it stays where it is."
        var hosts = marks.map(function (k) { return k.host }).filter(function (h, i, a) { return a.indexOf(h) === i }), hit = hostsHit()
        var carries = carrying.filter(function (c) { return !c.held }).map(function (c) { return c.f.flow || ("flow " + c.f.flow_id) }), first = allCopyRows[0]
        var kinds = [[countOf("restricted"), "restricted"], [countOf("private"), "private"], [countOf("watch"), "watched"]].filter(function (x) { return x[0] > 0 })
        var refused = recentRefusals()
        return Theme.many(marks.length, "thing") + (marks.length === 1 ? " is" : " are") + " protected on " + Theme.many(hosts.length, "machine")
               + (kinds.length > 1 ? ": " + kinds.map(function (x) { return x[0] + " " + x[1] }).join(", ").replace(/, ([^,]*)$/, " and $1") : kinds.length ? ", all " + kinds[0][1] : "") + ". "
               + (refused ? Theme.many(refused, "person was", "people were").replace(/^1 person was$/, "Someone was") + " refused a private file this week. " : "")
               + (!rmarks.length ? "" : first ? Theme.many(allCopyRows.length, "copy", "copies") + " turned up elsewhere, on " + Theme.listNames(hit) + "; the worst is " + first.c.file + " on " + first.c.host + "." : "Everything is where it belongs.")
               + (allowedRows.length ? " " + Theme.many(allowedRows.length, "copy", "copies").replace(/^(\d+) copy$/, "$1 copy") + (allowedRows.length === 1 ? " is" : " are") + " allowed elsewhere." : "")
               + (carries.length ? " " + Theme.listNames(carries) + (carries.length === 1 ? " carries" : " carry") + " something restricted." : "")
    }
    situationAt: Time.now

    // a copy's trail (rs-trail): where it was, how it went, where it was found, and who is there
    component Trail: Item {
        id: tr
        property string fromHost: ""
        property string fromName: ""
        property string how: ""
        property string howFull: ""             // the whole of it, on hover
        property string toHost: ""
        property string toPath: ""
        property bool hot: false
        property string who: ""
        property string whoLine: ""
        property bool whyStyle: false
        readonly property real unit: whyStyle ? (width - 150 - 30) / 3.6 : (width - 150 - 120 - 30) / 2.4     // a reason takes a share of its own
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
            // a few words between the boxes, never over them (the user, 12 Nov 2026): what does not fit is on hover
            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6
                Dash { width: Math.max(6, (150 - hw.width - 12) / 2); c: Theme.text4; anchors.verticalCenter: parent.verticalCenter }
                Txt { id: hw; width: Math.min(implicitWidth, 150 - 24); text: tr.how; font.pixelSize: 12; color: Theme.text3; elide: Text.ElideRight
                      Tip { over: hw; text: tr.howFull !== "" && tr.howFull !== tr.how ? tr.howFull : hw.truncated ? tr.how : "" } }
                Dash { width: Math.max(6, (150 - hw.width - 12) / 2); c: Theme.text4; anchors.verticalCenter: parent.verticalCenter }
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
                Txt { id: tp; width: parent.width; text: Theme.fitPath(tr.toPath, tpm, width); mono: true; font.pixelSize: 13; color: tr.hot ? Theme.crit : Theme.text
                      FontMetrics { id: tpm; font: tp.font }
                      Tip { over: tp; text: tp.truncated || tp.text !== tr.toPath ? tr.toPath : "" } } }
        }
        Column {
            id: d
            x: tr.unit * 2.4 + 10 + 150 + 10 + 10
            width: tr.whyStyle ? tr.unit * 1.2 : 120
            anchors.verticalCenter: parent.verticalCenter
            Txt { width: parent.width; text: tr.who; font.pixelSize: 12; color: tr.whyStyle ? Theme.text2 : Theme.text; font.italic: tr.whyStyle }
            Txt { width: parent.width; text: tr.whoLine; font.pixelSize: 12; color: Theme.text3 }
        }
    }

    // --- the three kinds of protection, each as it stands; a tile is the list's filter (click it again for all) --------------
    Row {
        objectName: "protKinds"
        visible: page.marks.length > 0
        width: parent.width
        spacing: 14
        Repeater {
            model: [
                ["restricted", "Restricted", "stop", "kept to its place; a copy anywhere else is caught",
                 page.allCopyRows.length ? Theme.many(page.allCopyRows.length, "copy", "copies") + " caught elsewhere" : "every copy is where it belongs", page.allCopyRows.length > 0],
                ["private", "Private", "lock", "only the people named may open it",
                 page.recentRefusals() ? Theme.many(page.recentRefusals(), "refusal") + " this week" : "nobody refused this week", page.recentRefusals() > 0],
                ["watch", "Watch", "eye", "anyone may use it; every change is noted",
                 page.watchLately.length ? Theme.many(page.watchLately.length, "change") + " in the last two weeks" : "nothing has changed lately", false]]
            delegate: Rectangle {
                id: kt
                required property var modelData
                readonly property bool on: page.show === modelData[0]
                readonly property int n: page.countOf(modelData[0])
                objectName: "kind_" + modelData[0]
                width: (parent.width - 28) / 3
                height: kc2.height + 28
                radius: Theme.radiusLg
                color: on ? Theme.mix(Theme.accent, Theme.surface, 0.07) : Theme.surface
                border.width: 1
                border.color: on ? Theme.accent : ka.containsMouse ? Theme.borderStrong : Theme.border
                opacity: n === 0 && !on ? 0.6 : 1
                Rectangle { x: 16; y: 16; width: 36; height: 36; radius: 18; color: Theme.surface3
                            Icon { anchors.centerIn: parent; name: kt.modelData[2]; size: 16; color: kt.modelData[5] ? Theme.crit : Theme.text2 } }
                Column {
                    id: kc2
                    x: 64; y: 14
                    width: parent.width - 64 - 16
                    spacing: 2
                    Row { spacing: 8
                        Txt { text: kt.modelData[1]; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideNone }
                        Txt { text: kt.n; font.pixelSize: 14; color: Theme.text3; elide: Text.ElideNone } }
                    Txt { width: parent.width; text: kt.modelData[3]; font.pixelSize: 12; color: Theme.text3 }
                    Txt { width: parent.width; text: kt.n ? kt.modelData[4] : "none yet"; font.pixelSize: 12; font.weight: kt.modelData[5] ? Font.DemiBold : Font.Normal
                          color: kt.modelData[5] ? Theme.crit : Theme.text2 }
                }
                MouseArea { id: ka; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: { if (kt.on) return; page.show = kt.modelData[0]; page.sel = ""; page.copy = ""; page.pg = 0 } }
            }
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
            title: page.show === "private" ? "What is private" : page.show === "watch" ? "What is watched" : "What is restricted"
            sub: "by the machine it lives on; click one to see it on the right, expand it for its rule"
            Repeater {
                model: page.hostOrder
                delegate: Group {
                    id: hg
                    required property var modelData
                    required property int index
                    readonly property var xs: page.markPage.filter(function (k) { return k.host === modelData })
                    visible: xs.length > 0
                    width: markP.innerW
                    spaced: index > 0
                    cardGap: 5
                    title: modelData + " · " + page.shownMarks.filter(function (k) { return k.host === hg.modelData }).length
                    sub: page.ownerOf(modelData)
                    Repeater {
                        model: hg.xs
                        delegate: Card {
                            id: kc
                            required property var modelData
                            objectName: "mark_" + modelData.id
                            width: hg.cardW
                            midW: 290
                            actW: 150
                            padV: 7
                            icon: modelData.kind === "folder" ? "folder" : "file"
                            title: modelData.name
                            tag: modelData.kind === "folder" ? Theme.many(modelData.files || 0, "file") : "file"
                            line: modelData.path
                            lineMono: true
                            picked: page.cur !== null && page.cur.id === modelData.id
                            expandable: true
                            expanded: page.exp === modelData.id
                            onOpen: { page.sel = modelData.id; page.copy = "" }
                            onToggle: { page.sel = modelData.id; page.exp = expanded ? "" : modelData.id }
                            mid: Row {
                                anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right
                                spacing: 14
                                Txt { anchors.verticalCenter: parent.verticalCenter; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone
                                      text: kc.modelData.prot === "private" ? Theme.many(page.readerNames(kc.modelData).length, "person", "people") + " may open it"
                                            : kc.modelData.prot === "watch" ? "every change noted"
                                            : kc.modelData.keep === "machine" ? "anywhere on " + kc.modelData.host : "only where it is" }
                                Txt { anchors.verticalCenter: parent.verticalCenter; text: kc.modelData.at ? "since " + Time.day(kc.modelData.at) : ""; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                            }
                            // opened: its rule, what happened to it lately (and, when private, who was refused), and Stop
                            Column {
                                width: parent.width
                                spacing: 10
                                Column {
                                    id: facts
                                    y: 2
                                    width: Math.min(parent.width, 460)
                                    readonly property var k: kc.modelData
                                    readonly property var rowsOf: {
                                        var covers = ["Covers", k.kind === "folder" ? Theme.many(k.files || 0, "file") + ", and any added later" : "1 file"]
                                        var tail = [["Since", Time.day(k.at)], ["Marked by", !k.by || k.by.you ? "you" : k.by.name || "an Admin"]]
                                        if (k.prot === "private")
                                            return [["Where", k.host + " " + k.path], ["Rule", "Only the people named may open it; Windows refuses anyone else"], ["May open it", page.readerNames(k).join(", ") || "only whoever made it private"],
                                                    ["Backup, antivirus", k.allowSystem ? "may open it" : "refused like anyone else"], ["On the machine", page.appliedWord(k)], covers].concat(tail)
                                        if (k.prot === "watch")
                                            return [["Where", k.host + " " + k.path], ["Rule", "Anyone may open, copy or move it; every change, copy and move is noted"], covers].concat(tail)
                                        return [["Where", k.host + " " + k.path], ["Rule", "It " + page.ruleOf(k)], covers, ["Recognised by", "content, " + Theme.many(k.versions || 0, "version") + " remembered"]].concat(tail)
                                    }
                                    Repeater {
                                        model: facts.rowsOf
                                        delegate: Item {
                                            required property var modelData
                                            required property int index
                                            width: parent.width
                                            height: fv.height + 10
                                            Txt { y: 5; width: 120; text: modelData[0]; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                                            Txt { id: fv; x: 132; y: 5; width: parent.width - 132 + 24; text: modelData[1]; font.pixelSize: 13; mono: index === 0; wrapMode: Text.Wrap; elide: Text.ElideNone
                                                  color: modelData[0] === "On the machine" && facts.k.applied && facts.k.applied.ok === false && !facts.k.applied.waiting ? Theme.crit : Theme.text }
                                            Rectangle { visible: index < facts.rowsOf.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                                        }
                                    }
                                }
                                Rectangle { width: parent.width; height: 1; color: Theme.border }
                                Row { anchors.right: parent.right; spacing: 8
                                    Btn { visible: kc.modelData.prot === "private"; objectName: "readers_" + kc.modelData.id; small: true; iconName: "team"; text: "Change who may open it"; onClicked: page.changeReaders(kc.modelData) }
                                    Btn { small: true; danger: true; iconName: "stop"; text: page.stopWord(kc.modelData); onClicked: page.unmark(kc.modelData) } }
                            }
                        }
                    }
                }
            }
            StepPager { visible: page.pages > 1; width: parent.width; from: page.pi * page.perM + 1; to: Math.min(page.ordered.length, page.pi * page.perM + page.perM); total: page.ordered.length; pageNo: page.pi; pages: page.pages; onStep: function (d) { page.pg = page.pi + d } }
            Quiet { visible: page.marks.length === 0; text: "Nothing protected yet. Protect something below." }
            Quiet { visible: page.marks.length > 0 && page.shownMarks.length === 0; text: "Nothing is " + (page.show === "watch" ? "watched" : page.show) + " yet. Protect something below, and pick " + (page.show === "watch" ? "Watch" : page.show === "private" ? "Private" : "Restricted") + "." }
        }
        // --- where it is, across every machine -----------------------------------------------------------------
        Box {
            id: mapP
            objectName: "markMap"
            width: (parent.width - 14) * 4 / 12
            height: Math.max(implicitHeight, markP.implicitHeight)
            title: !page.cur || page.cur.prot === "restricted" || !page.cur.prot ? "Where it is, across every machine" : page.cur.prot === "private" ? "Who may open it" : "What happened to it"
            readonly property var copies: page.cur && page.cur.mid !== undefined && page.det[page.cur.mid] ? page.det[page.cur.mid].copies || [] : []
            readonly property var allowedHere: page.cur && page.cur.mid !== undefined && page.det[page.cur.mid] ? page.det[page.cur.mid].allowed || [] : []
            sub: page.cur ? "<b><font color='" + Theme.text + "'>" + page.cur.name + "</font></b> · " + (page.cur.prot === "private" ? "on " + page.cur.host + "; Windows refuses anyone else"
                                : page.cur.prot === "watch" ? "on " + page.cur.host + "; nothing is refused, everything is noted"
                                : copies.length ? Theme.many(copies.length, "copy", "copies") + " away from home" : "only at home") : "pick something on the left"
            // Private: the people named, then what the machine did and who was refused
            Column {
                objectName: "privatePanel"
                visible: page.cur !== null && page.cur.prot === "private"
                width: parent.width
                spacing: 0
                opacity: page.loading ? 0 : 1
                PagedList {   // a long list pages in place (the user, 11 Nov 2026)
                    id: rdp; reserve: false; items: page.cur && page.cur.prot === "private" ? page.cur.readers : []; per: 6
                    delegate: Item {
                        required property var modelData
                        required property int index
                        readonly property string nm: modelData.account_id === falcon.accountId ? "You" : modelData.name || "Account " + modelData.account_id
                        width: parent.width; height: 44
                        Rectangle { y: 6; width: 32; height: 32; radius: 16; color: Theme.surface3
                                    Txt { anchors.centerIn: parent; text: Theme.initials(parent.parent.nm); font.pixelSize: 12; font.weight: Font.DemiBold; elide: Text.ElideNone } }
                        Txt { x: 44; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 44 - 110; text: parent.nm; font.pixelSize: 13; font.weight: Font.Medium }
                        Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 12; color: Theme.text3; elide: Text.ElideNone
                              text: page.cur && page.cur.by && page.cur.by.account_id === modelData.account_id ? "made it private" : "may open it" }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
                Item { width: 1; height: 10 }
                FactRows { width: parent.width
                           rows: page.cur && page.cur.prot === "private" ? [["Backup, antivirus", page.cur.allowSystem ? "may open it" : "refused like anyone else"], ["On " + page.cur.host, page.appliedWord(page.cur).replace(/^(set|being set|not set) on \S+/, "$1")]] : [] }
                Btn { anchors.right: parent.right; small: true; iconName: "team"; text: "Change who may open it"; onClicked: page.changeReaders(page.cur) }
                Txt { topPadding: 16; bottomPadding: 4; text: "Refused"; color: Theme.text3; font.pixelSize: 12 }
                PagedList {   // a long list pages in place (the user, 11 Nov 2026)
                    id: rfp; reserve: false; items: page.cur && page.cur.prot === "private" ? page.cur.refusals : []; per: 5
                    delegate: Item {
                        required property var modelData
                        width: parent.width; height: rw.height + 12
                        Txt { y: 6; width: 76; text: page.agoWord(modelData.at); color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                        Txt { id: rw; x: 84; y: 6; width: parent.width - 84; textFormat: Text.RichText; font.pixelSize: 13; wrapMode: Text.WordWrap
                              text: "<span style='font-weight:600'>" + (modelData.who || "Someone") + "</span> was refused" + (modelData.process ? " in " + modelData.process : "") }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
                Txt { visible: !page.cur || !(page.cur.refusals || []).length; text: "Nobody has been refused it."; color: Theme.text3; font.pixelSize: 13 }
            }
            // Watch: what happened to it, newest first
            Column {
                objectName: "watchPanel"
                visible: page.cur !== null && page.cur.prot === "watch"
                width: parent.width
                spacing: 0
                opacity: page.loading ? 0 : 1
                Txt { bottomPadding: 6; text: page.cur && page.cur.prot === "watch" ? (page.latelyOf(page.cur).length ? Theme.many(page.latelyOf(page.cur).length, "thing") + " in the last two weeks" : "") : ""
                      visible: text !== ""; color: Theme.text3; font.pixelSize: 12 }
                PagedList {   // a long list pages in place (the user, 11 Nov 2026)
                    id: wp; items: page.cur && page.cur.prot === "watch" ? page.latelyOf(page.cur) : []; per: 8
                    delegate: Item {
                        required property var modelData
                        width: parent.width; height: wl.height + 14
                        Rectangle { x: 3; y: 11; width: 7; height: 7; radius: 4; color: Theme.accent }
                        readonly property var h: page.happened(modelData, page.cur)
                        Column { id: wl; x: 20; y: 7; width: parent.width - 20; spacing: 1
                            Txt { width: parent.width; font.pixelSize: 13; font.weight: Font.DemiBold; wrapMode: Text.WordWrap; text: parent.parent.h.head }
                            Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap
                                  text: [parent.parent.h.when, parent.parent.h.who, parent.parent.h.place].filter(function (x) { return x }).join(" · ") } }
                    }
                }
                Txt { visible: !page.cur || !page.latelyOf(page.cur).length; text: "Nothing has happened to it in the last two weeks."; color: Theme.text3; font.pixelSize: 13; wrapMode: Text.WordWrap; width: parent.width }
            }
            // Restricted: where it is, across every machine
            Column {
                visible: !page.cur || page.cur.prot === "restricted" || !page.cur.prot
                width: parent.width
                spacing: 0
                opacity: page.loading ? 0 : 1
                Flickable {
                    width: parent.width
                    height: Math.min(contentHeight, 420)
                    contentHeight: depts.height
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    Column {
                        id: depts
                        objectName: "mapDepts"
                        width: parent.width
                        spacing: 0
                        bottomPadding: 10
                        Repeater {
                            model: page.mapDepts
                            delegate: Column {
                                id: dg
                                required property var modelData
                                required property int index
                                width: depts.width
                                spacing: 6
                                topPadding: dg.index ? 10 : 2
                                Txt { text: dg.modelData.name; color: Theme.text3; font.pixelSize: 12 }
                                Flow {
                                    width: parent.width
                                    spacing: 10
                                    Repeater {
                                        model: dg.modelData.hs
                                        delegate: Tile {
                                            required property var modelData
                                            readonly property bool home: page.cur !== null && page.cur.host === modelData
                                            readonly property var cp: mapP.copies.filter(function (c) { return c.host === modelData })[0] || null
                                            readonly property bool allowedOn: mapP.allowedHere.some(function (c) { return c.host === modelData })
                                            m: Fleet.byHost[modelData] || { host: modelData, online: true }
                                            mark: home ? "home" : cp ? "hot" : allowedOn ? "ok" : ""
                                            picked: !!cp && page.copy === String(cp.issue_id)
                                            still: !cp
                                            marksOnly: true
                                            tip: modelData + (page.ownerOf(modelData) ? ", " + page.ownerOf(modelData) : "") + (home ? " · its home" : cp ? " · a copy, " + Time.dur((Time.now - Time.ms(cp.opened_at)) / 3600000) + " ago" : allowedOn ? " · a copy allowed" : "")
                                            onClicked: page.copy = String(cp.issue_id)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Row {
                    spacing: 16
                    topPadding: 9
                    Repeater {
                        model: [["its home", Theme.mix(Theme.accent, Theme.surface3, 0.28)], ["a copy caught", Theme.mix(Theme.crit, Theme.surface3, 0.28)], ["a copy allowed", Theme.mix(Theme.ok, Theme.surface3, 0.26)]]
                        delegate: Row { required property var modelData; spacing: 6
                            Rectangle { width: 11; height: 11; radius: 3; color: modelData[1]; anchors.verticalCenter: parent.verticalCenter }
                            Txt { text: modelData[0]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
                    }
                }
            }
            // what happened to it lately, here and not in its opened card (the user, 12 Nov 2026: an opened card holds fixed details; a list that can grow is on the right, paged)
            Column {
                objectName: "restrictedLately"
                visible: page.cur !== null && (page.cur.prot === "restricted" || !page.cur.prot)
                width: parent.width
                topPadding: 14
                opacity: page.loading ? 0 : 1
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Txt { topPadding: 10; bottomPadding: 4; text: "What happened to it, the last two weeks"; color: Theme.text3; font.pixelSize: 12 }
                PagedList {
                    items: page.cur ? page.latelyOf(page.cur) : []
                    per: 4
                    delegate: Item {
                        required property var modelData
                        readonly property var h: page.happened(modelData, page.cur)
                        width: parent.width; height: rl.height + 12
                        Column { id: rl; y: 6; width: parent.width; spacing: 1
                            Txt { width: parent.width; font.pixelSize: 13; font.weight: Font.DemiBold; wrapMode: Text.WordWrap; text: parent.parent.h.head }
                            Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap
                                  text: [parent.parent.h.when, parent.parent.h.who, parent.parent.h.place].filter(function (x) { return x }).join(" · ") } }
                    }
                }
                Txt { visible: !page.cur || page.latelyOf(page.cur).length === 0; text: "Nothing has happened to it in the last two weeks."; color: Theme.text3; font.pixelSize: 13 }
            }
            Loading { parent: mapP; on: page.loading && page.cur !== null; under: mapP.headerHeight }
            Pulse { parent: mapP; key: page.pickedKey || null }
        }
    }

    // --- copies on other machines --------------------------------------------------------------------------
    Box {
        objectName: "copiesElsewhere"
        visible: page.rmarks.length > 0 && page.showing("restricted")
        width: parent.width
        title: "Copies on other machines"
        sub: page.allCopyRows.length ? "worst first; where it was, how it went, where it was found; click one to see it on the machines" : "no copy of anything restricted is anywhere else"
        Column {
            width: parent.width
            spacing: 12.5
            Repeater {
                model: page.allCopyRows.slice(page.piC * page.perC, page.piC * page.perC + page.perC)
                delegate: Rectangle {
                    id: cr
                    required property var modelData
                    readonly property string done: page.acted[modelData.id] || ""
                    width: parent.width
                    height: (page.allowingId === modelData.id ? Math.max(trl.height, 24) : Math.max(trl.height, acts.height)) + 16
                    radius: Theme.radiusLg
                    color: page.copy === modelData.id ? Theme.surface3 : "transparent"
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.pickCopy(cr.modelData) }
                    Trail {
                        id: trl
                        x: 10; y: 8
                        width: parent.width - 20 - acts.width - 14
                        opacity: cr.done !== "" ? 0.55 : 1
                        fromHost: cr.modelData.k.host; fromName: cr.modelData.k.name
                        how: page.howOf(cr.modelData.c)
                        howFull: page.howSaid(cr.modelData.c)
                        toHost: cr.modelData.c.host; toPath: (cr.modelData.c.folder || cr.modelData.c.path || "") + (cr.modelData.c.file ? "\\" + cr.modelData.c.file : "")
                        hot: cr.done === ""
                        who: cr.modelData.c.signed_in || "nobody signed in"; whoLine: page.agoWord(cr.modelData.c.opened_at)
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
                            model: cr.done !== "" || page.allowingId === cr.modelData.id ? [] : [["delete", "Delete the copy", true], ["allow", "Allow it there", false]]
                            delegate: Btn {
                                required property var modelData
                                small: true; danger: modelData[2]; text: modelData[1]
                                onClicked: modelData[0] === "allow" ? (page.allowingId = cr.modelData.id, page.why = "")
                                         : modelData[0] === "delete" ? confirm.ask({ title: "Delete the copy on " + cr.modelData.c.host + "?", text: "Only " + cr.modelData.c.file + " in " + cr.modelData.c.folder + " on " + cr.modelData.c.host + " is deleted. What is restricted is not touched.", ok: "Delete the copy", cancel: "Keep it", danger: true },
                                                                                   function () { page.act(cr.modelData, "delete", "") })
                                         : null
                            }
                        }
                    }
                }
            }
            StepPager { visible: page.pagesC > 1; width: parent.width; from: page.piC * page.perC + 1; to: Math.min(page.allCopyRows.length, page.piC * page.perC + page.perC); total: page.allCopyRows.length; pageNo: page.piC; pages: page.pagesC; onStep: function (d) { page.pgC = page.piC + d } }
            Quiet { visible: page.allCopyRows.length === 0; icon: "check"; text: "Nothing restricted has been found anywhere else." }
        }
    }

    // --- allowed copies --------------------------------------------------------------------------------------
    Box {
        objectName: "allowedCopies"
        visible: page.rmarks.length > 0 && page.showing("restricted")
        width: parent.width
        title: "Allowed copies"
        sub: "copies found away from home that were let stay, newest first, each with the reason given; they are not caught again unless an Admin takes it back"
        Column {
            width: parent.width
            spacing: 4
            Repeater {
                model: page.allowedRows.slice(page.piA * page.perC, page.piA * page.perC + page.perC)
                delegate: Item {
                    required property var modelData
                    width: parent.width
                    height: Math.max(at.height, 24) + 16
                    Trail {
                        id: at
                        x: 10; y: 8
                        width: parent.width - 20 - tb.width - 14
                        fromHost: modelData.k.host; fromName: modelData.k.name
                        how: "allowed " + page.allowedSince(modelData.c.at)
                        toHost: modelData.c.host; toPath: modelData.c.path || ""
                        who: modelData.c.reason ? "“" + modelData.c.reason + "”" : ""; whoLine: page.ownerOf(modelData.c.host)
                        whyStyle: true
                    }
                    Btn { id: tb; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; small: true; text: "Take it back"; onClicked: page.takeBack(parent.modelData) }
                }
            }
            StepPager { visible: page.pagesA > 1; width: parent.width; from: page.piA * page.perC + 1; to: Math.min(page.allowedRows.length, page.piA * page.perC + page.perC); total: page.allowedRows.length; pageNo: page.piA; pages: page.pagesA; onStep: function (d) { page.pgA = page.piA + d } }
            Quiet { visible: page.allowedRows.length === 0; text: "You have not allowed a copy anywhere else." }
        }
    }

    // --- flows carrying what you restricted (rs-fl) ------------------------------------------------------------
    Box {
        objectName: "flowsCarrying"
        visible: page.rmarks.length > 0 && page.showing("restricted")
        width: parent.width
        title: "Flows carrying what is restricted"
        sub: "right now; a flow held at something restricted waits for an Admin to allow it, for that flow only"
        Column {
            width: parent.width
            spacing: 10
            PagedList {   // a long list pages in place (the user, 11 Nov 2026)
                id: fp; items: page.carrying; per: 6
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
                        Txt { width: parent.width; textFormat: Text.RichText; font.pixelSize: 13
                              text: "<span style='font-weight:600'>" + (modelData.f.flow || modelData.f.name || "flow " + modelData.f.flow_id) + "</span> " + (modelData.held ? "is held at" : "carries") + " <span style='font-weight:600'>" + (modelData.f.what || (modelData.k ? modelData.k.name : "")) + "</span>" }
                        Txt { width: parent.width; mono: true; color: Theme.text3; font.pixelSize: 12; text: (modelData.f.from || "") + " → " + (modelData.f.to || "") }
                    }
                    Column {
                        x: parent.width - 150 - 12 - ob.width - 4; width: 150
                        anchors.verticalCenter: parent.verticalCenter
                        Txt { width: parent.width; horizontalAlignment: Text.AlignRight; font.pixelSize: 12; font.weight: Font.DemiBold; color: modelData.held ? Theme.crit : Theme.text
                              text: modelData.held ? "waiting for an Admin" : modelData.f.today ? Theme.fmt(modelData.f.today) + " today" : "allowed just now" }
                        Txt { width: parent.width; horizontalAlignment: Text.AlignRight; font.pixelSize: 12; color: Theme.text3
                              text: modelData.held ? "since " + Time.hhmm(modelData.f.asked_at) : (modelData.f.last_at ? "last " + Time.hhmm(modelData.f.last_at) + " · " : "") + "allowed " + page.allowedSince(modelData.f.since) }
                    }
                    Btn { id: ob; anchors.right: parent.right; anchors.rightMargin: 4; anchors.verticalCenter: parent.verticalCenter; small: true
                          kind: modelData.held ? "primary" : "default"; text: modelData.held ? "Allow" : "Open in Flows"
                          onClicked: modelData.held ? page.letFlow(modelData) : Nav.goAsk("flows", null, "Flows opens with this flow picked.", String(modelData.f.flow_id)) }
                    Rectangle { visible: index < fp.shown.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                }
            }
            Quiet { visible: page.carrying.length === 0; text: "No flow carries anything restricted." }
        }
    }

    // --- Private: everyone refused, across every private file -----------------------------------------------------------
    Box {
        objectName: "refusedLately"
        visible: page.countOf("private") > 0 && page.showing("private")
        width: parent.width
        title: "Refused lately"
        sub: page.allRefusals.length ? "who tried to open something private, newest first; Windows said no" : "nobody has been refused a private file"
        Column {
            width: parent.width
            PagedList {   // a long list pages in place (the user, 11 Nov 2026)
                id: rlp; items: page.allRefusals; per: 8
                delegate: Item {
                    required property var modelData
                    required property int index
                    width: parent.width; height: 40
                    Rectangle { x: 4; anchors.verticalCenter: parent.verticalCenter; width: 28; height: 28; radius: 14; color: Theme.surface3
                                Icon { anchors.centerIn: parent; name: "lock"; size: 13; color: Theme.text2 } }
                    Txt { x: 44; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 44 - 150; textFormat: Text.RichText; font.pixelSize: 13
                          text: "<span style='font-weight:600'>" + (modelData.r.who || "Someone") + "</span> was refused <span style='font-weight:600'>" + modelData.k.name + "</span>"
                                + (modelData.r.process ? " in " + modelData.r.process : "") + " <font color='" + Theme.text3 + "'>on " + (modelData.r.machine || modelData.k.host) + "</font>" }
                    Txt { anchors.right: parent.right; anchors.rightMargin: 4; anchors.verticalCenter: parent.verticalCenter; text: page.agoWord(modelData.r.at); color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                    Rectangle { visible: index < rlp.shown.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.sel = modelData.k.id }
                }
            }
            Quiet { visible: page.allRefusals.length === 0; icon: "check"; text: "Nobody has been refused a private file." }
        }
    }

    // --- Watch: what happened, across every watched file ---------------------------------------------------------------
    Box {
        objectName: "watchedLately"
        visible: page.countOf("watch") > 0 && page.showing("watch")
        width: parent.width
        title: "Lately on watched files"
        sub: page.watchLately.length ? "every change, copy and move, newest first, with who was signed in" : "nothing has happened to a watched file in the last two weeks"
        Column {
            width: parent.width
            PagedList {   // a long list pages in place (the user, 11 Nov 2026)
                id: wlp; items: page.watchLately; per: 8
                delegate: Item {
                    required property var modelData
                    required property int index
                    width: parent.width; height: 40
                    Rectangle { x: 4; anchors.verticalCenter: parent.verticalCenter; width: 28; height: 28; radius: 14; color: Theme.surface3
                                Icon { anchors.centerIn: parent; name: "eye"; size: 13; color: Theme.text2 } }
                    Txt { x: 44; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 44 - 150; textFormat: Text.RichText; font.pixelSize: 13
                          readonly property var h: page.happened(modelData.e, modelData.k)
                          text: "<span style='font-weight:600'>" + h.head + "</span> <font color='" + Theme.text3 + "'>" + [h.who, h.place].filter(function (x) { return x }).join(" · ") + "</font>" }
                    Txt { anchors.right: parent.right; anchors.rightMargin: 4; anchors.verticalCenter: parent.verticalCenter; text: page.agoWord(modelData.e.at); color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                    Rectangle { visible: index < wlp.shown.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.sel = modelData.k.id }
                }
            }
            Quiet { visible: page.watchLately.length === 0; icon: "check"; text: "Nothing has happened to a watched file lately." }
        }
    }

    // --- protect something: a few careful steps, so it has its own page ---------------------------------------
    Box {
        objectName: "restrictSomething"
        width: parent.width
        accentFoot: true
        title: "Protect something"
        sub: "it stays where it is and you keep using it"
        GiveSteps {
            steps: [["Pick what to protect", "a file or a folder on this PC, found by a search or picked in Explorer"], ["Say how", "restricted to its place, private to the people you name, or watched"], ["Check and protect", "a restricted one's copies elsewhere are found and listed straight away"]]
            act: "Protect something"
            onGo: Nav.go("restricted", "mark")
        }
    }
}
