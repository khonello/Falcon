import QtQuick
import QtQuick.Controls.Basic
import "."

// A DESCRIPTION BOX THAT MARKS WHAT IT RECOGNISES AS YOU TYPE: people, files, dates and programs, each
// in its colour. Clicking a marked phrase (or pausing on a new one) asks what it is; `@` picks a
// person. What is confirmed here is what the reader is told; the model is asked only about the rest.
//
// Drawn as the concept draws it: a mirror of the text with the marks behind a transparent text box.
Column {
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
    property var mention: null              // {start, end, q} while an @ is being typed

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
            anchors.fill: parent
            leftPadding: 11; rightPadding: 11; topPadding: 8; bottomPadding: 8
            wrapMode: TextEdit.Wrap
            font.family: Theme.sans
            font.pixelSize: 14
            color: Theme.text
            selectByMouse: true
            selectionColor: Theme.alpha(Theme.accent, 0.3)
            placeholderText: "What needs doing? Type @ to pick a person."
            placeholderTextColor: Theme.text4
            background: null
            text: root.text
            onTextChanged: {
                if (text !== root.text) root.edited(text)
                var c = cursorPosition, mm = /@([\w.]*)$/.exec(text.slice(0, c))
                root.mention = mm ? { start: c - mm[0].length, end: c, q: mm[1] } : null
                pause.restart()
            }
            onCursorPositionChanged: if (!root.mention) root.openAt = -1
            onReleased: {
                var c = cursorPosition
                root.openAt = root.matches.findIndex(function (m) { return c >= m.start && c <= m.end })
            }
            Keys.onEscapePressed: { root.openAt = -1; root.mention = null }
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
            readonly property var opts: root.optionsFor(m, root.mention)
            visible: m !== null || root.mention !== null
            readonly property rect at: m ? area.positionToRectangle(m.end) : root.mention ? area.positionToRectangle(root.mention.start) : Qt.rect(0, 0, 0, 0)
            x: Math.max(0, Math.min(at.x - 20, parent.width - width))
            y: at.y + at.height + 6
            width: 310
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
                    Txt { text: picker.m ? "Is this a " + root.kindWord[picker.m.kind] + "?" : "Who is this for?"; color: Theme.text3; font.pixelSize: 12; width: parent.width - 120 }
                    Txt { visible: picker.m !== null; text: picker.m ? picker.m.text : ""; font.weight: Font.Medium; font.pixelSize: 12; width: 100; horizontalAlignment: Text.AlignRight }
                }
                Txt { visible: picker.opts.length === 0 && root.mention !== null; text: "No one matches “" + (root.mention ? root.mention.q : "") + "”."; color: Theme.text3; font.pixelSize: 12; leftPadding: 8 }
                Repeater {
                    model: picker.opts
                    Rectangle {
                        required property var modelData
                        width: pcol.width
                        height: oc.height + 12
                        radius: Theme.radiusSm
                        color: oa.containsMouse ? Theme.accentSoft : "transparent"
                        Column {
                            id: oc
                            x: 8; y: 6
                            width: parent.width - 16
                            Txt { width: parent.width; text: modelData.label; mono: !!modelData.mono; font.pixelSize: 12; wrapMode: Text.WrapAnywhere; elide: Text.ElideNone }
                            Txt { visible: !!modelData.sub; width: parent.width; text: modelData.sub || ""; color: Theme.text3; font.pixelSize: 11 }
                        }
                        MouseArea { id: oa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: modelData.run() }
                    }
                }
                Rectangle { visible: picker.m !== null; width: parent.width; height: 1; color: Theme.border }
                Link {
                    visible: picker.m !== null
                    leftPadding: 8; topPadding: 6
                    text: picker.m ? "Not a " + root.kindWord[picker.m.kind] : ""
                    font.pixelSize: 12
                    onClicked: { var g = Object.assign({}, root.ignored); g[picker.m.key] = true; root.ignored = g; root.openAt = -1 }
                }
            }
        }
    }

    function choose(m, o) { var c = Object.assign({}, conf); c[m.key] = Object.assign({ kind: m.kind, text: m.text }, o); conf = c; openAt = -1; area.forceActiveFocus() }
    function pickPerson(p) {
        var v = text.slice(0, mention.start) + p.name + text.slice(mention.end)
        var c = Object.assign({}, conf); c["person:" + p.name.toLowerCase()] = { kind: "person", text: p.name, name: p.name, label: p.name, sub: p.sub, account: p.account }; conf = c
        mention = null; openAt = -1
        edited(v)
    }
    property var fileHits: ({})               // a file name -> what the index has under it
    function lookFile(name) {
        if (fileHits[name] !== undefined) return
        var h = Object.assign({}, fileHits); h[name] = []; fileHits = h
        falcon.call("index.search", { query: name }, function (ok, r) {
            var x = Object.assign({}, root.fileHits); x[name] = ok ? (r.results || []) : []; root.fileHits = x
        })
    }
    function optionsFor(m, men) {
        if (men && !m) return people.filter(function (p) { return p.name.toLowerCase().indexOf(men.q.toLowerCase()) >= 0 }).slice(0, 6)
                                    .map(function (p) { return { label: p.name, sub: p.sub, run: function () { root.pickPerson(p) } } })
        if (!m) return []
        if (m.kind === "person") return people.filter(function (p) { return p.name === m.text })
                                               .map(function (p) { return { label: p.name, sub: p.sub, run: function () { root.choose(m, { name: p.name, label: p.name, sub: p.sub, account: p.account }) } } })
        if (m.kind === "file") {
            lookFile(m.text)
            var hits = (fileHits[m.text] || []).filter(function (f) { return String(f.filename || f.path || "").toLowerCase().indexOf(m.text.toLowerCase()) >= 0 })
            return hits.slice(0, 4).map(function (f) {
                return { label: f.path || f.filename, sub: (f.hostname || "") + (f.resource_tag ? " · " + f.resource_tag : ""), mono: true,
                         run: function () { root.choose(m, { label: m.text, sub: f.path, file_index_id: f.id }) } }
            }).concat([{ label: "A new file", sub: hits.length ? "A different file with this name, not created yet" : "Not in the file index yet. A check can expect it to be created.",
                         run: function () { root.choose(m, { label: m.text, sub: "a new file" }) } }])
        }
        if (m.kind === "date") {
            var d = parseDate(m.text)
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
