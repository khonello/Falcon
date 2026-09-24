import QtQuick
import QtQuick.Layouts
import "."

// Page 1, composed (board P02). The densities run diagonally: figures at the top, shapes down the
// left, a shape with its sentence, and the words at the bottom right. The page answers without
// anything being clicked.
//
// Its signature is a band over two columns -- pages 2 and 3 have their own, so you can tell which
// page you are on from the shape alone.
Item {
    id: page
    property var view: null

    // the sentences: generated in core/narrate.py from exactly the data these charts drew
    readonly property var rolloutSays: falcon.narrate("rollout", {
        version: page.view.version, pcs_behind: page.view.behind, pc_count: page.view.pcCount })
    readonly property var confirmsSays: falcon.narrate("confirmations", { points: page.view.confirmations })
    readonly property var fleetSays: falcon.narrate("fleet", {
        pc_count: page.view.pcCount, pcs_behind: page.view.behind })
    readonly property var needsSays: falcon.narrate("needs_you", {
        tree: page.view.tree, pcs_behind: page.view.behind,
        violations: page.view.violations, deviations: page.view.deviations })

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        // --- density 1: figures. A number and a word; no chart and no sentence.
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 104
            radius: Theme.radiusLg
            color: Theme.chartBg

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 24
                anchors.verticalCenter: parent.verticalCenter
                spacing: 64

                Hero {
                    value: String(page.view.pcCount)
                    label: "client PCs"
                    sub: page.view.tree.length + (page.view.tree.length === 1 ? " department" : " departments")
                }
                Hero {
                    value: String(page.view.confirmedCount)
                    label: page.view.version ? ("on " + page.view.version.version_string) : "on the current build"
                    sub: page.view.behindCount === 0 ? "all confirmed" : page.view.behindCount + " still behind"
                    tone: page.view.behindCount > 0 ? "warn" : "ok"
                }
                Hero {
                    value: String(page.view.waitingOnYou)
                    label: "waiting on you"
                    sub: page.needsSays.sentence
                    tone: page.view.waitingOnYou > 0 ? "danger" : "ok"
                }
                Hero {
                    value: String(page.view.traversalsToday)
                    label: "traversals today"
                    sub: page.view.openTraversals > 0 ? page.view.openTraversals + " still open" : "none still open"
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: page.width - Theme.laneWidth - 16
                Layout.fillHeight: true
                spacing: 16

                // --- density 2: a shape and its legend.
                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: page.view.version ? ("Rollout " + page.view.version.version_string) : "Rollout"
                    note: "by department, to the same scale"
                    notice: page.rolloutSays.state === "empty" ? page.rolloutSays.note : ""
                    noticeSub: page.rolloutSays.state === "empty" ? page.rolloutSays.sentence : ""

                    StackedBars {
                        width: parent.width
                        rows: page.view.rolloutRows.length > 0 ? page.view.rolloutRows : page.view.skeletonRows
                    }

                    foot: Legend {
                        items: [{ label: "Confirmed", color: Theme.ok, round: true },
                                { label: "Behind", color: Theme.warn, round: true },
                                { label: "Failing", color: Theme.danger, round: true }]
                    }
                }

                // --- density 3: the same kind of shape, and the one sentence it is making.
                Panel {
                    id: confPanel
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: "Confirmations"
                    note: "since the rollout was approved"
                    notice: page.confirmsSays.state !== "ok" ? page.confirmsSays.note : ""
                    noticeSub: page.confirmsSays.state !== "ok" ? page.confirmsSays.sentence : ""

                    Trend {
                        width: parent.width
                        height: Math.max(70, confPanel.height - 150)
                        points: page.view.confirmations.length > 1 ? page.view.confirmations
                                                                   : [0, 0, 0, 0, 0, 0, 0]
                    }
                    Sentence {
                        width: parent.width
                        text: page.confirmsSays.state === "ok" ? page.confirmsSays.sentence : ""
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: false
                Layout.preferredWidth: Theme.laneWidth
                Layout.fillHeight: true
                spacing: 16

                // --- density 2, short: the fleet.
                Panel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 196
                    title: "The fleet"
                    note: "one square per PC"
                    notice: page.fleetSays.state === "empty" ? page.fleetSays.note : ""
                    noticeSub: page.fleetSays.state === "empty" ? page.fleetSays.sentence : ""

                    Waffle {
                        width: parent.width
                        cells: page.view.fleetCells.length > 0 ? page.view.fleetCells : page.view.skeletonCells
                    }

                    foot: Legend {
                        items: [{ label: "Confirmed", color: Theme.ok, round: true },
                                { label: "Behind", color: Theme.warn, round: true },
                                { label: "Failing", color: Theme.danger, round: true }]
                    }
                }

                // --- density 4: the words. The end of the reading order, and the panel you would
                //     read first if you only had ten seconds.
                ReadingPanel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: "What needs you"
                    narration: page.needsSays
                    onActionTriggered: shell.notify(narration.action + " — not wired yet", false)
                }
            }
        }
    }
}
