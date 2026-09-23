import QtQuick
import QtQuick.Layouts
import "."

// The record of the day. Nothing here is a status a person set: sessions are never deleted, a
// violation is never quietly cleared and a deviation is logged rather than corrected, so what is
// drawn is simply what happened.
Item {
    id: page
    property var view: null

    RowLayout {
        anchors.fill: parent
        spacing: 16

        Panel {
            id: sessionsPanel
            Layout.preferredWidth: page.width * 0.5
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "Sessions today"
            note: "who held each PC, and for how long"

            DayTimeline {
                width: parent.width
                // the lanes share out whatever height the panel has, so the day fills its panel
                laneHeight: Math.max(18, Math.min(32, (sessionsPanel.height - 140)
                                                      / Math.max(1, lanes.length) - laneGap))
                lanes: page.view.timelineLanes
                fromHour: page.view.windowStart
                toHour: page.view.windowEnd
                visible: page.view.timelineLanes.length > 0
            }
            Txt {
                text: "No client PCs registered"
                color: Theme.faint
                visible: page.view.timelineLanes.length === 0
            }

            foot: Legend {
                items: [{ label: "At the PC", color: Theme.line2, round: false },
                        { label: "An Admin entered", color: Theme.warn, round: false },
                        { label: "You entered", color: Theme.danger, round: false },
                        { label: "Assisted", color: Theme.accent, round: false }]
                note: {
                    var quiet = 0
                    for (var i = 0; i < page.view.timelineLanes.length; i++)
                        if (page.view.timelineLanes[i].blocks.length === 0) quiet++
                    return quiet === 0 ? "" : quiet + (quiet === 1 ? " PC was never signed in"
                                                                   : " PCs were never signed in")
                }
            }
        }

        ColumnLayout {
            Layout.preferredWidth: page.width * 0.47
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            Panel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Violations by tier"
                note: "files found where their tier does not allow them"

                TierBars {
                    width: parent.width
                    rows: page.view.tierRows
                }

                foot: Txt {
                    width: parent.width
                    text: page.view.violations.length === 0
                          ? "Nothing is out of place right now."
                          : (page.view.violations[0].filename + ", found in " + page.view.violations[0].path
                             + " on " + page.view.violations[0].hostname + ".")
                    color: Theme.faint
                    font.pixelSize: Theme.fMeta
                    wrapMode: Text.WordWrap
                    elide: Text.ElideRight
                    maximumLineCount: 2
                }
            }

            Panel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Deviations"
                note: "logged, surfaced, never silently corrected"

                Column {
                    width: parent.width
                    spacing: 0

                    Repeater {
                        model: page.view.deviations.slice(0, 5)
                        delegate: Item {
                            required property var modelData
                            width: parent.width
                            height: 34

                            Txt {
                                id: at
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                width: 46
                                text: String(modelData.detected_at).substring(11, 16)
                                color: Theme.faint
                                monospace: true
                                font.pixelSize: Theme.fMeta
                            }
                            Txt {
                                anchors.left: at.right
                                anchors.leftMargin: 10
                                anchors.right: mark.left
                                anchors.rightMargin: 10
                                anchors.verticalCenter: parent.verticalCenter
                                text: {
                                    var w = String(modelData.expectation).replace(/_/g, " ")
                                    return w.charAt(0).toUpperCase() + w.slice(1)
                                }
                                font.pixelSize: Theme.fBody
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
                    Txt {
                        text: "Nothing has deviated from what the system expects."
                        color: Theme.faint
                        font.pixelSize: Theme.fBody
                        height: 34
                        visible: page.view.deviations.length === 0
                    }
                }
            }
        }
    }
}
