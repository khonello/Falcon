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
    readonly property var stages: ["Reaching", "Gathering", "Hiding", "Taking out", "Covering up"]
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
            Msg.ok(outcome === "escalated" ? "Sent to the Super User" : "Recorded: " + outcome)
            page.note = ""
            page.load()
        })
    }
    Component.onCompleted: load()
    Connections { target: falcon; function onConnected() { page.load() } function onPushReceived(type, payload) { if (/^detective/.test(type)) again.restart() } }
    Timer { id: again; interval: 400; onTriggered: { page.load(); page.loadCase() } }

    component Head: Txt { color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66; elide: Text.ElideNone }
    component Tile: Rectangle {
        property string label: ""
        property int n: 0
        property color tone: Theme.text
        width: (parent.width - 3 * 12) / 4; height: 64; radius: Theme.radius; color: Theme.surface; border.width: 1; border.color: Theme.border
        Column { x: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 2
                 Txt { text: String(parent.parent.n); color: parent.parent.n > 0 ? parent.parent.tone : Theme.text3; font.pixelSize: 22; font.weight: Font.DemiBold; elide: Text.ElideNone }
                 Txt { text: parent.parent.label; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
    }

    Row {
        width: parent.width; spacing: 12
        Tile { objectName: "tileUrgent"; label: "Urgent"; n: page.ov.by_level.urgent; tone: Theme.crit }
        Tile { objectName: "tileCases"; label: "Cases"; n: page.ov.by_level["case"]; tone: Theme.med }
        Tile { label: "Noted quietly"; n: page.ov.by_level.noted }
        Tile { label: "Reviewed"; n: page.ov.reviewed }
    }

    Row {
        width: parent.width; spacing: 14

        // --- the cases -------------------------------------------------------------------------------------------------------------------------
        Panel {
            id: listPanel
            width: Math.max(300, (parent.width - 14) * 0.34)
            title: "Cases"
            sub: Nav.boss ? "every machine, strongest first" : "your department's machines, strongest first"
            pad: 0
            flush: true
            extra: Segmented { objectName: "detShow"; options: [{ value: "open", label: "Open" }, { value: "noted", label: "+ Noted" }, { value: "reviewed", label: "Reviewed" }]; value: page.show; onPicked: function (v) { page.show = v } }
            Column {
                width: parent.width
                Empty { visible: page.cases.length === 0; width: parent.width; icon: "filesearch"; title: page.show === "reviewed" ? "Nothing reviewed yet" : "Nothing to look at"
                        text: "Detective watches by itself. When several small things add up to a pattern, it appears here."; h: 150 }
                Repeater {
                    model: page.cases
                    delegate: Rectangle {
                        required property var modelData
                        readonly property bool on: page.cur && page.cur.id === modelData.id
                        objectName: "case_" + modelData.id
                        width: parent.width; height: 72
                        color: on ? Theme.accentSoft : rowArea.containsMouse ? Theme.surface2 : "transparent"
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
                        Column {
                            x: 16; y: 10; width: parent.width - 32; spacing: 3
                            Row { spacing: 8
                                  Txt { text: modelData.intent; font.weight: Font.DemiBold; width: Math.min(implicitWidth, parent.parent.width - 90); elide: Text.ElideRight }
                                  Tag { text: modelData.level === "urgent" ? "Urgent" : modelData.level === "case" ? "Case" : "Noted"; tone: page.levelTone[modelData.level] } }
                            Txt { text: modelData.host + " · " + Time.at(modelData.last_at); color: Theme.text3; font.pixelSize: 12; width: parent.width }
                            Row { spacing: 4
                                  Repeater { model: 5
                                             Rectangle { required property int index; width: 22; height: 5; radius: 2
                                                         color: index < modelData.stage_count ? (modelData.level === "urgent" ? Theme.crit : Theme.med) : Theme.border } } }
                        }
                        MouseArea { id: rowArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.sel = modelData.id }
                    }
                }
            }
        }

        // --- one case ------------------------------------------------------------------------------------------------------------------------------
        Panel {
            id: casePanel
            objectName: "casePanel"
            width: parent.width - listPanel.width - 14
            title: page.cur ? page.cur.intent : "Case"
            sub: page.cur ? page.cur.host + " · " + Time.date(page.cur.first_at) : ""
            pad: 20
            Column {
                width: parent.width; spacing: 22
                Empty { visible: !page.cur; width: parent.width; icon: "filesearch"; title: "Pick a case"; text: "It shows what it looks like and the evidence behind it."; h: 150 }

                Column {
                    visible: !!page.cur; width: parent.width; spacing: 6
                    Txt { objectName: "caseHeadline"; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; font.pixelSize: 15; text: page.cur ? page.cur.headline : "" }
                    Txt { objectName: "modelSays"; visible: !!page.cur && page.cur.model_says !== null && page.cur.model_says !== undefined; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone
                          color: Theme.text3; font.pixelSize: 12
                          text: page.cur && page.cur.model_says !== null && page.cur.model_says !== undefined
                                ? (page.cur.model_says === "" ? "The local model reads it as nothing odd. That is its opinion, not the rules'." : "The local model reads it as: " + page.cur.model_says.toLowerCase() + ". That is its opinion, not the rules'.") : "" }
                    Txt { visible: !!(page.cur && page.cur.not_yet); width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.med; font.weight: Font.DemiBold
                          text: page.cur && page.cur.not_yet ? page.cur.not_yet + (page.cur.next_stage ? " Next, it usually goes on to: " + page.cur.next_stage.toLowerCase() + "." : "") : "" }
                }

                // how far along it is
                Column {
                    visible: !!page.cur; width: parent.width; spacing: 8
                    Head { text: "HOW FAR ALONG" }
                    Row {
                        spacing: 6
                        Repeater {
                            model: page.stages
                            Rectangle {
                                required property string modelData
                                readonly property bool seen: page.cur && page.cur.behaviours && ((modelData === "Reaching" && page.cur.behaviours.indexOf("reach") >= 0)
                                    || (modelData === "Gathering" && page.cur.behaviours.indexOf("collection") >= 0) || (modelData === "Hiding" && page.cur.behaviours.indexOf("concealment") >= 0)
                                    || (modelData === "Taking out" && (page.cur.behaviours.indexOf("exfiltration") >= 0 || page.cur.behaviours.indexOf("capture") >= 0))
                                    || (modelData === "Covering up" && page.cur.behaviours.indexOf("erasure") >= 0))
                                width: pl.implicitWidth + 22; height: 28; radius: 14
                                color: seen ? Theme.alpha(page.cur && page.cur.level === "urgent" ? Theme.crit : Theme.med, 0.16) : "transparent"
                                border.width: 1; border.color: seen ? (page.cur && page.cur.level === "urgent" ? Theme.crit : Theme.med) : Theme.border
                                Txt { id: pl; anchors.centerIn: parent; text: modelData; color: parent.seen ? Theme.text : Theme.text4; font.pixelSize: 12; elide: Text.ElideNone }
                            }
                        }
                    }
                }

                // the picture
                Column {
                    visible: !!page.cur && !!page.det; width: parent.width; spacing: 8
                    Head { text: "WHAT HAPPENED" }
                    Rectangle {
                        width: parent.width; height: graph.height + 16; radius: Theme.radius; color: Theme.surface2; border.width: 1; border.color: Theme.border
                        CaseGraph { id: graph; x: 4; y: 8; width: parent.width - 8; graph: page.det ? page.det.graph : ({ nodes: [], edges: [] }) }
                    }
                }

                // the story, in order
                Column {
                    visible: !!page.cur; width: parent.width; spacing: 6
                    Head { text: "IN ORDER" }
                    Repeater {
                        model: page.cur ? page.cur.story : []
                        Row {
                            required property string modelData
                            spacing: 12
                            Txt { text: modelData.slice(0, modelData.indexOf("  ")); mono: true; color: Theme.text3; width: 78; font.pixelSize: 12; elide: Text.ElideNone }
                            Txt { text: modelData.slice(modelData.indexOf("  ") + 2); width: casePanel.width - 40 - 90; font.pixelSize: 13; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                        }
                    }
                }

                // each finding: why, and what would make it innocent
                Column {
                    visible: !!page.cur && !!page.det; width: parent.width; spacing: 10
                    Head { text: "WHAT DETECTIVE NOTICED" }
                    Repeater {
                        model: page.det ? page.det.findings : []
                        Rectangle {
                            required property var modelData
                            width: parent.width; height: fc.height + 24; radius: Theme.radius; color: Theme.surface; border.width: 1; border.color: Theme.border
                            Column { id: fc; x: 14; y: 12; width: parent.width - 28; spacing: 4
                                     Row { spacing: 8
                                           Tag { text: modelData.behaviour === "exfiltration" ? "Taking out" : modelData.behaviour.charAt(0).toUpperCase() + modelData.behaviour.slice(1) }
                                           Txt { text: Math.round(modelData.weight * 100) + "% on its own"; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone } }
                                     Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; text: modelData.summary; font.weight: Font.Medium }
                                     Txt { visible: modelData.why && modelData.why.length > 0; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                                           text: modelData.why ? "Because " + modelData.why.join("; ") + "." : "" }
                                     Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12; text: "It would be harmless if: " + modelData.innocent + "." } }
                        }
                    }
                }

                // what you make of it
                Column {
                    visible: !!page.cur; width: parent.width; spacing: 8
                    Head { text: page.cur && page.cur.status !== "open" ? "REVIEWED" : "WHAT DO YOU MAKE OF IT?" }
                    Txt { visible: !!page.cur && page.cur.status !== "open"; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text2
                          text: page.cur ? "Marked " + page.cur.status + (page.det && page.det.case.reviewed_by ? " by " + page.det.case.reviewed_by : "") + (page.cur.note ? ": " + page.cur.note : ".") : "" }
                    Field { visible: !!page.cur && page.cur.status === "open"; objectName: "detNote"; width: parent.width; placeholderText: "A note (optional): what you found out"; maximumLength: 500; text: page.note; onTextEdited: page.note = text }
                    Row {
                        visible: !!page.cur && page.cur.status === "open"; spacing: 8
                        Btn { objectName: "detExplained"; text: "It is explained"; onClicked: page.review("explained") }
                        Btn { objectName: "detAccepted"; text: "Accept it"; onClicked: page.review("accepted") }
                        Btn { objectName: "detDismissed"; text: "Dismiss"; onClicked: page.review("dismissed") }
                        Btn { objectName: "detEscalate"; visible: !Nav.boss; kind: "primary"; text: "Send to the Super User"; onClicked: page.review("escalated") }
                    }
                }
            }
        }
    }
}
