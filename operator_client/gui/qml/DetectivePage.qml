import QtQuick
import "."

// DETECTIVE: what a person seems to be trying to do, read from several things happening together on a machine. A case is a pattern and its evidence, never an
// accusation: it says what it looks like, how far along it is (and what has not happened yet), shows the picture and the story in order, and says what would
// make it innocent. It is Detective's own conclusion; what you make of it is recorded (explained, accepted, dismissed, escalated).
// The Super User sees every machine; an Admin sees their department's machines, never their own and never another Admin's.
Page {
    id: page
    objectName: "detectiveView"

    property var cases: []
    property var ov: ({ by_level: { noted: 0, "case": 0, urgent: 0 }, by_intent: {}, reviewed: 0 })
    property string show: "open"                 // open | noted | reviewed
    property int sel: 0
    property var det: null                       // detective.case for the case on the right
    property string note: ""
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
        loadExtras()
    }
    // what Detective suggests to the other features (pause a flow, mark a folder, a follow-up task): said, never done; a person decides. And the things already said to be fine.
    property var proposals: []
    property var rules: []
    function loadExtras() {
        if (!falcon.isConnected) return
        falcon.call("proposals.list", {}, function (ok, r) { page.proposals = ok && r ? (r.proposals || []) : [] })
        falcon.call("detective.rules", {}, function (ok, r) { page.rules = ok && r ? (r.rules || []) : [] })
    }
    function decide(p, accept) {
        falcon.call("proposals.decide", { proposal_id: p.id, accept: accept }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not answered"); return }
            Msg.ok(!accept ? "Dismissed" : r.paused ? "Paused" : r.mark ? "Mark " + r.mark + " from the machine it is on, on the Restricted page" : r.task_description ? "Give this as a task: " + r.task_description : "Accepted")
            page.loadExtras()
        })
    }
    function takeBack(rule) {
        falcon.call("detective.rule_revoke", { rule_id: rule.id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not taken back"); return }
            Msg.ok("Taken back · it is weighed in full again")
            page.loadExtras()
        })
    }
    function loadCase() {
        if (!cur) { det = null; return }
        var id = cur.id
        falcon.call("detective.case", { case_id: id }, function (ok, r) { if (ok && page.cur && page.cur.id === id) page.det = r })
    }
    onCurChanged: { note = ""; det = null; loadCase() }
    onShowChanged: load()
    // what could be written down as fine, by kind: {kind: [values]} (a program, a folder or a drive that this case involves)
    readonly property var ruleKinds: {
        var out = {}, o = det && det.rule_options ? det.rule_options : []
        for (var i = 0; i < o.length; i++) { (out[o[i].kind] = out[o[i].kind] || []); if (out[o[i].kind].indexOf(o[i].value) < 0) out[o[i].kind].push(o[i].value) }
        return out
    }
    function review(outcome, remember) {
        var p = { case_id: cur.id, outcome: outcome, note: note }
        if (remember) p.remember = { kind: remember }
        falcon.call("detective.review", p, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Could not record that"); return }
            Msg.ok(outcome === "escalated" ? "Sent to the Super User" : remember ? "Recorded: " + outcome + ", and written down as fine" : "Recorded: " + outcome)
            page.note = ""
            page.load()
        })
    }
    Component.onCompleted: load()
    Connections { target: falcon; function onConnected() { page.load() } function onPushReceived(type, payload) { if (/^detective|^proposal/.test(type)) again.restart() } }
    Timer { id: again; interval: 400; onTriggered: { page.load(); page.loadCase() } }

    component Head: Txt { color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66; elide: Text.ElideNone }
    readonly property var levelWord: ({ urgent: "Urgent", "case": "Case", noted: "Noted" })
    function levelTint(l) { return l === "urgent" ? Theme.crit : l === "case" ? Theme.med : Theme.text3 }

    Strip {
        objectName: "detStrip"
        width: parent.width
        items: [
            { label: "Urgent", value: Theme.fmt(page.ov.by_level.urgent), delta: page.ov.by_level.urgent ? "worth looking at now" : "nothing urgent", dc: page.ov.by_level.urgent ? Theme.crit : undefined },
            { label: "Cases", value: Theme.fmt(page.ov.by_level["case"]), delta: page.ov.by_level["case"] ? "several things add up" : "none open", dc: page.ov.by_level["case"] ? Theme.med : undefined },
            { label: "Noted quietly", value: Theme.fmt(page.ov.by_level.noted), delta: "kept in view, not raised" },
            { label: "Reviewed", value: Theme.fmt(page.ov.reviewed), delta: "by a person, with their note" }
        ]
    }

    // --- the cases, and the one picked beside them, at one height ----------------------------------------------------------------------------
    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            objectName: "caseList"
            width: (parent.width - 14) * 7 / 12
            title: "Cases"
            sub: Nav.boss ? "every machine, strongest first" : "your department's machines, strongest first"
            tools: Segmented { objectName: "detShow"; options: [{ value: "open", label: "Open" }, { value: "noted", label: "+ Noted" }, { value: "reviewed", label: "Reviewed" }]; value: page.show; onPicked: function (v) { page.show = v } }
            rows: page.cases
            pick: page.cur ? page.cur.id : null
            onPicked: function (k) { page.sel = k }
            icon: function (c) { return c.level === "urgent" ? "alert" : "filesearch" }
            nameTitle: "What it looks like"
            nameText: function (c) { return c.intent }
            nameLine: function (c) { return c.host + " · " + Time.at(c.last_at) }
            cols: [
                { title: "Stage", width: 110, text: function (c) { return c.stage_count + " of 5 stages" } },
                { title: "Last seen", width: 100, text: function (c) { return Time.age(c.last_at) } }
            ]
            nowTitle: "Now"
            nowWidth: 130
            now: function (c) { return c.status !== "open" ? [c.status.charAt(0).toUpperCase() + c.status.slice(1), "good"] : [page.levelWord[c.level], c.level === "urgent" ? "bad" : c.level === "case" ? Theme.med : "wait"] }
            showEmpty: page.cases.length === 0
            emptyIcon: "filesearch"
            emptyTitle: page.show === "reviewed" ? "Nothing reviewed yet" : "Nothing to look at"
            emptyText: "Detective watches by itself. When several small things add up to a pattern, it appears here."
        }
        SidePanel {
            id: side
            objectName: "casePanel"
            width: (parent.width - 14) * 5 / 12
            showEmpty: !page.cur
            emptyIcon: "filesearch"
            emptyTitle: "Pick a case"
            emptyText: "It shows what it looks like and the evidence behind it."
            title: page.cur ? page.cur.intent : ""
            sub: page.cur ? page.cur.host : ""
            facts: page.cur ? [
                ["Level", page.levelWord[page.cur.level], page.levelTint(page.cur.level), false, true],
                ["Machine", page.cur.host, null, true],
                ["Began", Time.at(page.cur.first_at)],
                ["Last seen", Time.at(page.cur.last_at) + " · " + Time.age(page.cur.last_at) + " ago"],
                ["Status", page.cur.status === "open" ? "Open" : page.cur.status.charAt(0).toUpperCase() + page.cur.status.slice(1) + (page.det && page.det.case.reviewed_by ? " by " + page.det.case.reviewed_by : "")]
            ] : []
            actions: [
                Btn { objectName: "detExplained"; visible: !!page.cur && page.cur.status === "open"; small: true; text: "It is explained"; onClicked: page.review("explained") },
                Btn { objectName: "detAccepted"; visible: !!page.cur && page.cur.status === "open"; small: true; text: "Accept it"; onClicked: page.review("accepted") },
                Btn { objectName: "detDismissed"; visible: !!page.cur && page.cur.status === "open"; small: true; text: "Dismiss"; onClicked: page.review("dismissed") },
                Btn { objectName: "detEscalate"; visible: !Nav.boss; small: true; kind: "primary"; text: "Send to the Super User"; onClicked: page.review("escalated") }
            ]
            foot: Field { objectName: "detNote"; visible: !!page.cur && page.cur.status === "open"; width: parent.width; placeholderText: "A note (optional): what you found out"; maximumLength: 500; text: page.note; onTextEdited: page.note = text }

            Txt { objectName: "caseHeadline"; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; text: page.cur ? page.cur.headline : "" }
            Txt { objectName: "modelSays"; visible: !!page.cur && page.cur.model_says !== null && page.cur.model_says !== undefined; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone
                  color: Theme.text3; font.pixelSize: 12
                  text: page.cur && page.cur.model_says !== null && page.cur.model_says !== undefined
                        ? (page.cur.model_says === "" ? "The local model reads it as nothing odd. That is its opinion, not the rules'." : "The local model reads it as: " + page.cur.model_says.toLowerCase() + ". That is its opinion, not the rules'.") : "" }
            Txt { visible: !!page.cur && page.cur.status !== "open" && !!page.cur.note; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text2
                  text: page.cur && page.cur.note ? "Their note: " + page.cur.note : "" }
            // dismissing for good: the same kind of finding with the same program, folder or drive is then weighed lower on this machine (still recorded, with the rule named; it can be taken back)
            Column {
                visible: !!page.cur && page.cur.status === "open" && Object.keys(page.ruleKinds).length > 0
                width: parent.width; spacing: 8
                Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                      text: "Or dismiss it and remember, so the same thing from the same place is weighed lower here next time. It is still recorded, and you can take it back." }
                Flow {
                    width: parent.width; spacing: 8
                    Btn { objectName: "detRememberProgram"; visible: !!page.ruleKinds.program; small: true; text: "Dismiss, trust " + (page.ruleKinds.program ? page.ruleKinds.program[0] : ""); onClicked: page.review("dismissed", "program") }
                    Btn { objectName: "detRememberFolder"; visible: !!page.ruleKinds.folder; small: true; text: "Dismiss, trust this folder"; onClicked: page.review("dismissed", "folder") }
                    Btn { objectName: "detRememberDrive"; visible: !!page.ruleKinds.drive; small: true; text: "Dismiss, trust this drive"; onClicked: page.review("dismissed", "drive") }
                }
            }
        }
    }

    // --- the evidence of the one picked, two panels a row, each row one height -------------------------------------------------------------
    Row {
        visible: !!page.cur
        width: parent.width
        spacing: 14
        Panel {
            id: pictureP
            width: (parent.width - 14) * 7 / 12
            height: Math.max(pictureP.implicitHeight, coverP.implicitHeight)
            title: "What happened"
            sub: "what was touched, and where it went"
            pad: 8
            CaseGraph { x: 0; y: 0; width: parent.width; graph: page.det ? page.det.graph : ({ nodes: [], edges: [] }) }
        }
        Panel {
            id: coverP
            objectName: "coverPanel"
            width: (parent.width - 14) * 5 / 12
            height: pictureP.height
            title: "What it covers"
            sub: "areas, in no order · none is required"
            pad: 16
            Column {
                width: parent.width; spacing: 14
                Txt { visible: !!page.cur && !!page.cur.not_yet; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.med; font.weight: Font.DemiBold
                      text: page.cur && page.cur.not_yet ? page.cur.not_yet + (page.cur.next_stage ? " Next, it usually goes on to: " + page.cur.next_stage.toLowerCase() + "." : "") : "" }
                Repeater {
                    model: page.det && page.det.board ? page.det.board : []
                    Column {
                        required property var modelData
                        objectName: "cover_" + modelData.behaviour
                        width: parent.width; spacing: 6
                        Txt { text: modelData.label + " · " + modelData.covered + " of " + modelData.of + " areas have something in them"; color: Theme.text2; font.pixelSize: 12; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                        Flow {
                            width: parent.width; spacing: 6
                            Repeater {
                                model: parent.parent.modelData.areas
                                Rectangle {
                                    required property var modelData
                                    objectName: "area_" + modelData.name
                                    readonly property color tone: page.cur && page.cur.level === "urgent" ? Theme.crit : Theme.med
                                    width: al.implicitWidth + 22; height: 28; radius: 14
                                    color: modelData.covered ? Theme.alpha(tone, 0.16) : "transparent"
                                    border.width: 1; border.color: modelData.covered ? tone : Theme.border
                                    Txt { id: al; anchors.centerIn: parent; elide: Text.ElideNone; font.pixelSize: 12; color: parent.modelData.covered ? Theme.text : Theme.text4
                                          text: parent.modelData.name + (parent.modelData.seen ? "" : " (no signal yet)") }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Row {
        visible: !!page.cur
        width: parent.width
        spacing: 14
        Panel {
            id: storyP
            width: (parent.width - 14) * 5 / 12
            height: Math.max(storyP.implicitHeight, noticedP.implicitHeight)
            title: "In order"
            sub: "what happened, as it happened"
            pad: 16
            Column {
                width: parent.width; spacing: 8
                Repeater {
                    model: page.cur ? page.cur.story : []
                    Row {
                        required property string modelData
                        spacing: 12
                        Txt { text: modelData.slice(0, modelData.indexOf("  ")); mono: true; color: Theme.text3; width: 78; font.pixelSize: 12; elide: Text.ElideNone }
                        Txt { text: modelData.slice(modelData.indexOf("  ") + 2); width: storyP.width - 32 - 90; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                    }
                }
            }
        }
        Panel {
            id: noticedP
            width: (parent.width - 14) * 7 / 12
            height: storyP.height
            title: "What Detective noticed"
            sub: "each thing on its own, and what would make it harmless"
            pad: 16
            Column {
                width: parent.width; spacing: 12
                Repeater {
                    model: page.det ? page.det.findings : []
                    Column {
                        required property var modelData
                        width: parent.width; spacing: 4
                        Row { spacing: 8
                              Tag { text: modelData.behaviour === "exfiltration" ? "Taking out" : modelData.behaviour.charAt(0).toUpperCase() + modelData.behaviour.slice(1) }
                              Txt { text: Math.round(modelData.weight * 100) + "% on its own"; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone } }
                        Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; text: modelData.summary; font.weight: Font.Medium }
                        Txt { visible: modelData.why && modelData.why.length > 0; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                              text: modelData.why ? "Because " + modelData.why.join("; ") + "." : "" }
                        Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12; text: "It would be harmless if: " + modelData.innocent + "." }
                        Rectangle { width: parent.width; height: 1; color: Theme.grid }
                    }
                }
            }
        }
    }

    // --- what Detective suggests to the other features, and what you have said is fine (always shown, side by side) ----------------------------
    Row {
        width: parent.width
        spacing: 14
        Panel {
            id: sugP
            objectName: "suggestions"
            width: (parent.width - 14) / 2
            height: Math.max(sugP.implicitHeight, rulesP.implicitHeight, 150)
            title: "Detective suggests"
            sub: "to Flows, Restricted and Tasks · nothing happens until you say so"
            pad: 14
            Column {
                width: parent.width; spacing: 10
                Empty { visible: page.proposals.length === 0; width: parent.width; icon: "check"; title: "Nothing to suggest"; text: "When a case needs a flow paused, a folder marked or a follow-up, it says so here."; h: 110 }
                Repeater {
                    model: page.proposals
                    Rectangle {
                        required property var modelData
                        objectName: "proposal_" + modelData.id
                        width: parent.width; height: pc.height + 24; radius: Theme.radius; color: Theme.accentSoft; border.width: 1; border.color: Theme.mix(Theme.accent, Theme.border, 0.3)
                        Column { id: pc; x: 12; y: 12; width: parent.width - 24; spacing: 8
                                 Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; text: modelData.title }
                                 Row { spacing: 8
                                       Btn { objectName: "proposalYes_" + modelData.id; small: true; kind: "primary"
                                             text: modelData.kind === "pause_flow" ? "Pause it" : modelData.kind === "mark_folder" ? "Show me where" : "Give me the words"; onClicked: page.decide(modelData, true) }
                                       Btn { objectName: "proposalNo_" + modelData.id; small: true; text: "Not now"; onClicked: page.decide(modelData, false) } } }
                    }
                }
            }
        }
        Panel {
            id: rulesP
            objectName: "writtenRules"
            width: (parent.width - 14) / 2
            height: sugP.height
            title: "Things you have said are fine"
            sub: "weighed lower there, still recorded · take one back any time"
            pad: 14
            Column {
                width: parent.width; spacing: 8
                Empty { visible: page.rules.length === 0; width: parent.width; icon: "filesearch"; title: "Nothing written down"; text: "Dismiss a case and choose to remember it, and the rule appears here."; h: 110 }
                Repeater {
                    model: page.rules
                    Rectangle {
                        required property var modelData
                        objectName: "rule_" + modelData.id
                        width: parent.width; height: 48; radius: Theme.radius; color: Theme.surface; border.width: 1; border.color: Theme.border
                        Column { x: 12; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 110; spacing: 1
                                 Txt { width: parent.width; text: modelData.graph.replace(/_/g, " ") + " · " + modelData.kind + " " + modelData.value }
                                 Txt { width: parent.width; color: Theme.text3; font.pixelSize: 12; text: "on " + (modelData.host || "a machine") } }
                        Btn { objectName: "ruleBack_" + modelData.id; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; small: true; text: "Take back"; onClicked: page.takeBack(modelData) }
                    }
                }
            }
        }
    }
}
