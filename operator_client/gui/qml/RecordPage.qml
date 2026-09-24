import QtQuick
import QtQuick.Layouts
import "."

// Page 3, composed (board P04). Its signature is a lead and a column: the day is one large shape,
// and the column beside it hands over 3 → 3 → 4. A third structure again, so the three pages are
// told apart by their shape before anything is read.
//
// Nothing here is a status a person set: sessions are never deleted, a violation is never quietly
// cleared and a deviation is logged rather than corrected. What is drawn is what happened.
Item {
    id: page
    objectName: "recordPage"
    property var view: null

    readonly property var readingOrder: [sessionsPanel, violationsPanel, deviationsPanel, dayPanel]
    readonly property var densities: readingOrder.map(function (p) { return p.density })

    readonly property var daySays: falcon.narrate("the_day", {
        sessions: page.view.sessions, pc_count: page.view.pcCount, quiet_pcs: page.view.quietPcs })
    readonly property var violationSays: falcon.narrate("violations", { violations: page.view.violations })
    readonly property var deviationSays: falcon.narrate("deviations", { deviations: page.view.deviations })

    RowLayout {
        anchors.fill: parent
        spacing: 16

        // --- density 2: the lead. The whole day as one shape.
        Panel {
            id: sessionsPanel
            density: 2
            Layout.fillWidth: true
            Layout.preferredWidth: page.width - Theme.laneWidth - 16
            Layout.fillHeight: true
            title: "Sessions today"
            note: "who held each PC, and for how long"
            notice: page.view.timelineLanes.length === 0 ? "Nothing recorded yet" : ""
            noticeSub: page.view.timelineLanes.length === 0 ? "no client PCs are registered" : ""

            DayTimeline {
                width: parent.width
                // the lanes share out whatever height the panel has, so the day fills its panel
                laneHeight: Math.max(18, Math.min(46, (sessionsPanel.height - 140)
                                                      / Math.max(1, lanes.length) - laneGap))
                lanes: page.view.timelineLanes.length > 0 ? page.view.timelineLanes : page.view.skeletonLanes
                fromHour: page.view.windowStart
                toHour: page.view.windowEnd
            }

            foot: Legend {
                items: [{ label: "At the PC", color: Theme.line2, round: false },
                        { label: "An Admin entered", color: Theme.warn, round: false },
                        { label: "You entered", color: Theme.danger, round: false },
                        { label: "Assisted", color: Theme.accent, round: false }]
                note: page.view.quietPcs === 0 ? ""
                      : page.view.quietPcs + (page.view.quietPcs === 1 ? " PC was never signed in"
                                                                       : " PCs were never signed in")
            }
        }

        ColumnLayout {
            Layout.fillWidth: false
            Layout.preferredWidth: Theme.laneWidth
            Layout.fillHeight: true
            spacing: 16

            // --- density 3: a shape with its sentence. A tier with nothing in it keeps its row
            //     and its zero -- that is a result, not an absence.
            Panel {
                id: violationsPanel
                density: 3
                Layout.fillWidth: true
                Layout.preferredHeight: 190
                title: "Violations by tier"

                TierBars {
                    width: parent.width
                    rows: page.view.tierRows
                }
                Sentence { width: parent.width; text: page.violationSays.sentence }
            }

            // --- density 3 again.
            Panel {
                id: deviationsPanel
                density: 3
                Layout.fillWidth: true
                Layout.preferredHeight: 172
                title: "Deviations"

                Column {
                    width: parent.width
                    spacing: 0

                    Repeater {
                        model: page.view.deviations.slice(0, 3)
                        delegate: Item {
                            required property var modelData
                            width: parent.width
                            height: 30

                            Txt {
                                id: at
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                width: 42
                                text: String(modelData.detected_at).substring(11, 16)
                                color: Theme.faint
                                monospace: true
                                font.pixelSize: Theme.fMeta
                            }
                            Txt {
                                anchors.left: at.right
                                anchors.leftMargin: 8
                                anchors.right: mark.left
                                anchors.rightMargin: 8
                                anchors.verticalCenter: parent.verticalCenter
                                text: {
                                    var w = String(modelData.expectation).replace(/_/g, " ")
                                    return w.charAt(0).toUpperCase() + w.slice(1)
                                }
                                font.pixelSize: Theme.fMeta
                            }
                            Chip {
                                id: mark
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.resolved_at ? "Addressed" : "Logged"
                                tone: modelData.resolved_at ? "ok" : "neutral"
                            }
                        }
                    }
                }
                Sentence { width: parent.width; text: page.deviationSays.sentence }
            }

            // --- density 4: the day in words. The panel a Super User would read first with ten
            //     seconds, so it sits at the end of the reading order.
            ReadingPanel {
                id: dayPanel
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Today, in words"
                maxFacts: 3
                narration: page.daySays
                onActionTriggered: shell.show("hierarchy")
            }
        }
    }
}
