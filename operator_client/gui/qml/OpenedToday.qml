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
                       open: !s.ended_at,
                       tone: s.occupant_role === "super_user" ? "danger"
                             : s.occupied_via === "assisted_access" ? "accent" : "warn" })
        }
        return out.sort(function (a, b) { return a.at < b.at ? 1 : -1 })
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
                objectName: "todayEntered"
                Layout.fillWidth: true
                Layout.fillHeight: false
                Layout.preferredHeight: Math.max(150, page.height * 0.27)
                title: "Who entered"
                topAlign: true
                narration: page.enteredSays

                EnteredRows {
                    width: parent.width
                    entries: page.entered
                }
            }

            // --- and which machines nobody touched at all
            GridCell {
                objectName: "todayQuiet"
                Layout.fillWidth: true
                Layout.fillHeight: false
                Layout.preferredHeight: Math.max(140, page.height * 0.24)
                title: "Never signed in"
                narration: page.quietSays

                QuietStrip {
                    width: parent.width
                    hosts: page.quietHosts
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
