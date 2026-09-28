import QtQuick
import QtQuick.Layouts
import "."

// Today, opened (board K05). A third subject, so a third shape: a record is read DOWN -- one lane
// per machine -- so the lead runs the whole height on the left, and a column of three explains it
// down the right. Neither Authority's map-and-column nor Rollout's band-and-row.
//
// The lead shows every PC, where the cell had to collapse the quiet ones into "N more": an empty
// lane is the answer to a question the cell had no room to ask.
Item {
    id: page
    objectName: "openedToday"
    property var view: null

    readonly property var everyLane: {
        var out = []
        for (var i = 0; i < page.view.tree.length; i++)
            for (var j = 0; j < page.view.tree[i].workers.length; j++) {
                var w = page.view.tree[i].workers[j]
                out.push({ name: w.name || w.hostname, hostname: w.hostname || w.name,
                           blocks: page.view.blocksFor(w.pc_id) })
            }
        return out
    }
    readonly property var quietHosts: everyLane.map(function (l) {
        return { hostname: l.hostname, quiet: l.blocks.length === 0 }
    })
    // every session on a machine that is not the occupant's own, newest first
    readonly property var entered: {
        var out = []
        for (var i = 0; i < page.view.sessions.length; i++) {
            var s = page.view.sessions[i]
            if (s.occupied_via === "native") continue
            out.push({ who: s.occupant_name || "someone", hostname: s.hostname || "a PC",
                       at: String(s.entered_at).substring(11, 16),
                       until: s.ended_at ? String(s.ended_at).substring(11, 16) : "",
                       open: !s.ended_at, session_id: s.session_id, pc_id: s.pc_id,
                       assisted: s.occupied_via === "assisted_access",
                       tone: s.occupant_role === "super_user" ? "danger"
                             : s.occupied_via === "assisted_access" ? "accent" : "warn" })
        }
        return out.sort(function (a, b) { return a.at < b.at ? 1 : -1 })
    }

    // the machines nobody signed in to, as the one mark -- unused is not a problem, so they stay quiet
    readonly property var quietMarks: page.quietHosts.filter(function (h) { return h.quiet })
        .map(function (h) { return { host: h.hostname, label: String(h.hostname).split("-").pop() } })

    // the one act a card about an open session carries, and it states its cost first (DG01)
    function endSession(e) {
        shell.ask({ title: "End " + e.who + "'s session on " + e.hostname + "?",
                    lead: "They are in there now. Ending it puts the machine back to whoever owns it.",
                    body: "They are not warned first; the trail records that you ended it.",
                    act: "End it", actIcon: "stop", cancel: "Leave it" }, function () {
            falcon.call("hierarchy.end_session", { session_id: e.session_id }, function (ok, r) {
                shell.notify(ok ? e.hostname + " is theirs again" : r.message, !ok)
                if (ok && page.view) page.view.refresh()
            })
        })
    }

    readonly property var daySays: falcon.narrate("the_day", {
        sessions: page.view.sessions, pc_count: page.view.pcCount, quiet_pcs: page.view.quietPcs })
    readonly property var enteredSays: falcon.narrate("entries", { sessions: page.view.sessions })
    readonly property var quietSays: falcon.narrate("never_signed_in", {
        quiet: page.quietHosts.filter(function (h) { return h.quiet })
                              .map(function (h) { return h.hostname }),
        pc_count: page.view.pcCount })

    RowLayout {
        anchors.fill: parent
        spacing: 20

        // --- the lead: the whole day, every machine, for the whole height
        GridCell {
            objectName: "todayLead"
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "The day"
            narration: page.daySays

            DayTimeline {
                width: parent.width
                labelWidth: 112
                laneGap: 10
                // the lanes share out the height they are given, and never grow past comfortable
                laneHeight: Math.max(12, Math.min(34, (page.height - 150)
                                                      / Math.max(1, lanes.length) - laneGap))
                lanes: page.everyLane.length > 0 ? page.everyLane : page.view.skeletonLanes
                fromHour: page.view.windowStart
                toHour: page.view.windowEnd
            }
            Legend {
                items: [{ label: "At the PC", color: Theme.line2, round: false },
                        { label: "An Admin entered", color: Theme.warn, round: false },
                        { label: "You entered", color: Theme.danger, round: false },
                        { label: "Assisted", color: Theme.accent, round: false }]
            }
        }

        ColumnLayout {
            Layout.fillWidth: false
            Layout.preferredWidth: 440
            Layout.fillHeight: true
            spacing: 20

            // --- who was on a machine that is not theirs
            GridCell {
                id: enteredCell
                objectName: "todayEntered"
                Layout.fillWidth: true
                Layout.fillHeight: false
                Layout.preferredHeight: Math.max(150, page.height * 0.27)
                title: "Who entered"
                topAlign: true
                narration: page.enteredSays

                PagedColumn {
                    objectName: "todayEnteredCards"
                    width: parent.width
                    // a GridCell's body is a Column: `parent.height` would collapse to nothing
                    height: enteredCell.room
                    itemHeight: 58
                    spacing: 9
                    model: page.entered
                    attention: function (e) { return e.open ? e.hostname : "" }
                    delegate: InfoCard {
                        property var modelData: null
                        readonly property var e: modelData || ({})
                        width: parent ? parent.width : 0
                        iconName: e.assisted ? "assistance" : "user"
                        iconTone: e.tone || "warn"
                        title: (e.who || "") + " entered " + (e.hostname || "")
                        line: e.open ? e.at + " · still in there"
                              : e.at + " – " + e.until + " · left"
                        lineTone: e.open ? (e.tone || "warn") : ""
                        stateWord: e.open ? "End it" : ""
                        stateTone: e.tone || "warn"
                        onClicked: if (e.open) page.endSession(e)
                    }
                }
            }

            // --- and which machines nobody touched at all
            GridCell {
                objectName: "todayQuiet"
                Layout.fillWidth: true
                Layout.fillHeight: false
                Layout.preferredHeight: Math.max(166, page.height * 0.26)
                title: "Never signed in"
                narration: page.quietSays

                // free is not a problem: the marks stay quiet, and the reason is the cell's title --
                // repeating "never signed in" under every one of them says nothing and collides
                PagedRow {
                    objectName: "todayQuietRow"
                    width: parent.width
                    height: 72
                    itemWidth: 58
                    spacing: 10
                    model: page.quietMarks
                    delegate: MachineMark {
                        property var modelData: ({})
                        size: 42
                        label: modelData.label || ""
                        status: "free"
                        name: modelData.host || ""
                    }
                }
                Sentence {
                    width: parent.width
                    text: page.quietSays.sentence
                }
            }

            // --- the words: what the record adds up to, and the one way into it
            GridCell {
                objectName: "todayReading"
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "What the day means"
                topAlign: true
                narration: page.daySays

                ReadingBody {
                    width: parent.width
                    narration: page.daySays
                    maxFacts: 3
                    onActionTriggered: shell.notify(narration.action + " — not wired yet", false)
                }
            }
        }
    }
}
