import QtQuick
import "."

// DETECTIVE: what a person seems to be trying to do, read from several things happening together on a machine. A case is a pattern and its evidence, never an
// accusation: it says what it looks like, how far along it is (and what has not happened yet), shows the picture and the story in order, and says what would
// make it innocent. It is Detective's own conclusion; what you make of it is recorded (explained, accepted, dismissed).
// The page, top to bottom: the cases with the one picked beside them; its Evidence (the picture and the story in order, as two tabs); and what Detective
// noticed, each thing on its own with what would make it harmless, in rows across the width.
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
                Btn { objectName: "detDismissed"; visible: !!page.cur && page.cur.status === "open"; small: true; text: "Dismiss"; onClicked: page.review("dismissed") }
            ]
            foot: Field { objectName: "detNote"; visible: !!page.cur && page.cur.status === "open"; width: parent.width; placeholderText: "A note (optional): what you found out"; maximumLength: 500; text: page.note; onTextEdited: page.note = text }

            Txt { objectName: "caseHeadline"; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; text: page.cur ? page.cur.headline : "" }
            Txt { objectName: "modelSays"; visible: !!page.cur && page.cur.model_says !== null && page.cur.model_says !== undefined; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone
                  color: Theme.text3; font.pixelSize: 12
                  text: page.cur && page.cur.model_says !== null && page.cur.model_says !== undefined
                        ? (page.cur.model_says === "" ? "The local model reads it as nothing odd. That is its opinion, not the rules'." : "The local model reads it as: " + page.cur.model_says.toLowerCase() + ". That is its opinion, not the rules'.") : "" }
            Txt { visible: !!page.cur && page.cur.status !== "open" && !!page.cur.note; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text2
                  text: page.cur && page.cur.note ? "Their note: " + page.cur.note : "" }
            Txt { objectName: "coverLine"; visible: !!page.det && !!page.det.board && page.det.board.length > 0; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                  text: page.det && page.det.board ? page.det.board.map(function (b) { return b.label + ": " + b.covered + " of " + b.of + " areas" }).join(" · ") : "" }
        }
    }

    // --- the evidence of the one picked: the picture first, the story in order beside it as a tab --------------------------------------------------------
    Panel {
        objectName: "evidencePanel"
        visible: !!page.cur
        width: parent.width
        title: "Evidence"
        sub: "what Detective saw on this machine · the same case as above"
        pad: 0
        Column {
            width: parent.width
            Tabs {
                x: 16
                width: parent.width - 32
                tabs: [{ key: "picture", label: "Picture" }, { key: "order", label: "In order · " + (page.cur ? page.cur.story.length : 0) }]
                current: page.evTab
                onPicked: function (k) { page.evTab = k }
            }
            Item {
                visible: page.evTab === "picture"
                width: parent.width
                height: Math.min(460, graph.implicitHeight + 24)
                Flickable {
                    anchors.fill: parent
                    anchors.margins: 8
                    contentWidth: width
                    contentHeight: graph.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    CaseGraph { id: graph; x: 0; y: 0; width: parent.width; graph: page.det ? page.det.graph : ({ nodes: [], edges: [] }) }
                }
            }
            Item {
                visible: page.evTab === "order"
                width: parent.width
                height: Math.min(460, steps.implicitHeight + 32)
                Flickable {
                    anchors.fill: parent
                    anchors.margins: 16
                    contentWidth: width
                    contentHeight: steps.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    Column {
                        id: steps
                        width: parent.width; spacing: 8
                        Repeater {
                            model: page.cur ? page.cur.story : []
                            Row {
                                required property string modelData
                                spacing: 12
                                Txt { text: modelData.slice(0, modelData.indexOf("  ")); mono: true; color: Theme.text3; width: 78; font.pixelSize: 12; elide: Text.ElideNone }
                                Txt { text: modelData.slice(modelData.indexOf("  ") + 2); width: steps.width - 90; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                            }
                        }
                    }
                }
            }
        }
    }

    // what Detective noticed: one row a finding, in four columns across the width (the kind, what it saw, why it counts, what would make it harmless)
    Panel {
        objectName: "noticedPanel"
        visible: !!page.cur
        width: parent.width
        title: "What Detective noticed"
        sub: page.det && page.det.findings && page.det.findings.length > 4 ? "each thing on its own, and what would make it harmless · " + Theme.fmt(page.det.findings.length) + ", scroll to see them all"
                                                                           : "each thing on its own, and what would make it harmless"
        pad: 16
        Item {
            id: nt
            width: parent.width
            height: Math.min(460, nrows.implicitHeight + head.height)
            readonly property real kindW: 150
            readonly property real colW: (width - kindW - 3 * 20) / 3.3
            Row {
                id: head
                width: parent.width; spacing: 20; height: 26
                Head { width: nt.kindW; text: "Kind" }
                Head { width: nt.colW * 1.3; text: "What Detective saw" }
                Head { width: nt.colW; text: "Why it counts" }
                Head { width: nt.colW; text: "It would be harmless if" }
            }
            Rectangle { y: head.height - 1; width: parent.width; height: 1; color: Theme.border }
            Flickable {
                y: head.height
                width: parent.width; height: parent.height - head.height
                contentWidth: width; contentHeight: nrows.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                Column {
                    id: nrows
                    width: parent.width
                    Repeater {
                        model: page.det ? page.det.findings : []
                        Item {
                            required property var modelData
                            width: nrows.width
                            height: Math.max(52, Math.max(sm.implicitHeight, why.implicitHeight, ok.implicitHeight) + 20)
                            Column {
                                x: 0; y: 10; width: nt.kindW; spacing: 4
                                Tag { text: modelData.behaviour === "exfiltration" ? "Taking out" : modelData.behaviour.charAt(0).toUpperCase() + modelData.behaviour.slice(1) }
                                Txt { text: Math.round(modelData.weight * 100) + "% on its own"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                            }
                            Txt { id: sm; x: nt.kindW + 20; y: 10; width: nt.colW * 1.3; wrapMode: Text.WordWrap; elide: Text.ElideNone; text: modelData.summary; font.weight: Font.Medium }
                            Txt { id: why; x: nt.kindW + 40 + nt.colW * 1.3; y: 10; width: nt.colW; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                                  text: modelData.why && modelData.why.length ? modelData.why.join("; ") + "." : "—" }
                            Txt { id: ok; x: nt.kindW + 60 + nt.colW * 2.3; y: 10; width: nt.colW; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12; text: modelData.innocent + "." }
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                        }
                    }
                }
            }
        }
    }
}
