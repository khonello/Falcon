import QtQuick
import QtQuick.Layouts
import "."

// The system at a glance: four figures, the rollout it is all held on, and the work underneath.
// The four figures are the only place a number stands on its own; everything else is drawn.
Item {
    id: page
    property var view: null

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 108
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
                    sub: page.view.behindCount === 0 ? "all confirmed"
                                                     : page.view.behindCount + " still behind"
                    tone: page.view.behindCount > 0 ? "warn" : "ok"
                }
                Hero {
                    value: String(page.view.waitingOnYou)
                    label: "waiting on you"
                    sub: {
                        var bits = []
                        if (page.view.emptyDepartments > 0)
                            bits.push(page.view.emptyDepartments === 1 ? "an empty department"
                                                                      : page.view.emptyDepartments + " empty departments")
                        if (page.view.violations.length > 0)
                            bits.push(page.view.violations.length
                                      + (page.view.violations.length === 1 ? " violation" : " violations"))
                        if (page.view.deviations.length > 0)
                            bits.push(page.view.deviations.length
                                      + (page.view.deviations.length === 1 ? " deviation" : " deviations"))
                        return bits.length ? bits.join(", ") : "nothing outstanding"
                    }
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

            Panel {
                Layout.preferredWidth: page.width * 0.52
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: page.view.version ? ("Rollout " + page.view.version.version_string) : "Rollout"
                note: "by department, to the same scale"

                StackedBars {
                    width: parent.width
                    rows: page.view.rolloutRows
                    visible: page.view.rolloutRows.length > 0
                }
                Txt {
                    text: "No version has been approved yet"
                    color: Theme.faint
                    visible: page.view.rolloutRows.length === 0
                }

                foot: Legend {
                    items: [{ label: "Confirmed", color: Theme.ok, round: true },
                            { label: "Behind", color: Theme.warn, round: true },
                            { label: "Failing", color: Theme.danger, round: true }]
                    note: page.view.behindCount > 0
                          ? "the next version stays blocked until all " + page.view.pcCount + " confirm"
                          : "every PC has confirmed"
                }
            }

            Panel {
                Layout.preferredWidth: page.width * 0.45
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "The fleet"
                note: "one square per PC"

                Waffle {
                    width: parent.width
                    cells: page.view.fleetCells
                }
                Txt {
                    text: "No client PCs registered"
                    color: Theme.faint
                    visible: page.view.fleetCells.length === 0
                }

                foot: Legend {
                    items: [{ label: "Confirmed", color: Theme.ok, round: true },
                            { label: "Behind", color: Theme.warn, round: true },
                            { label: "Failing", color: Theme.danger, round: true }]
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            Panel {
                id: confPanel
                Layout.preferredWidth: page.width * 0.52
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Confirmations"
                note: "PCs confirmed on the current version, this week"

                Trend {
                    width: parent.width
                    height: Math.max(80, confPanel.height - 122)
                    points: page.view.confirmations
                    visible: page.view.confirmations.length > 0
                }
                Row {
                    width: parent.width
                    visible: page.view.confirmations.length > 0
                    Repeater {
                        model: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                        delegate: Txt {
                            required property int index
                            width: parent.width / 7
                            text: {
                                var t = new Date()
                                t.setDate(t.getDate() - (6 - index))
                                return index === 6 ? "Today" : ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][t.getDay()]
                            }
                            color: Theme.faint
                            font.pixelSize: Theme.fMeta
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }
                Txt {
                    text: "No update attempts recorded this week"
                    color: Theme.faint
                    visible: page.view.confirmations.length === 0
                }
            }

            Panel {
                Layout.preferredWidth: page.width * 0.45
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Work, by department"
                note: "the same two bars, once each"

                Row {
                    width: parent.width
                    spacing: 14

                    Repeater {
                        model: page.view.tree
                        delegate: HealthCard {
                            required property var modelData
                            required property int index
                            width: (parent.width - (page.view.tree.length - 1) * 14) / Math.max(1, page.view.tree.length)
                            name: modelData.name
                            tint: Theme.series(index)
                            tasks: page.view.taskParts(modelData.department_id)
                            flows: page.view.flowParts(modelData.department_id)
                        }
                    }
                }

                foot: Legend {
                    items: [{ label: "On track", color: Theme.ok, round: true },
                            { label: "Needs attention", color: Theme.warn, round: true },
                            { label: "Overdue", color: Theme.danger, round: true }]
                }
            }
        }
    }
}
