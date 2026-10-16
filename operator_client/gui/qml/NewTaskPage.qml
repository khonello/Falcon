import QtQuick
import "."

// NEW TASK. Describe the work in plain words; people, files, dates and programs are marked as you type
// and can be confirmed there. "Read it" asks the local model about the rest (task.propose) and nothing
// is created until you say so: the right shows the task that will be created, every value marked with
// where it came from -- found by rule, chosen by the model, needs your input, or set by you.
Page {
    id: page
    objectName: "newTask"
    bare: true

    property string text: ""
    property var conf: ({})
    property var ignored: ({})
    property string checked: ""            // the text the proposal was read from
    property bool busy: false
    property var proposal: null
    property var tasks: []                 // [{title, phrase, who, whoSrc, final, finalSrc, soft, softSrc, none, checks: [...]}]
    property int cur: 0
    readonly property bool read: proposal !== null
    readonly property bool stale: read && text.trim() !== checked.trim()

    readonly property var people: {
        var out = []
        Fleet.machines.forEach(function (m) { if (m.user && m.account) out.push({ name: m.user, sub: m.host + " · " + m.deptName, host: m.host, account: m.account }) })
        return out.length ? out : Fleet.cachedPeople()          // before the Engine has answered, or with no Engine: what was known last time
    }
    readonly property var confirmedPerson: {
        for (var k in conf) if (conf[k].kind === "person") return conf[k]
        return null
    }
    readonly property var foundPerson: {
        if (confirmedPerson) return confirmedPerson
        var m = smart.matches.filter(function (x) { return x.kind === "person" && !page.ignored[x.key] })
        if (!m.length) return null
        var p = people.filter(function (q) { return q.name === m[0].text })[0]
        return p ? { name: p.name, account: p.account, sub: p.sub } : null
    }
    readonly property var srcColor: ({ rule: Theme.ser6, model: Theme.ser1, input: Theme.med, you: Theme.accent, none: Theme.text4 })
    readonly property var srcWord: ({ rule: "Rule", model: "Model", input: "Needs input", you: "You", none: "—" })
    readonly property var srcLong: ({ rule: "Found by rule", model: "Chosen by the model", input: "Needs your input", you: "Set by you" })
    readonly property var fileIntents: [["create", "Create"], ["update", "Update"], ["exists", "Must exist"]]
    readonly property var progIntents: [["used", "Used"], ["used_with_file", "Used with file"], ["installed_available", "Installed"], ["closed_not_running", "Not running"]]
    function intentWord(i) { var all = fileIntents.concat(progIntents); for (var k = 0; k < all.length; k++) if (all[k][0] === i) return all[k][1]; return i }

    function readIt() {
        if (!foundPerson) return
        busy = true
        var at = text
        falcon.call("task.propose", { description: at.trim(), assignee_account_id: foundPerson.account, hints: smart.hints, now: page.nowLocal() }, function (ok, r) {
            page.busy = false
            if (!ok) { Msg.failed(r && r.message ? r.message : "Nothing came back"); return }
            page.checked = at
            page.proposal = r
            page.build(r)
        })
    }
    function build(r) {
        var vals = Object.keys(conf).map(function (k) { return conf[k] })
        var fin = vals.filter(function (c) { return c.kind === "date" && c.role === "final" }).pop()
        var soft = vals.filter(function (c) { return c.kind === "date" && c.role === "soft" }).pop()
        var files = vals.filter(function (c) { return c.kind === "file" })
        var checks = (r.items || []).map(function (it, i) {
            var hit = files.filter(function (f) { return f.text.toLowerCase() === String(it.name).toLowerCase() })[0]
            return { target_type: it.target_type, intent: it.intent, name: it.name, path: it.path || null,
                     file_index_id: hit && hit.file_index_id ? hit.file_index_id : it.file_index_id || null,
                     linked_item_index: it.linked_item_index === undefined ? null : it.linked_item_index,
                     src: it.source === "hint" || it.intent_by === "hint" || hit ? "you" : it.populated_by === "manual" ? "you" : it.intent_by === "rule" ? "rule" : "model",
                     why: it.intent_by === "hint" ? "You set this with @" : it.source === "hint" ? "You marked the " + it.target_type + " with @; “" + page.intentWord(it.intent) + "” was " + (it.intent_by === "rule" ? "read from your words" : "chosen by the model")
                          : hit ? "You picked it while typing; “" + page.intentWord(it.intent) + "” was " + (it.intent_by === "rule" ? "read from your words" : "chosen by the model")
                          : it.intent_by === "rule" ? "Found and settled by rule: the words around it say “" + page.intentWord(it.intent) + "”" : "Chosen by the model from the intents for a " + it.target_type }
        })
        var one = {
            title: text.trim().split(/[.\n]/)[0].slice(0, 80), titleSrc: "rule", phrase: text.trim(),
            who: foundPerson.name, whoAccount: foundPerson.account, whoSrc: confirmedPerson ? "you" : "rule",
            // the Engine finds a deadline as the words in the text ("by tomorrow evening"); the task needs a time. Put in a time here, or say it is still
            // needed: never send the words on as if they were one (the Engine refuses them, and the person would see only "must be ISO 8601")
            final: fin ? fin.v : r.final_deadline_at ? new Date(r.final_deadline_at).toISOString() : page.whenOf(r.final_deadline),
            finalSrc: fin ? "you" : r.final_deadline_at ? (r.deadline_source === "hint" ? "you" : "rule") : r.final_deadline ? (page.whenOf(r.final_deadline) && !(r.flags || []).some(function (f) { return f.kind === "ambiguous_deadline" }) ? "rule" : "input") : "none",
            soft: soft ? soft.v : r.soft_deadline_at ? new Date(r.soft_deadline_at).toISOString() : page.whenOf(r.soft_deadline), softSrc: soft ? "you" : r.soft_deadline_at ? "you" : r.soft_deadline ? (page.whenOf(r.soft_deadline) ? "rule" : "input") : "none",
            none: false, checks: checks
        }
        var out = [one]
        ;(r.proposed_split || []).slice(1).forEach(function (s) {
            var phrase = typeof s === "string" ? s : (s.text || s.description || "")
            out.push({ title: phrase.slice(0, 80), titleSrc: "rule", phrase: phrase, who: one.who, whoAccount: one.whoAccount, whoSrc: "rule",
                       final: one.final, finalSrc: one.finalSrc, soft: null, softSrc: "none", none: false, checks: [] })
        })
        if (out.length > 1 && (r.proposed_split || [])[0]) { var p0 = r.proposed_split[0]; out[0].phrase = typeof p0 === "string" ? p0 : (p0.text || p0.description || one.phrase) }
        tasks = out
        cur = 0
    }
    function whenOf(phrase) {
        if (!phrase) return null
        if (typeof falcon.readWhen === "function") { var w = falcon.readWhen(String(phrase)); return w.at ? new Date(w.at).toISOString() : null }
        var t = smart.parseDate(String(phrase)); return t ? t.toISOString() : null
    }
    // the assigner's own UTC offset as +hh:mm, so "tomorrow 3pm" means their clock, not the Engine's
    function nowLocal() {
        var d = new Date(), p = function (n) { return ("0" + n).slice(-2) }
        return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + "T" + p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds()) + page.zone()
    }
    function zone() { var o = -new Date().getTimezoneOffset(), a = Math.abs(o); return (o < 0 ? "-" : "+") + ("0" + Math.floor(a / 60)).slice(-2) + ":" + ("0" + (a % 60)).slice(-2) }
    function patch(i, f) { var t = tasks.slice(); t[i] = Object.assign({}, t[i], f); tasks = t }
    function patchCheck(i, k, f) {
        var cs = tasks[i].checks.slice(); cs[k] = Object.assign({}, cs[k], f, { src: "you", why: "Set by you" })
        patch(i, { none: false, checks: cs })
    }
    function blocked(t) { return (t.checks.length === 0 && !t.none) || t.checks.some(function (c) { return !c.name }) }
    readonly property int open: tasks.filter(blocked).length
    readonly property var t: tasks.length ? tasks[Math.min(cur, tasks.length - 1)] : null

    function create(asOne) {
        var list = asOne ? [Object.assign({}, tasks[0], { phrase: text.trim(), checks: tasks.reduce(function (a, x) { return a.concat(x.checks) }, []) })] : tasks
        var left = list.length, failed = false
        list.forEach(function (x) {
            var payload = { description: x.phrase, assignee_account_id: x.whoAccount, verification_mode: x.checks.length ? "stack" : "none" }
            if (x.checks.length) payload.items = x.checks.map(function (c) {
                return { target_type: c.target_type, intent: c.intent, name: c.name, path: c.path, file_index_id: c.file_index_id,
                         linked_item_index: c.linked_item_index, populated_by: c.src === "model" ? "llm" : "manual" }
            })
            else payload.confirm_none = true
            if (x.final) payload.final_deadline_at = x.final
            if (x.soft) payload.soft_deadline_at = x.soft
            falcon.call("task.create", payload, function (ok, r) {
                if (!ok) { failed = true; Msg.failed(r && r.message ? r.message : "It was not created") }
                if (--left === 0 && !failed) { Msg.ok(list.length > 1 ? "Created " + list.length + " tasks" : "Task created"); Nav.go("tasks") }
            })
        })
    }

    component Lbl: Txt { width: 104; topPadding: 5; color: Theme.text3; elide: Text.ElideNone }
    component Head: Txt { color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
    component Src: Row {
        property string s: "none"
        property string why: ""
        spacing: 5
        Rectangle { width: 6; height: 6; radius: 3; color: page.srcColor[parent.s]; anchors.verticalCenter: parent.verticalCenter }
        Txt { text: page.srcWord[parent.s]; color: parent.s === "input" ? Theme.med : Theme.text3; font.pixelSize: 11; elide: Text.ElideNone }
    }

    Row {
        width: parent.width
        spacing: 14

        // --- the description, and once read, the details -------------------------------------------
        Panel {
            id: left
            width: (parent.width - 14) / 2
            title: "New task"
            sub: "describe the work in plain words"
            Column {
                width: parent.width
                spacing: 8
                Head { text: "DESCRIPTION" }
                SmartText {
                    id: smart
                    width: parent.width
                    text: page.text
                    people: page.people
                    conf: page.conf
                    ignored: page.ignored
                    hostHint: page.foundPerson ? (page.people.filter(function (p) { return p.name === page.foundPerson.name })[0] || { host: "" }).host : ""
                    onEdited: function (t) { page.text = t }
                    onConfChanged: page.conf = conf
                    onIgnoredChanged: page.ignored = ignored
                }
                Row {
                    spacing: 10
                    Btn {
                        small: true
                        kind: !page.read || page.stale ? "primary" : "default"
                        loading: page.busy
                        enabled: !page.busy && page.foundPerson !== null && (page.read ? page.stale : page.text.trim() !== "")
                        text: page.busy ? "Reading" : !page.read ? "Read it" : page.stale ? "Check again" : "Checked"
                        onClicked: page.readIt()
                    }
                    // the hint; while the box is empty it runs on into "use an example", as the concept's does
                    Txt {
                        anchors.verticalCenter: parent.verticalCenter
                        width: left.width - 140
                        color: Theme.text3
                        font.pixelSize: 12
                        readonly property bool empty: !page.busy && !page.read && page.text.trim() === ""
                        textFormat: empty ? Text.StyledText : Text.PlainText
                        linkColor: Theme.accent
                        text: page.busy ? "The local model is reading it…"
                              : empty ? "Write what needs doing, or <a href=\"x\">use an example</a>."
                              : !page.read ? (page.foundPerson ? "It proposes what to check, and when. Nothing is created yet." : "Name who it is for: type @ to pick a person.")
                              : page.stale ? "The details below are for the previous text." : "Read by the local model."
                        onLinkActivated: page.text = "Have " + (page.people.length ? page.people[0].name : "Kojo") + " reconcile the Q3 invoices in Excel into reconciliation.xlsx by Friday 17:00, and write up q3-summary.docx for Finance."
                        HoverHandler { enabled: parent.empty; cursorShape: parent.hoveredLink ? Qt.PointingHandCursor : Qt.ArrowCursor }
                    }
                }

                // what the model read, marked by where each part came from
                Column {
                    visible: page.read
                    width: parent.width
                    spacing: 8
                    topPadding: 12
                    Rectangle { width: parent.width; height: 1; color: Theme.border }
                    Head { text: "WHAT THE MODEL READ"; topPadding: 6 }
                    Rectangle {
                        width: parent.width
                        height: annotated.implicitHeight + 16
                        radius: 5
                        color: Theme.surface2
                        opacity: page.stale ? 0.5 : 1
                        Txt {
                            id: annotated
                            x: 10; y: 8
                            width: parent.width - 20
                            wrapMode: Text.Wrap
                            elide: Text.ElideNone
                            textFormat: Text.RichText
                            text: {
                                var t = page.checked, out = "", at = 0, ms = smart.find(t)
                                ms.forEach(function (m) {
                                    var s = page.conf[m.key] ? "you" : m.kind === "person" || m.kind === "date" ? "rule" : "model"
                                    out += smart.esc(t.slice(at, m.start)) + "<span style='background-color:" + Theme.alpha(page.srcColor[s], 0.14) + "'>" + smart.esc(t.slice(m.start, m.end)) + "</span>"
                                    at = m.end
                                })
                                return out + smart.esc(t.slice(at))
                            }
                        }
                    }
                    Row {
                        spacing: 14
                        Repeater {
                            model: ["rule", "model", "input", "you"]
                            Row { required property var modelData; spacing: 6
                                  Rectangle { width: 10; height: 10; radius: 2; color: page.srcColor[modelData]; anchors.verticalCenter: parent.verticalCenter }
                                  Txt { text: page.srcLong[modelData]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
                        }
                    }
                }

                // the details, for each task
                Column {
                    visible: page.read && page.t !== null
                    width: parent.width
                    spacing: 10
                    topPadding: 12
                    opacity: page.stale ? 0.5 : 1
                    Rectangle { width: parent.width; height: 1; color: Theme.border }
                    Item {
                        width: parent.width; height: 26
                        Head { text: "DETAILS"; anchors.verticalCenter: parent.verticalCenter }
                        Segmented {
                            visible: page.tasks.length > 1
                            anchors.right: parent.right
                            options: page.tasks.map(function (x, j) { return { value: j, label: "Task " + (j + 1) + (page.blocked(x) ? " ●" : "") } })
                            value: page.cur
                            onPicked: function (v) { page.cur = v }
                        }
                    }
                    Txt { text: "Who and when"; color: Theme.text2; font.pixelSize: 12; font.weight: Font.Medium }
                    Row { width: parent.width; Lbl { text: "Title" }
                          Field { width: parent.width - 104; text: page.t ? page.t.title : ""; onTextEdited: page.patch(page.cur, { title: text, titleSrc: "you" }) } }
                    Row { width: parent.width; Lbl { text: "Assignee" }
                          Select { width: parent.width - 104; search: true; value: page.t ? page.t.whoAccount : null
                                   options: page.people.map(function (p) { return { value: p.account, label: p.name + " · " + p.host } })
                                   onPicked: function (v) { var p = page.people.filter(function (q) { return q.account === v })[0]; page.patch(page.cur, { who: p.name, whoAccount: v, whoSrc: "you" }) } } }
                    Row { width: parent.width; spacing: 8; Lbl { text: "Deadlines" }
                          DateTimeField { width: (parent.width - 120) / 2; placeholder: "Final"; value: page.t ? page.t.final : null; onChanged: function (v) { page.patch(page.cur, { final: v, finalSrc: "you" }) } }
                          DateTimeField { width: (parent.width - 120) / 2; placeholder: "Soft (optional)"; value: page.t ? page.t.soft : null; onChanged: function (v) { page.patch(page.cur, { soft: v, softSrc: "you" }) } } }
                    Txt { text: "What done looks like"; color: Theme.text2; font.pixelSize: 12; font.weight: Font.Medium; topPadding: 6 }
                    Row {
                        width: parent.width
                        Lbl { text: "Checks"; color: page.t && page.blocked(page.t) ? Theme.med : Theme.text3 }
                        Column {
                            width: parent.width - 104
                            spacing: 8
                            Repeater {
                                model: page.t ? page.t.checks : []
                                Row {
                                    required property var modelData
                                    required property int index
                                    spacing: 6
                                    Select { width: 92; small: true; value: modelData.target_type; options: [{ value: "file", label: "File" }, { value: "program", label: "Program" }]
                                             onPicked: function (v) { page.patchCheck(page.cur, index, { target_type: v, intent: v === "file" ? "exists" : "used", name: "" }) } }
                                    Field { width: parent.parent.width - 92 - 130 - 40 - 18; height: Theme.controlSm; text: modelData.name; placeholderText: modelData.target_type === "file" ? "File or folder" : "Program"
                                            onTextEdited: page.patchCheck(page.cur, index, { name: text }) }
                                    Select { width: 130; small: true; value: modelData.intent
                                             options: (modelData.target_type === "file" ? page.fileIntents : page.progIntents).map(function (x) { return { value: x[0], label: x[1] } })
                                             onPicked: function (v) { page.patchCheck(page.cur, index, { intent: v }) } }
                                    Btn { small: true; kind: "text"; iconName: "close"; onClicked: { var cs = page.t.checks.slice(); cs.splice(index, 1); page.patch(page.cur, { checks: cs }) } }
                                }
                            }
                            Btn { visible: page.t !== null && page.t.checks.length > 0; small: true; iconName: "plus"; text: "Add check"
                                  onClicked: page.patch(page.cur, { none: false, checks: page.t.checks.concat([{ target_type: "file", intent: "create", name: "", src: "you", why: "Set by you" }]) }) }
                            // no checks: a decision, asked plainly
                            Rectangle {
                                visible: page.t !== null && page.t.checks.length === 0
                                width: parent.width
                                height: dec.height + 24
                                radius: Theme.radius
                                readonly property color c: page.t && page.t.none ? Theme.ok : Theme.med
                                color: Theme.alpha(c, 0.09)
                                border.width: 1
                                border.color: Theme.alpha(c, 0.35)
                                Column {
                                    id: dec
                                    x: 14; y: 12
                                    width: parent.width - 28
                                    spacing: 6
                                    Txt { width: parent.width; font.weight: Font.DemiBold; wrapMode: Text.WordWrap; elide: Text.ElideNone
                                          text: page.t && page.t.none ? "No checks. You will verify it by hand." : "How should this task be checked?" }
                                    Txt { width: parent.width; color: Theme.text2; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                                          text: page.t && page.t.none ? "Nothing is watched. You close the task when you are satisfied it is done."
                                                : "“" + (page.t ? page.t.phrase : "") + "” names no file, folder or program, so there is nothing to watch yet." }
                                    Row {
                                        spacing: 8
                                        visible: page.t !== null && !page.t.none
                                        Btn { iconName: "plus"; text: "Add a check"; onClicked: page.patch(page.cur, { none: false, checks: [{ target_type: "file", intent: "create", name: "", src: "you", why: "Set by you" }] }) }
                                        Txt { text: "or"; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                                        Btn { iconName: "eye"; text: "No checks, I will verify it by hand"; onClicked: page.patch(page.cur, { none: true }) }
                                    }
                                    Btn { visible: page.t !== null && page.t.none; small: true; kind: "text"; text: "Change"; onClicked: page.patch(page.cur, { none: false }) }
                                }
                            }
                        }
                    }
                }
            }
        }

        // --- what will be created ----------------------------------------------------------------------
        Panel {
            width: (parent.width - 14) / 2
            height: left.height
            fill: true
            flush: true
            title: page.tasks.length > 1 ? "Task " + (page.cur + 1) + " of " + page.tasks.length : "The task"
            sub: "what will be created"
            extra: Tag { visible: page.read; text: page.t && page.blocked(page.t) ? "Needs input" : "Ready"; c: page.t && page.blocked(page.t) ? Theme.med : Theme.ok }
            opacity: page.busy || page.stale ? 0.55 : 1

            Column {
                visible: !page.read
                anchors.centerIn: parent
                width: 300
                spacing: 8
                Icon { anchors.horizontalCenter: parent.horizontalCenter; name: page.busy ? "loading" : "filesearch"; size: 22; color: Theme.text3 }
                Txt { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3
                      text: page.busy ? "Reading the description…" : "The proposed task appears here once the description has been read." }
            }
            Column {
                visible: page.read && page.t !== null
                x: 14; y: 6
                width: parent.width - 28
                Repeater {
                    model: page.t ? [["Title", page.t.title, page.t.titleSrc],
                                     ["Assignee", page.t.who + (page.people.filter(function (p) { return p.account === page.t.whoAccount })[0] ? " · " + page.people.filter(function (p) { return p.account === page.t.whoAccount })[0].host : ""), page.t.whoSrc],
                                     ["Final deadline", page.t.final ? Time.date(page.t.final) : "Not set", page.t.final ? page.t.finalSrc : "none"],
                                     ["Soft deadline", page.t.soft ? Time.date(page.t.soft) : "Not set", page.t.soft ? page.t.softSrc : "none"]] : []
                    Item {
                        required property var modelData
                        width: parent.width; height: 34
                        Txt { width: 112; anchors.verticalCenter: parent.verticalCenter; text: modelData[0]; color: Theme.text3 }
                        Txt { x: 124; width: parent.width - 124 - 100; anchors.verticalCenter: parent.verticalCenter; text: modelData[1]
                              color: modelData[2] === "none" ? Theme.text3 : Theme.text; font.weight: modelData[0] === "Title" ? Font.Medium : Font.Normal }
                        Src { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; s: modelData[2] }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
                Txt { topPadding: 16; bottomPadding: 2; color: Theme.text3; textFormat: Text.RichText
                      text: "What done looks like" + (page.t && page.t.checks.length ? " · " + page.t.checks.length : "") + " <span style='color:" + Theme.text4 + "'>· verification, you confirm it when the work is in</span>" }
                Repeater {
                    model: page.t ? (page.t.checks.length ? page.t.checks : [null]) : []
                    Item {
                        required property var modelData
                        width: parent.width; height: 34
                        Icon { anchors.verticalCenter: parent.verticalCenter; name: !modelData ? (page.t.none ? "check" : "question") : modelData.target_type === "file" ? "file" : "appstore"; size: 13; color: Theme.text3 }
                        Txt { x: 22; width: parent.width - 22 - 100; anchors.verticalCenter: parent.verticalCenter; textFormat: Text.RichText
                              text: !modelData ? "<span style='color:" + (page.t.none ? Theme.text : Theme.med) + "'>" + (page.t.none ? "None. You will verify it by hand." : "None found yet") + "</span>"
                                    : "<span style='font-family:" + Theme.mono + ";color:" + (modelData.name ? Theme.text : Theme.med) + "'>" + (modelData.name || "No target yet") + "</span><span style='color:" + Theme.text3 + "'> · " + page.intentWord(modelData.intent) + "</span>" }
                        Src { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; s: !modelData ? (page.t.none ? "you" : "input") : modelData.name ? modelData.src : "input" }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
                Txt { topPadding: 16; bottomPadding: 2; color: Theme.text3; textFormat: Text.RichText
                      text: "Signs of progress <span style='color:" + Theme.text4 + "'>· expectations, they follow from the targets above</span>" }
                Repeater {
                    model: page.t ? page.t.checks.filter(function (c) { return c.name }) : []
                    Row {
                        required property var modelData
                        width: parent.width
                        spacing: 8
                        topPadding: 7; bottomPadding: 7
                        Icon { name: "eye"; size: 13; color: Theme.text3 }
                        Column {
                            width: parent.width - 22
                            Txt { width: parent.width; textFormat: Text.RichText
                                  text: (modelData.target_type === "program" ? (modelData.intent === "installed_available" ? "Shows up among the installed programs" : "Time in real use")
                                         : modelData.intent === "create" ? "The file appearing, then its saves" : "Saves, renames and moves of the file")
                                        + " <span style='color:" + Theme.text3 + "'>·</span> <span style='font-family:" + Theme.mono + ";color:" + Theme.text2 + "'>" + modelData.name + "</span>" }
                            Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone
                                  text: modelData.target_type === "program" ? "Counted only while it is in use: keyboard, processor and memory moving. Open but idle does not count."
                                        : "Watched through the machine's own file events, as they happen. Recognised by content, so a rename or a move does not lose it." }
                        }
                    }
                }
                Row { visible: page.t !== null && page.t.checks.filter(function (c) { return c.name }).length === 0; spacing: 8; topPadding: 7
                      Icon { name: "eyeoff"; size: 13; color: Theme.text3 }
                      Txt { text: page.t && page.t.none ? "Nothing is watched. You judge it when the work is in." : "None until a target is set."; color: Theme.text3 } }
            }
            Rectangle {
                visible: page.read
                anchors.bottom: parent.bottom
                width: parent.width
                height: 52
                color: "transparent"
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Row {
                    x: 14
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    visible: page.tasks.length > 1
                    Repeater {
                        model: page.tasks
                        Link { required property var modelData; required property int index; font.pixelSize: 12
                               text: "Task " + (index + 1) + (page.blocked(modelData) ? " · needs input" : " · ready")
                               color: index === page.cur ? Theme.text : page.blocked(modelData) ? Theme.med : Theme.text3
                               onClicked: page.cur = index }
                    }
                }
                Row {
                    anchors.right: parent.right
                    anchors.rightMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    Btn { text: "Cancel"; onClicked: Nav.go("tasks") }
                    Btn { visible: page.tasks.length > 1; enabled: !page.busy && !page.stale; text: "Keep as one"; onClicked: page.create(true) }
                    Btn { kind: "primary"; enabled: !page.busy && !page.stale && page.open === 0
                          text: page.tasks.length > 1 ? "Create " + page.tasks.length + " tasks" : "Create task"; onClicked: page.create(false) }
                }
            }
        }
    }
}
