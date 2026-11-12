import QtQuick
import "."

// DETECTIVE: what a person seems to be trying to do, read from several things happening together on a machine. A case is a pattern and its evidence, never an
// accusation: it says what it looks like, how far along it is (and what has not happened yet), shows the picture and the story in order, and says what would
// make it innocent. It is Detective's own conclusion; what you make of it is recorded (explained, accepted, dismissed).
// The page, top to bottom: the cases with the one picked beside them; its Evidence (the picture and the story in order, as two tabs); and what Detective
// noticed, each thing on its own with what would make it harmless, in rows across the width.
// An IT Admin sees every machine but their own and another Admin's.
Page {
    id: page
    objectName: "detectiveView"

    property var cases: []
    property var ov: ({ by_level: { noted: 0, "case": 0, urgent: 0 }, by_intent: {}, reviewed: 0 })
    property string show: "open"                 // open | noted | reviewed
    property int sel: { var a = Nav.takeArrive("detective"); return a !== null ? Number(a) : 0 }
    property var det: null                       // detective.case for the case on the right
    property string note: ""
    property string evTab: "picture"             // the evidence: the picture first, the story in order as the other tab
    readonly property var cur: { for (var i = 0; i < cases.length; i++) if (cases[i].id === sel) return cases[i]; return cases.length ? cases[0] : null }
    readonly property var levelTone: ({ urgent: "danger", "case": "warn", noted: "t4", quiet: "t4" })

    function load() {
        if (!falcon.isConnected) return
        var p = show === "reviewed" ? { status: "reviewed" } : { include_noted: show === "noted", status: "open" }
        falcon.call("detective.cases", p, function (ok, r) {
            if (!ok) return
            var rows = r.cases || []
            page.cases = rows
            if (rows.length && !rows.some(function (c) { return c.id === page.sel })) page.sel = rows[0].id
        })
        falcon.call("detective.overview", {}, function (ok, r) { if (ok && r.by_level) page.ov = r })
    }
    function loadCase() {
        if (!cur) { det = null; return }
        var id = cur.id
        falcon.call("detective.case", { case_id: id }, function (ok, r) { if (ok && page.cur && page.cur.id === id) page.det = r })
    }
    onCurChanged: { note = ""; det = null; loadCase() }
    onShowChanged: load()
    function review(outcome) {
        falcon.call("detective.review", { case_id: cur.id, outcome: outcome, note: note }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Could not record that"); return }
            Msg.ok("Recorded: " + outcome)
            page.note = ""
            page.load()
        })
    }
    Component.onCompleted: load()
    Connections { target: falcon; function onConnected() { page.load() } function onPushReceived(type, payload) { if (/^detective/.test(type)) again.restart() } }
    Timer { id: again; interval: 400; onTriggered: { page.load(); page.loadCase() } }

    // a paragraph of the case told in words: the words, with each fact marked by its kind (dt-tell, .hl.ok)
    readonly property var factColor: ({ person: Theme.ser1, file: Theme.ser2, time: Theme.ser5, program: Theme.ser3, machine: Theme.ser6 })
    component Told: Flow {
        id: tl
        property var parts: []
        // a word at a time, so the marks wrap with the text. Punctuation right after a fact stays with it; at the seam between two
        // pieces, a piece that starts with a letter or a digit after one that does not end in a space gets one ("a restricted file" +
        // "was created" read "filewas"; a sentence's "." + "What" read ".What": the user, 11 Nov 2026)
        readonly property var words: {
            var out = []
            function ends(x) { return x.c !== undefined ? x.tail || x.t : x.t }
            parts.forEach(function (p) {
                var txt = String(p.text), last = out[out.length - 1]
                if (last && /^[A-Za-z0-9\u00C0-\u024F]/.test(txt) && !/[\s(\[\u201C\u2018"']$/.test(ends(last))) { if (last.c !== undefined) last.tail += " "; else last.t += " " }
                if (p.kind && page.factColor[p.kind]) { out.push({ t: txt, c: page.factColor[p.kind], mono: p.kind === "file" || p.kind === "machine", tail: "" }); return }
                var ws = txt.match(/\S+\s*|\s+/g) || []
                ws.forEach(function (w, i) {
                    var l = out[out.length - 1]
                    if (i === 0 && l && l.c !== undefined && /^[^\sA-Za-z0-9]/.test(w)) l.tail += w
                    else if (/^\s+$/.test(w) && l) { if (l.c !== undefined) l.tail += w; else l.t += w }
                    else out.push({ t: w })
                })
            })
            return out
        }
        Repeater {
            model: tl.words
            delegate: Row {
                required property var modelData
                height: 21.7
                Rectangle {
                    visible: modelData.c !== undefined
                    width: fw.implicitWidth + 4; height: 20; y: 1; radius: 2
                    color: visible ? Theme.alpha(modelData.c, 0.18) : "transparent"
                    Rectangle { visible: parent.visible; anchors.bottom: parent.bottom; width: parent.width; height: 2; color: modelData.c !== undefined ? modelData.c : "transparent" }
                    Txt { id: fw; x: 2; anchors.verticalCenter: parent.verticalCenter; text: modelData.t; mono: !!modelData.mono; font.pixelSize: modelData.mono ? 13 : 14; elide: Text.ElideNone }
                }
                Txt { visible: modelData.c === undefined || modelData.tail !== ""; height: 21.7; verticalAlignment: Text.AlignVCenter; text: modelData.c === undefined ? modelData.t : modelData.tail; font.pixelSize: 14; elide: Text.ElideNone; textFormat: Text.PlainText; wrapMode: Text.NoWrap }
            }
        }
    }

    function openFor(c) { var h = (Time.now - Time.ms(c.last_at)) / 3600000; return h < 1 ? Math.max(1, Math.round(h * 60)) + "m" : h < 48 ? Math.round(h) + "h" : Math.round(h / 24) + " days" }
    component Head: Txt { color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66; elide: Text.ElideNone }
    readonly property var levelWord: ({ urgent: "Urgent", "case": "Case", noted: "Noted" })
    function levelTint(l) { return l === "urgent" ? Theme.crit : l === "case" ? Theme.med : Theme.text3 }

    // --- the version 1 concept's layout (docs/design/concepts-admin.html, AdminDetectivePage) ----------------------------------------------------
    property int exp: 0
    property int cp: 0                                   // the cases' page, five at a time
    readonly property int per: Math.max(2, Math.round(5 * Theme.viewScale))   // five on the design's 900-high window; follows the screen
    property bool loading: false
    property int pickedId: 0
    onSelChanged: { pickedId = cur ? cur.id : 0; loading = true; ldT.restart() }
    Timer { id: ldT; interval: Theme.loadMs; onTriggered: page.loading = false }
    readonly property var urgentCases: cases.filter(function (c) { return c.level === "urgent" })
    situation: {
        if (!cases.length) return "Nothing to look at. Detective watches by itself; when several small things add up to a pattern, it appears here."
        var depts = cases.map(function (c) { var m = Fleet.byHost[c.host]; return m ? m.dept : null }).filter(function (d, i, a) { return d !== null && a.indexOf(d) === i })
        return Theme.many(cases.length, "open case") + (depts.length ? " across " + Theme.many(depts.length, "department") : "") + "."
               + (urgentCases.length ? " " + Theme.fmt(urgentCases.length) + " urgent: " + Theme.listNames(urgentCases.map(function (c) { return c.intent.toLowerCase() + " on " + c.host }), 3) + "." : "")
               + " Nobody at a machine is told."
    }
    situationAt: Time.now

    // the concept's words for how far a case got (DT_STAGE, DT_NEXT, DT_DID)
    readonly property var stageSaid: ({ Reaching: "Files outside their work were opened", Gathering: "Files were gathered together", "Taking out": "Files left the machine", "Covering up": "The tracks were covered" })
    readonly property var nextSaid: ({ Gathering: "gathering files", "Taking out": "taking them off the machine", "Covering up": "covering the tracks" })
    readonly property var didSaid: ({ "Wrecking things": "Files were damaged", "Hiding something": "A file was hidden", "Copying what is on screen": "The screen was copied", "Covering up": "A record was wiped" })
    function stand(c) { return c.intent === "Copying what is on screen" && c.stage_name === "Taking out" ? "The screen was copied to the clipboard" : stageSaid[c.stage_name] || didSaid[c.intent] || c.intent }
    function ago(c) { var h = (Time.now - Time.ms(c.last_at || c.first_at)) / 3600000; return h < 1 ? Math.max(1, Math.round(h * 60)) + "m ago" : h < 48 ? Math.round(h) + "h ago" : Math.round(h / 24) + " days ago" }
    readonly property var gl: det && det.glance ? det.glance : null
    property var okRules: []
    function loadRules() { falcon.call("detective.rules", {}, function (ok, r) { page.okRules = ok ? (r.rules || []) : [] }) }
    Timer { running: true; interval: 10; onTriggered: page.loadRules() }
    readonly property var okWord: ({ drive_after_staging: "files copied onto it are not counted", mass_removal: "files it removes in bulk are not counted", many_zipped: "files packed together here are not counted" })
    readonly property var okIcon: ({ drive: "usb", program: "appstore", folder: "folder" })

    Row {
        width: parent.width
        spacing: 14
        // --- the open cases ------------------------------------------------------------------------------------------------------------------
        Box {
            id: caseP
            objectName: "caseList"
            width: (parent.width - 14) * 8 / 12
            title: "Open cases · " + page.cases.length
            sub: "every department, strongest first; click one to see what it covers, expand it to answer"
            readonly property int pages: Math.max(1, Math.ceil(page.cases.length / page.per))
            readonly property int pi: Math.min(page.cp, pages - 1)
            Column {
                width: parent.width
                spacing: 5
                Repeater {
                    model: page.cases.slice(caseP.pi * page.per, caseP.pi * page.per + page.per)
                    delegate: Card {
                        id: cc
                        required property var modelData
                        objectName: "case_" + modelData.id
                        width: parent.width
                        midW: 237
                        actW: 150
                        padV: 7
                        icon: "filesearch"
                        title: modelData.intent
                        line: page.stand(modelData) + (modelData.restricted || (page.cur && page.cur.id === modelData.id && page.gl && page.gl.restricted) ? " · restricted files involved" : "")
                        picked: page.cur !== null && page.cur.id === modelData.id
                        expandable: true
                        expanded: page.exp === modelData.id
                        onOpen: page.sel = modelData.id
                        onToggle: { page.sel = modelData.id; page.exp = expanded ? 0 : modelData.id }
                        mid: Row {
                            anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right
                            spacing: 14
                            Txt { textFormat: Text.StyledText; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone
                                  text: "<font face='" + Theme.mono + "'>" + cc.modelData.host + "</font>" + ((Fleet.byHost[cc.modelData.host] || {}).user ? " · " + Fleet.byHost[cc.modelData.host].user : "") }
                            Txt { text: page.ago(cc.modelData); color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                        }
                        // opened: what it is, what the model makes of it, a note, and the answer
                        Column {
                            width: parent.width
                            spacing: 10
                            Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text2; font.pixelSize: 13; text: cc.modelData.headline }
                            Txt { visible: !!cc.modelData.not_yet; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 13; text: cc.modelData.not_yet || "" }
                            Txt { visible: !!cc.modelData.model_says; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 13
                                  text: cc.modelData.model_says ? "The local model reads it as " + cc.modelData.model_says.toLowerCase() + ". That is its opinion, not the rules'." : "" }
                            Field { objectName: "detNote"; width: parent.width; placeholderText: "What you found out (optional); it stays with the case"; maximumLength: 500; text: page.note; onTextEdited: page.note = text }
                            Rectangle { width: parent.width; height: 1; color: Theme.border }
                            Item {
                                width: parent.width
                                height: 24
                                Txt { anchors.verticalCenter: parent.verticalCenter; text: "Your answer"; color: Theme.text3; font.pixelSize: 13 }
                                Row {
                                    anchors.right: parent.right
                                    spacing: 8
                                    Btn { objectName: "detDismissed"; small: true; text: "Dismiss"; onClicked: page.review("dismissed") }
                                    Btn { objectName: "detAccepted"; small: true; text: "Accept it"; onClicked: page.review("accepted") }
                                    Btn { objectName: "detExplained"; small: true; kind: "primary"; text: "It is explained"; onClicked: page.review("explained") }
                                }
                            }
                        }
                    }
                }
            }
            StepPager {
                visible: caseP.pages > 1
                width: parent.width
                noun: "cases"
                from: caseP.pi * page.per + 1
                to: Math.min(page.cases.length, caseP.pi * page.per + page.per)
                total: page.cases.length
                pageNo: caseP.pi
                pages: caseP.pages
                onStep: function (d) { page.cp = caseP.pi + d }
            }
            Quiet { visible: page.cases.length === 0; text: "Nothing open. Detective watches by itself and raises a case when several small things add up." }
        }
        // --- at a glance (dt-gl) --------------------------------------------------------------------------------------------------------
        Box {
            id: glance
            objectName: "casePanel"
            width: (parent.width - 14) * 4 / 12
            title: "At a glance"
            sub: page.cur ? page.cur.intent + " on <font face='" + Theme.mono + "'>" + page.cur.host + "</font>" : "pick a case on the left"
            readonly property var m: page.cur ? Fleet.byHost[page.cur.host] || null : null
            Quiet { visible: page.cur === null; text: "Pick a case on the left." }
            Column {
                visible: page.cur !== null
                width: parent.width
                Repeater {
                    model: !page.cur ? [] : [
                        ["flag", page.stand(page.cur), page.gl && page.gl.next_stage ? "no further yet; next would be " + (page.nextSaid[page.gl.next_stage] || page.gl.next_stage.toLowerCase()) : page.cur.stage_name ? "it went all the way" : "nothing came of it after that"],
                        ["lock", page.gl && page.gl.restricted ? "Restricted files are involved" : "No restricted files involved", page.gl && page.gl.restricted ? "they need an Admin's consent to leave" : "what was touched is ordinary"],
                        ["user", page.gl && page.gl.signed_in_then && page.gl.signed_in_then.length ? page.gl.signed_in_then.map(function (s) { return s.name || "someone" }).join(", ") : glance.m && glance.m.user ? glance.m.user : "Nobody signed in",
                         (glance.m && glance.m.deptName ? glance.m.deptName + " · " : "") + "signed in on " + page.cur.host + " at the time"],
                        ["desktop", page.cur.host, glance.m ? (glance.m.online ? "on now" + (glance.m.user ? ", " + glance.m.user + " signed in" : "") : "off, last seen " + (glance.m.seen ? Time.age(glance.m.seen) + " ago" : "a while ago")) : ""],
                        ["history", page.gl && page.gl.earlier && page.gl.earlier.length ? Theme.many(page.gl.earlier.length, "earlier case") + " on this machine" : "The first case on this machine",
                         page.gl && page.gl.earlier && page.gl.earlier.length ? Theme.listNames(page.gl.earlier.map(function (e) { return e.intent.toLowerCase() + " (" + e.outcome + ")" }), 2) : "nothing before this"],
                        ["clock", "Open for " + page.openFor(page.cur), "raised at " + Time.hhmm(page.gl && page.gl.raised_at ? page.gl.raised_at : page.cur.last_at) + (page.cur.status === "open" ? "; nobody has answered yet" : "")]]
                    delegate: Item {
                        required property var modelData
                        required property int index
                        width: parent.width
                        height: Math.max(28, glc.height) + 16
                        Rectangle { y: 8 + (Math.max(28, glc.height) - 28) / 2; width: 28; height: 28; radius: 7; color: Theme.surface2
                                    Icon { anchors.centerIn: parent; name: modelData[0]; size: 13; color: Theme.text3 } }
                        Column { id: glc; x: 40; y: 8 + (Math.max(28, height) - height) / 2; width: parent.width - 40; spacing: 1
                            Txt { width: parent.width; text: modelData[1]; font.weight: Font.DemiBold }
                            Txt { width: parent.width; text: modelData[2]; color: Theme.text3; font.pixelSize: 12 } }
                        Rectangle { visible: index < 5; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
            }
            Pulse { parent: glance; key: page.pickedId || null }
        }
    }

    Row {
        width: parent.width
        spacing: 14
        visible: !!page.cur
        // --- what happened, drawn ---------------------------------------------------------------------------------------------------------
        Box {
            id: whatP
            objectName: "evidencePanel"
            width: (parent.width - 14) * 8 / 12
            height: Math.max(implicitHeight, stepP.implicitHeight)
            title: "What happened"
            sub: page.cur ? page.cur.intent + " on <font face='" + Theme.mono + "'>" + page.cur.host + "</font>, " + Time.hhmm(page.cur.first_at) + " to " + Time.hhmm(page.cur.last_at) + "; each connection carries its step's number" : ""
            Item {
                width: parent.width
                height: Math.min(460, Math.max(220, graph.implicitHeight + 8))
                opacity: page.loading ? 0 : 1
                Flickable {
                    anchors.fill: parent
                    contentWidth: Math.max(width, graph.implicitWidth)
                    contentHeight: graph.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    CaseGraph { id: graph; x: 0; y: 0; story: page.cur ? page.cur.story : []; graph: page.det ? page.det.graph : ({ nodes: [], edges: [] }) }
                }
            }
            // wider than its box: it says so (dg-hint)
            Row {
                parent: whatP
                x: 17; y: whatP.height - 37
                visible: graph.implicitWidth > whatP.innerW
                spacing: 6
                Icon { name: "drag"; size: 12; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                Txt { text: "drag to move around the picture"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
            }
            Loading { parent: whatP; on: page.loading && page.cur !== null; under: whatP.headerHeight }
            Pulse { parent: whatP; key: page.pickedId || null }
        }
        // --- step by step (dt-story) -------------------------------------------------------------------------------------------------------
        Box {
            id: stepP
            objectName: "stepByStep"
            width: (parent.width - 14) * 4 / 12
            height: Math.max(implicitHeight, whatP.implicitHeight)
            title: "Step by step"
            sub: page.cur ? Theme.many(page.cur.story.length, "step") + ", in the order they happened" : ""
            Column {
                width: parent.width
                opacity: page.loading ? 0 : 1
                Repeater {
                    model: page.cur ? page.cur.story : []
                    Item {
                        required property string modelData
                        required property int index
                        readonly property var m: /^(\d\d:\d\d)\s+(.*)$/.exec(modelData)
                        width: parent.width
                        height: Math.max(18, st.height) + 10
                        Rectangle { y: 5 + (Math.max(18, st.height) - 18) / 2; width: 18; height: 18; radius: 9; color: "transparent"; border.width: 1; border.color: Theme.text3
                                    Txt { anchors.centerIn: parent; text: index + 1; font.pixelSize: 10; font.weight: Font.DemiBold; elide: Text.ElideNone } }
                        Txt { x: 28; y: 5 + st.baselineOffset - baselineOffset; width: 44; text: parent.m ? parent.m[1] : ""; mono: true; color: Theme.text3; elide: Text.ElideNone }
                        Txt { id: st; x: 82; y: 5; width: parent.width - 82; text: parent.m ? parent.m[2] : modelData; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                        Rectangle { visible: index < page.cur.story.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
            }
            Loading { parent: stepP; on: page.loading && page.cur !== null; under: stepP.headerHeight }
            Pulse { parent: stepP; key: page.pickedId || null }
        }
    }

    // --- what Detective noticed: what went on, told plainly (dt-tell) ---------------------------------------------------------------------
    Box {
        objectName: "noticedPanel"
        visible: !!page.cur
        width: parent.width
        title: "What Detective noticed"
        readonly property var told: page.det && page.det.telling ? page.det.telling : null
        sub: told && told.smoothed ? "what went on, worded by a model; every fact is Falcon's" : "what went on, from what Detective found"
        Column {
            width: parent.width
            spacing: 10
            Repeater {
                model: page.det && page.det.telling ? page.det.telling.paragraphs : []
                Told { required property var modelData; width: parent.width; parts: modelData }
            }
            Txt { visible: !page.det || !page.det.telling; width: parent.width; text: page.cur ? page.cur.headline : ""; font.pixelSize: 14; lh: 1.55; wrapMode: Text.WordWrap; elide: Text.ElideNone }
        }
        Column {
            width: parent.width
            topPadding: 10
            spacing: 12
            Rectangle { width: parent.width; height: 1; color: Theme.grid }
            Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12
                  // who wrote it, as it happened: the model when its smoothing was kept, else the system
                  text: (page.det && page.det.telling && page.det.telling.smoothed ? "Worded by a model from what Detective found; every fact is Falcon's." : "Written by Falcon from what Detective found.") + " It is a reading of the evidence, not proof." }
        }
    }

    // --- said to be fine: what Detective lets pass on one machine (dt-oks) --------------------------------------------------------------------
    Box {
        width: parent.width
        title: "Said to be fine · " + page.okRules.length
        sub: "what Detective lets pass on one machine; restricted files are never let pass"
        Column {
            width: parent.width
            PagedList {   // a long list pages in place (the user, 11 Nov 2026)
                id: op; items: page.okRules; per: 8
                delegate: Item {
                    required property var modelData
                    required property int index
                    readonly property real flex: width - 8 - 18 - 260 - 64 - 82 - tb.width - 70
                    width: parent.width; height: 37
                    Icon { x: 4; anchors.verticalCenter: parent.verticalCenter; name: page.okIcon[modelData.kind] || "check"; size: 13; color: Theme.text4 }
                    Txt { x: 36; width: 260; anchors.verticalCenter: parent.verticalCenter; mono: true; color: Theme.text2; text: modelData.value }
                    Txt { x: 310; width: parent.flex; anchors.verticalCenter: parent.verticalCenter; color: Theme.text3; font.pixelSize: 13; text: (page.okWord[modelData.graph] || "not counted") + "; restricted files still are" }
                    Txt { x: 324 + parent.flex; width: 64; anchors.verticalCenter: parent.verticalCenter; mono: true; color: Theme.text3; text: modelData.hostname || modelData.host || "" }
                    Txt { x: 402 + parent.flex; width: 82; anchors.verticalCenter: parent.verticalCenter; color: Theme.text3; font.pixelSize: 13; text: modelData.made_at ? "since " + Time.day(modelData.made_at) : "" }
                    Txt { id: tb; anchors.right: parent.right; anchors.rightMargin: 4; anchors.verticalCenter: parent.verticalCenter; text: "Take it back"; color: tba.containsMouse ? Theme.accent : Theme.text3; font.pixelSize: 12; elide: Text.ElideNone
                          MouseArea { id: tba; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                      onClicked: falcon.call("detective.rule_revoke", { rule_id: modelData.id }, function (ok, r) { if (!ok) { Msg.failed(r && r.message ? r.message : "Not taken back"); return } Msg.ok("Taken back"); page.loadRules() }) } }
                    Rectangle { visible: index < op.shown.length - 1; anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                }
            }
            Quiet { visible: page.okRules.length === 0; text: "Nothing. When you dismiss a case you can say what is fine from now on." }
        }
    }
}
