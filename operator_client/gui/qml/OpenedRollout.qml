import QtQuick
import QtQuick.Layouts
import "."

// Rollout, opened (board K04). It deliberately does NOT take Authority's shape. Authority's subject
// is a structure, so its hero is a map with the words down the side; Rollout's subject is a FLEET,
// which is wide, so the hero runs the full width and the three panels that explain it sit in a row
// beneath — shape, shape, then words, left to right.
//
// The hard gate is the reason the page exists: the Engine refuses to approve N+1 while any PC is
// still not confirmed on N, so what a Super User needs is which machines the gate is resting on.
Item {
    id: page
    objectName: "openedRollout"
    property var view: null

    readonly property var fleetSays: falcon.narrate("fleet", {
        pc_count: page.view.pcCount, pcs_behind: page.view.behind })
    readonly property var deptSays: falcon.narrate("rollout_departments", {
        departments: page.view.rollout.departments || [] })
    readonly property var trendSays: falcon.narrate("confirmations", { points: page.view.confirmations })
    readonly property var blockingSays: falcon.narrate("blocking", {
        version: page.view.version, pcs_behind: page.view.behind, pc_count: page.view.pcCount })

    ColumnLayout {
        anchors.fill: parent
        spacing: 20

        // --- the hero: every client PC, one square each, big enough to pick one out by name
        GridCell {
            objectName: "rolloutHero"
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: Math.max(210, page.height * 0.36)
            title: "The fleet"
            narration: page.fleetSays

            FleetGroups {
                width: parent.width
                maxSize: 76
                groups: page.view.fleetGroups.length > 0 ? page.view.fleetGroups
                                                         : page.view.skeletonGroups
            }
            Legend {
                items: [{ label: "Confirmed", color: Theme.ok, round: true },
                        { label: "Behind", color: Theme.warn, round: true },
                        { label: "Failing", color: Theme.danger, round: true }]
            }
        }

        RowLayout {
            // a nested layout fills by default, which would starve the hero above it
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            // --- told: the same rollout by department, so the one holding it up is named
            GridCell {
                objectName: "rolloutByDept"
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "By department"
                narration: page.deptSays

                StackedBars {
                    width: parent.width
                    barHeight: 22
                    rowGap: 38
                    rows: page.view.rolloutRows.length > 0 ? page.view.rolloutRows : page.view.skeletonRows
                }
                Sentence {
                    width: parent.width
                    text: page.deptSays.sentence
                }
            }

            // --- told: what has actually landed since Monday, accumulated
            GridCell {
                objectName: "rolloutTrend"
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Since Monday"
                narration: page.trendSays

                Trend {
                    width: parent.width
                    height: Math.max(110, page.height * 0.22)
                    points: page.view.confirmations
                    tint: Theme.ok
                }
                Sentence {
                    width: parent.width
                    text: page.trendSays.sentence
                }
            }

            // --- the words: which machines the N+1 gate is resting on, and the one lever
            GridCell {
                objectName: "rolloutBlocking"
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "What is blocking"
                topAlign: true
                narration: page.blockingSays

                ReadingBody {
                    width: parent.width
                    narration: page.blockingSays
                    maxFacts: 4
                    onActionTriggered: shell.notify(narration.action + " — not wired yet", false)
                }
            }
        }
    }
}
