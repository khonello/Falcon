import QtQuick
import QtQuick.Controls.Basic
import "."

// A DESCRIPTION BOX THAT MARKS WHAT IT RECOGNISES AS YOU TYPE: people, files, dates and programs, each
// in its colour. Clicking a marked phrase (or pausing on a new one) asks what it is; `@` picks a
// person. What is confirmed here is what the reader is told; the model is asked only about the rest.
//
// Drawn as the concept draws it: a mirror of the text with the marks behind a transparent text box.
Column {
    objectName: "smartText"
    id: root
    property string text: ""
    property var people: []                  // [{name, sub, host, account}]
    property var programs: [["Excel", "EXCEL.EXE"], ["Word", "WINWORD.EXE"], ["Outlook", "OUTLOOK.EXE"], ["Edge", "msedge.exe"], ["Acrobat", "AcroRd32.exe"], ["Notepad", "notepad.exe"]]
    property var conf: ({})                   // key -> {kind, text, label, sub, ...}
    property var ignored: ({})
    property string hostHint: ""
    signal edited(string text)
    spacing: 8

    readonly property var kindColor: ({ person: Theme.ser1, file: Theme.ser2, date: Theme.ser5, program: Theme.ser3 })
    readonly property var kindWord: ({ person: "person", file: "file", date: "date", program: "program" })
    readonly property var matches: find(text)

    function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>") }
    // files first, so a date inside a file name (backup-2026-09-28.bak) is never offered as a deadline;
    // only unambiguous dates: a day with a time, "tomorrow", a calendar date, or "by <day>"
    function find(t) {
        var out = []
        function add(kind, re, grp) {
            re.lastIndex = 0
            var m
            while ((m = re.exec(t)) !== null) {
                var str = grp ? m[grp] : m[0]
                if (!str) { if (re.lastIndex === m.index) re.lastIndex++; continue }
                var s0 = m.index + (grp ? m[0].lastIndexOf(str) : 0), e0 = s0 + str.length
                if (t[s0 - 1] === "@") continue
                var clash = out.some(function (o) { return s0 < o.end && e0 > o.start })
                if (!clash) out.push({ kind: kind, start: s0, end: e0, text: str, key: kind + ":" + str.toLowerCase() })
            }
        }
        add("file", /[\w\-.]+\.(?:xlsx|xls|docx|doc|csv|pdf|txt|zip|pptx)\b/gi)
        add("date", /\b((?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day\s+(?:at\s+)?\d{1,2}(?::\d{2})?(?:\s?[ap]m)?|tomorrow(?:\s+at\s+\d{1,2}(?::\d{2})?)?|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(?:\s+at\s+\d{1,2}:\d{2})?)/gi, 1)
        add("date", /\b(?:by|before|due)\s+((?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day)\b/gi, 1)
        people.forEach(function (p) { add("person", new RegExp("(^|[^\\w])(" + p.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")(?![\\w])", "g"), 2) })
        programs.forEach(function (p) { add("program", new RegExp("\\b(" + p[0] + ")\\b", "g"), 1) })
        return out.sort(function (a, b) { return a.start - b.start })
    }
    // a date phrase as a time: weekday, tomorrow or "12 Oct", with a clock time or 17:00
    function parseDate(s) {
        var t = s.toLowerCase(), d = new Date(Time.now), wd = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
        d.setHours(0, 0, 0, 0)
        var k = wd.findIndex(function (w) { return t.indexOf(w) >= 0 })
        if (k >= 0) { var add = (k - d.getDay() + 7) % 7 || 7; d.setDate(d.getDate() + add) }
        else if (t.indexOf("tomorrow") >= 0) d.setDate(d.getDate() + 1)
        else {
            var m = /(\d{1,2})\s+([a-z]{3})/.exec(t)
            if (!m) return null
            var mi = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].indexOf(m[2])
            if (mi < 0) return null
            d.setMonth(mi); d.setDate(+m[1])
        }
        var tm = /(?:at\s+|\s)(\d{1,2})(?::(\d{2}))?\s?([ap]m)?\s*$/.exec(t), h = 17, mn = 0
        if (tm) { h = +tm[1] + (tm[3] === "pm" && +tm[1] < 12 ? 12 : 0); mn = tm[2] ? +tm[2] : 0 }
        d.setHours(h, mn, 0, 0)
        return d
    }

    // the mirror: the same text, transparent, with the marks behind
    readonly property string mirror: {
        var out = "", at = 0, t = text
        for (var i = 0; i < matches.length; i++) {
            var m = matches[i], c = kindColor[m.kind], ok = conf[m.key], ig = ignored[m.key]
            out += esc(t.slice(at, m.start))
            var bg = ig ? "transparent" : Theme.alpha(c, ok ? 0.22 : 0.10)
            out += "<span style='background-color:" + bg + "'>" + esc(t.slice(m.start, m.end)) + "</span>"
            at = m.end
        }
        return out + esc(t.slice(at)) + "&#8203;"
    }

    property int openAt: -1                  // the match whose picker is open
    property var mention: null              // {start, end, q, kind} while an @ is being typed ("" kind = still choosing what it is)
    property var stage: null                // {title, sub, at, opts} -- the second question after a file or program (what is to happen to it)
    property int hi: 0                      // the highlighted option: Up/Down move it, Enter or Tab takes it, Esc closes
    readonly property bool pickerOpen: picker.visible
    readonly property var kinds: [
        { id: "person", label: "Person", sub: "who it is for" },
        { id: "file", label: "File", sub: "a file the work is about" },
        { id: "folder", label: "Folder", sub: "where a new file is to be put" },
        { id: "program", label: "Program", sub: "an application to be used or checked" },
        { id: "deadline", label: "Deadline", sub: "a time: final or soft" }]
    // everything the person stated outright, as the Engine reads it (task.propose `hints`): the model and the patterns work on the rest
    readonly property var hints: {
        var out = []
        for (var k in conf) {
            var c = conf[k]
            if (c.kind === "file") out.push({ kind: "file", name: c.text, intent: c.intent || undefined, file_index_id: c.file_index_id || undefined })
            else if (c.kind === "program") out.push({ kind: "program", name: c.text, intent: c.intent || undefined })
            else if (c.kind === "folder") out.push({ kind: "folder", path: c.text })
            else if (c.kind === "date" && c.v) out.push({ kind: "deadline", role: c.role || "final", at: c.v })
        }
        return out
    }

    Item {
        width: root.width
        height: Math.max(96, area.implicitHeight)
        Rectangle { anchors.fill: parent; radius: Theme.radiusSm; color: Theme.surface; border.width: 1; border.color: area.activeFocus ? Theme.accent : Theme.borderStrong }
        Text {
            id: mirror
            anchors.fill: parent
            leftPadding: 11; rightPadding: 11; topPadding: 8; bottomPadding: 8
            textFormat: Text.RichText
            wrapMode: Text.Wrap
            font.family: Theme.sans
            font.pixelSize: 14
            color: "transparent"
            text: root.mirror
        }
        TextArea {
            id: area
            objectName: "smartArea"
            anchors.fill: parent
            leftPadding: 11; rightPadding: 11; topPadding: 8; bottomPadding: 8
            wrapMode: TextEdit.Wrap
            font.family: Theme.sans
            font.pixelSize: 14
            color: Theme.text
            selectByMouse: true
            selectionColor: Theme.alpha(Theme.accent, 0.3)
            placeholderText: "What needs doing? Type @ to mark a person, file, folder, program or deadline."
            placeholderTextColor: Theme.text4
            background: null
            text: root.text
            onTextChanged: {
                if (text !== root.text) root.edited(text)
                root.detect()
                pause.restart()
            }
            onCursorPositionChanged: { root.detect(); if (!root.mention) root.openAt = -1 }
            onReleased: {
                var c = cursorPosition
                root.openAt = root.matches.findIndex(function (m) { return c >= m.start && c <= m.end })
            }
            // with a picker open the keyboard drives it: Up/Down choose, Enter or Tab take the highlighted option, Esc closes
            Keys.onPressed: function (e) {
                if (!root.pickerOpen) return
                var n = picker.opts.length
                if (e.key === Qt.Key_Escape) { root.close(); e.accepted = true }
                else if (root.stage && !root.mention && e.text.length > 0 && e.key !== Qt.Key_Return && e.key !== Qt.Key_Enter && e.key !== Qt.Key_Tab) { root.stage = null }
                else if (n === 0) return
                else if (e.key === Qt.Key_Down) { root.hi = (root.hi + 1) % n; e.accepted = true }
                else if (e.key === Qt.Key_Up) { root.hi = (root.hi + n - 1) % n; e.accepted = true }
                else if (e.key === Qt.Key_Return || e.key === Qt.Key_Enter || e.key === Qt.Key_Tab) {
                    var o = picker.opts[Math.min(root.hi, n - 1)]
                    if (o && !o.off) o.run()
                    e.accepted = true
                }
            }
        }
        // a pause on a new, unconfirmed match offers it once; after that it waits to be clicked
        property var offered: ({})
        Timer {
            id: pause
            interval: 900
            onTriggered: {
                if (!area.activeFocus || root.mention) return
                var c = area.cursorPosition, i = root.matches.findIndex(function (m) { return c >= m.start && c <= m.end })
                if (i < 0) return
                var m = root.matches[i]
                if (root.conf[m.key] || root.ignored[m.key] || parent.offered[m.key]) return
                var o = Object.assign({}, parent.offered); o[m.key] = 1; parent.offered = o
                root.openAt = i
            }
        }

        // the picker under the phrase
        Rectangle {
            id: picker
            readonly property var m: root.openAt >= 0 && root.openAt < root.matches.length ? root.matches[root.openAt] : null
            readonly property var opts: root.stage ? root.stage.opts : root.optionsFor(m, root.mention)
            visible: m !== null || root.mention !== null || root.stage !== null
            readonly property rect at: root.stage ? area.positionToRectangle(root.stage.at) : m ? area.positionToRectangle(m.end) : root.mention ? area.positionToRectangle(root.mention.start) : Qt.rect(0, 0, 0, 0)
            x: Math.max(0, Math.min(at.x - 20, parent.width - width))
            y: at.y + at.height + 6
            objectName: "smartPicker"
            width: 330
            height: pcol.height + 12
            radius: Theme.radius
            color: Theme.surface
            border.width: 1
            border.color: Theme.borderStrong
            z: 20
            Column {
                id: pcol
                x: 6; y: 6
                width: parent.width - 12
                Row {
                    width: parent.width
                    spacing: 6
                    leftPadding: 2
                    bottomPadding: 4
                    Rectangle { visible: picker.m !== null; width: 8; height: 8; radius: 2; color: picker.m ? root.kindColor[picker.m.kind] : "transparent"; anchors.verticalCenter: parent.verticalCenter }
                    Txt { objectName: "smartPickerTitle"; text: root.stage ? root.stage.title : picker.m ? "Is this a " + root.kindWord[picker.m.kind] + "?" : root.mention ? root.mentionTitle() : ""; color: Theme.text3; font.pixelSize: 12; width: parent.width - 120 }
                    Txt { visible: picker.m !== null || root.stage !== null; text: root.stage ? root.stage.sub : picker.m ? picker.m.text : ""; font.weight: Font.Medium; font.pixelSize: 12; width: 100; horizontalAlignment: Text.AlignRight }
                }
                Txt { visible: picker.opts.length === 0 && root.mention !== null; text: root.mention ? root.emptyWord(root.mention) : ""; color: Theme.text3; font.pixelSize: 12; leftPadding: 8; width: pcol.width; wrapMode: Text.Wrap }
                Repeater {
                    model: picker.opts
                    Rectangle {
                        required property var modelData
                        required property int index
                        width: pcol.width
                        height: oc.height + 12
                        radius: Theme.radiusSm
                        color: oa.containsMouse || index === root.hi ? Theme.accentSoft : "transparent"
                        opacity: modelData.off ? 0.55 : 1
                        Column {
                            id: oc
                            x: 8; y: 6
                            width: parent.width - 16
                            Txt { width: parent.width; text: modelData.label; mono: !!modelData.mono; font.pixelSize: 12; wrapMode: Text.WrapAnywhere; elide: Text.ElideNone }
                            Txt { visible: !!modelData.sub; width: parent.width; text: modelData.sub || ""; color: Theme.text3; font.pixelSize: 11 }
                        }
                        MouseArea { id: oa; anchors.fill: parent; hoverEnabled: true; cursorShape: modelData.off ? Qt.ArrowCursor : Qt.PointingHandCursor; onEntered: root.hi = index; onClicked: if (!modelData.off) modelData.run() }
                    }
                }
                Rectangle { visible: picker.m !== null && root.stage === null; width: parent.width; height: 1; color: Theme.border }
                Link {
                    visible: picker.m !== null && root.stage === null
                    leftPadding: 8; topPadding: 6
                    text: picker.m ? "Not a " + root.kindWord[picker.m.kind] : ""
                    font.pixelSize: 12
                    onClicked: { var g = Object.assign({}, root.ignored); g[picker.m.key] = true; root.ignored = g; root.openAt = -1 }
                }
            }
        }
    }

    // is the cursor inside an @ token? (read again whenever the text or the cursor moves)
    function detect() {
        var text = area.text
                var c = area.cursorPosition, before = text.slice(0, c)
                var mk = /(?:^|[^\w])@(person|file|folder|program|deadline):([^\n@]*)$/.exec(before), mm = /(?:^|[^\w])@([\w.]*)$/.exec(before)
                var old = mention
                if (mk) { var t0 = mk[0].lastIndexOf("@"); mention = { start: c - mk[0].length + t0, end: c, q: mk[2], kind: mk[1] } }
                else if (mm) { var t1 = mm[0].lastIndexOf("@"); mention = { start: c - mm[0].length + t1, end: c, q: mm[1], kind: "" } }
                else mention = null
                if (mention) stage = null
                if (!old || !mention || old.q !== mention.q || old.kind !== mention.kind) hi = 0
    }
    function close() { openAt = -1; mention = null; stage = null; hi = 0; area.forceActiveFocus() }
    function choose(m, o) { var c = Object.assign({}, conf); c[m.key] = Object.assign({ kind: m.kind, text: m.text }, o); conf = c; close() }
    // put `insert` where the @ token was, remember what it is, and leave the cursor after it
    function settle(insert, key, entry, next) {
        var men = mention, c = Object.assign({}, conf)
        c[key] = Object.assign({ text: insert }, entry); conf = c
        var v = text.slice(0, men.start) + insert + text.slice(men.end), pos = men.start + insert.length
        mention = null; openAt = -1; hi = 0; stage = null
        edited(v)
        Qt.callLater(function () {
            area.forceActiveFocus(); area.cursorPosition = pos
            if (next) { var r = next(); r.at = pos; root.stage = r; root.hi = 0 }
        })
    }
    function pickPerson(p) {
        settle(p.name, "person:" + p.name.toLowerCase(), { kind: "person", name: p.name, label: p.name, sub: p.sub, account: p.account })
    }
    function mentionTitle() {
        var k = mention.kind
        return k === "" ? "Mark this as…" : k === "person" ? "Who is this for?" : k === "file" ? "Which file?" : k === "folder" ? "Which folder?" : k === "program" ? "Which program?" : "When?"
    }
    function emptyWord(men) {
        if (men.kind === "person" || men.kind === "") return men.q ? "No one matches “" + men.q + "”." : "No one to pick."
        if (men.kind === "deadline") return "Type a time, for example “friday 3pm” or “in 2 hours”."
        return "Type a name."
    }
    // the second question: what is to happen to the file or program that was just marked
    function askIntent(kind, entryKey, label, items) {
        return function () {
            return { title: "What should happen to " + label + "?", sub: kind, opts: items.map(function (it) {
                return { label: it[1], sub: it[2], run: function () {
                    var c = Object.assign({}, root.conf), e = Object.assign({}, c[entryKey])
                    if (it[0]) e.intent = it[0]; else delete e.intent
                    c[entryKey] = e; root.conf = c; root.close()
                } }
            }) }
        }
    }
    readonly property var fileIntentList: [["create", "Create it", "a new file the work should produce"], ["update", "Change it", "an existing file the work should edit"], ["exists", "It must exist", "only check that it is there"], ["", "Let the model decide", "read it from the words around it"]]
    readonly property var programIntentList: [["used", "Use it", "the work is done in it"], ["used_with_file", "Use it on the file", "tied to the file marked above"], ["installed_available", "Have it installed", ""], ["running", "Have it running", ""], ["closed_not_running", "Not running", "closed"], ["", "Let the model decide", "read it from the words around it"]]
    readonly property var asked: ({})
    property var fileHits: ({})               // a file name -> what the index has under it
    function lookFile(name) {
        if (name.length < 2 || asked[name] || fileHits[name] !== undefined) return
        asked[name] = true                  // marked in place: this runs while the options are being worked out, so it must not change a bound value
        falcon.call("index.search", { query: name }, function (ok, r) {
            var x = Object.assign({}, root.fileHits); x[name] = ok ? (r.results || []) : []; root.fileHits = x
        })
    }
    function fileOptions(q, m) {
        lookFile(q)
        var hits = (fileHits[q] || []).filter(function (f) { return String(f.filename || f.path || "").toLowerCase().indexOf(q.toLowerCase()) >= 0 })
        function mark(nm, extra) { var k = "file:" + nm.toLowerCase(); root.settle(nm, k, Object.assign({ kind: "file", label: nm }, extra), root.askIntent("file", k, nm, root.fileIntentList)) }
        var res = hits.slice(0, 5).map(function (f) {
            var nm = f.filename || String(f.path).split(/[\\/]/).pop()
            return { label: f.path || f.filename, sub: (f.hostname || "") + (f.resource_tag ? " · " + f.resource_tag : ""), mono: true,
                     run: function () { if (m) root.choose(m, { label: q, sub: f.path, file_index_id: f.id }); else mark(nm, { sub: f.path, file_index_id: f.id }) } }
        })
        if (q) res.push({ label: m ? "A new file" : "“" + q + "” as a new file", mono: !m, sub: hits.length ? "A different file with this name, not created yet" : "Not in the file index yet. A check can expect it to be created.",
                          run: function () { if (m) root.choose(m, { label: q, sub: "a new file" }); else mark(q, { sub: "a new file" }) } })
        return res
    }
    function deadlineOptions(q, m) {
        if (!q.trim()) return []
        var w = typeof falcon.readWhen === "function" ? falcon.readWhen(q) : { at: "", said: "", why: "The reader is not available here." }
        if (!w.at) return [{ label: "“" + q.trim() + "” is not one time", sub: w.why, off: true, run: function () {} }]
        function mk(role, word) {
            return { label: word + " · " + w.said, sub: role === "final" ? "the task is overdue after this" : "a nudge before the final deadline", run: function () {
                if (m) root.choose(m, { role: role, v: w.at, label: word, sub: w.said })
                else root.settle(q.trim(), "date:" + q.trim().toLowerCase(), { kind: "date", role: role, v: w.at, label: word, sub: w.said }) } }
        }
        return [mk("final", "Final deadline"), mk("soft", "Soft deadline")]
    }
    function programOptions(q) {
        var ql = q.trim().toLowerCase()
        function mark(name, exe) { var k = "program:" + name.toLowerCase(); root.settle(name, k, { kind: "program", label: exe, exe: exe, sub: "program" }, root.askIntent("program", k, name, root.programIntentList)) }
        var known = programs.filter(function (p) { return !ql || p[0].toLowerCase().indexOf(ql) >= 0 })
        var res = known.map(function (p) { return { label: p[0], sub: p[1], run: function () { mark(p[0], p[1]) } } })
        if (ql && !known.some(function (p) { return p[0].toLowerCase() === ql }))
            res.push({ label: "“" + q.trim() + "”", sub: "A program that is not in the list", run: function () { mark(q.trim(), q.trim()) } })
        return res
    }
    function optionsFor(m, men) {
        if (men && !m) {
            var q = men.q, ql = q.toLowerCase()
            var ppl = people.filter(function (p) { return p.name.toLowerCase().indexOf(ql) >= 0 }).slice(0, 6)
                            .map(function (p) { return { label: p.name, sub: p.sub, run: function () { root.pickPerson(p) } } })
            if (men.kind === "person") return ppl
            if (men.kind === "") {
                var cats = kinds.filter(function (k) { return !ql || k.label.toLowerCase().indexOf(ql) === 0 })
                                .map(function (k) { return { label: k.label, sub: k.sub, run: function () {
                                    var ins = "@" + k.id + ":", v = text.slice(0, men.start) + ins + text.slice(men.end), pos = men.start + ins.length
                                    edited(v); Qt.callLater(function () { area.forceActiveFocus(); area.cursorPosition = pos }) } } })
                return ql ? cats.concat(ppl) : cats
            }
            if (men.kind === "file") return fileOptions(q.trim(), null)
            if (men.kind === "folder") return q.trim() ? [{ label: q.trim(), mono: true, sub: "Where a new file is to be put",
                run: function () { root.settle(q.trim(), "folder:" + q.trim().toLowerCase(), { kind: "folder", label: q.trim(), sub: "folder" }) } }] : []
            if (men.kind === "program") return programOptions(q)
            return deadlineOptions(q, null)
        }
        if (!m) return []
        if (m.kind === "person") return people.filter(function (p) { return p.name === m.text })
                                               .map(function (p) { return { label: p.name, sub: p.sub, run: function () { root.choose(m, { name: p.name, label: p.name, sub: p.sub, account: p.account }) } } })
        if (m.kind === "file") return fileOptions(m.text, m)
        if (m.kind === "date") {
            var w = typeof falcon.readWhen === "function" ? falcon.readWhen(m.text) : { at: "" }
            var d = w.at ? new Date(w.at) : parseDate(m.text)
            return d ? [{ label: "Final deadline", sub: Time.date(d), run: function () { root.choose(m, { role: "final", v: d.toISOString(), label: "Final deadline", sub: Time.date(d) }) } },
                        { label: "Soft deadline", sub: Time.date(d), run: function () { root.choose(m, { role: "soft", v: d.toISOString(), label: "Soft deadline", sub: Time.date(d) }) } }] : []
        }
        if (m.kind === "program") {
            var exe = programs.filter(function (p) { return p[0].toLowerCase() === m.text.toLowerCase() })[0][1]
            return [{ label: exe, mono: true, sub: hostHint ? "on " + hostHint : "Confirm the person first to check theirs.", run: function () { root.choose(m, { exe: exe, label: exe, sub: "program" }) } }]
        }
        return []
    }

    // what was found while typing
    Flow {
        visible: root.uniq.length > 0
        width: root.width
        spacing: 6
        Txt { text: "Found while typing"; color: Theme.text3; font.pixelSize: 12; height: 22; elide: Text.ElideNone }
        Repeater {
            model: root.uniq
            Rectangle {
                required property var modelData
                readonly property var ok: root.conf[modelData.m.key]
                readonly property bool ig: !!root.ignored[modelData.m.key]
                width: fc.implicitWidth + 16
                height: 22
                radius: 11
                color: Theme.surface2
                border.width: 1
                border.color: fa.containsMouse ? Theme.borderStrong : Theme.border
                opacity: ig ? 0.5 : 1
                Row {
                    id: fc
                    anchors.centerIn: parent
                    spacing: 5
                    Rectangle { width: 7; height: 7; radius: 2; color: root.kindColor[modelData.m.kind]; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: modelData.m.text; font.pixelSize: 12; font.strikeout: ig; elide: Text.ElideNone }
                    Txt { text: ok ? "✓" : "?"; color: ok ? Theme.ok : Theme.text4; font.pixelSize: 12; elide: Text.ElideNone }
                }
                MouseArea { id: fa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: { var g = Object.assign({}, root.ignored); g[modelData.m.key] = false; root.ignored = g; root.openAt = modelData.i } }
            }
        }
        Txt {
            readonly property int n: root.uniq.filter(function (u) { return root.conf[u.m.key] }).length
            text: "· " + n + " of " + root.uniq.length + " confirmed" + (n && n < root.uniq.length ? ". The model is asked only about the rest." : n === root.uniq.length ? ". The model only has to read what is left." : "")
            color: Theme.text3; font.pixelSize: 12; height: 22; elide: Text.ElideNone
        }
    }
    readonly property var uniq: {
        var out = []
        matches.forEach(function (x, i) { if (!out.some(function (u) { return u.m.key === x.key })) out.push({ m: x, i: i }) })
        return out
    }
}
