import QtQuick
import QtQuick.Layouts
import "."

// The hierarchy, seen -- and then descended into. Picking a department on the map does not open a
// different screen: the map stays, everything else quietens, and the right-hand column swaps from
// the system's relationships to that department's own numbers.
Item {
    id: page
    property var view: null
    readonly property bool descended: page.view.focusDept !== 0

    RowLayout {
        anchors.fill: parent
        spacing: 16

        ColumnLayout {
            Layout.preferredWidth: page.width * 0.5
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            Panel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "The hierarchy"
                note: page.descended ? (page.view.focused ? page.view.focused.name + ", in place" : "")
                                     : "every department, Admin and PC you govern"

                OrgMap {
                    width: parent.width
                    height: Math.max(180, page.height - (page.descended ? 300 : 120))
                    departments: page.view.tree
                    focusId: page.view.focusDept
                    onPicked: function (id) { page.view.focusDept = (id === page.view.focusDept ? 0 : id) }
                }

                foot: Legend {
                    items: page.view.tree.map(function (d, i) {
                        return { label: d.name, color: Theme.series(i), round: true }
                    })
                    note: page.descended ? "pick Everything to back out" : "pick a department to descend into it"
                }
            }

            Panel {
                Layout.fillWidth: true
                Layout.preferredHeight: implicitHeight
                visible: page.descended
                title: "Its Admins"
                note: "who governs here"

                Column {
                    width: parent.width
                    spacing: 0

                    Repeater {
                        model: page.descended && page.view.focused ? page.view.focused.admins : []
                        delegate: Item {
                            required property var modelData
                            width: parent.width
                            height: 46

                            Row {
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 11

                                Avatar {
                                    initials: page.view.initials(modelData.name)
                                    size: 30
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Column {
                                    spacing: 1
                                    anchors.verticalCenter: parent.verticalCenter
                                    Txt { text: modelData.name || "unnamed"; font.pixelSize: Theme.fBody }
                                    Txt {
                                        text: modelData.hostname || ""
                                        color: Theme.faint
                                        monospace: true
                                        font.pixelSize: Theme.fMeta
                                    }
                                }
                            }
                            Chip {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                text: Theme.sessionWord(Theme.stateOf(modelData.session))
                                tone: Theme.stateOf(modelData.session) === "free" ? "neutral" : "accent"
                            }
                        }
                    }
                    Txt {
                        text: "No Admin governs this department"
                        color: Theme.danger
                        font.pixelSize: Theme.fBody
                        height: 40
                        visible: page.descended && page.view.focused && page.view.focused.admins.length === 0
                    }
                }
            }
        }

        // --- the system's relationships, or the department's own numbers -----------------------
        ColumnLayout {
            Layout.preferredWidth: page.width * 0.47
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16
            visible: !page.descended

            Panel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Assistance between departments"
                note: "peer help, by consent"

                Arcs {
                    width: parent.width
                    height: Math.max(120, page.height * 0.32)
                    nodes: page.view.assistNodes
                    links: page.view.assistLinks
                }

                foot: Txt {
                    text: "You see every session and gate none of them."
                    color: Theme.faint
                    font.pixelSize: Theme.fMeta
                }
            }

            Panel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Report routing"
                note: "additive: routing never takes your copy away"

                RoutingMap {
                    width: parent.width
                    height: Math.max(150, page.height * 0.36)
                    categories: page.view.routingRows
                    destinations: page.view.routingDests
                    visible: page.view.routingRows.length > 0
                }
                Txt {
                    text: "No report categories configured"
                    color: Theme.faint
                    visible: page.view.routingRows.length === 0
                }
            }
        }

        ColumnLayout {
            Layout.preferredWidth: page.width * 0.47
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16
            visible: page.descended

            Panel {
                id: herePanel
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Sessions today, here"
                note: "who held each PC, and for how long"

                DayTimeline {
                    width: parent.width
                    laneHeight: Math.max(18, Math.min(32, (herePanel.height - 140)
                                                          / Math.max(1, lanes.length) - laneGap))
                    lanes: page.view.timelineLanes
                    fromHour: page.view.windowStart
                    toHour: page.view.windowEnd
                    visible: page.view.timelineLanes.length > 0
                }
                Txt {
                    text: "No client PCs in this department"
                    color: Theme.faint
                    visible: page.view.timelineLanes.length === 0
                }

                foot: Legend {
                    items: [{ label: "At the PC", color: Theme.line2, round: false },
                            { label: "An Admin entered", color: Theme.warn, round: false },
                            { label: "You entered", color: Theme.danger, round: false }]
                }
            }

            Panel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: page.view.focused ? (page.view.focused.name + ", in numbers") : ""
                note: "its rollout, and its work"

                StackedBars {
                    width: parent.width
                    labelWidth: 72
                    rows: page.view.focused
                          ? [{ label: "Rollout", parts: page.view.rolloutParts(page.view.focusDept) }]
                          : []
                }

                Row {
                    width: parent.width
                    spacing: 20

                    HealthCard {
                        width: (parent.width - 20) * 0.56
                        name: "Tasks and flows"
                        tint: Theme.series(page.view.deptIndex(page.view.focusDept))
                        tasks: page.view.taskParts(page.view.focusDept)
                        flows: page.view.flowParts(page.view.focusDept)
                    }
                    Column {
                        spacing: 18
                        Hero {
                            value: {
                                var n = 0
                                for (var i = 0; i < page.view.behind.length; i++)
                                    if (page.view.behind[i].department_id === page.view.focusDept) n++
                                return String(n)
                            }
                            label: "PCs behind"
                            tone: "warn"
                        }
                    }
                }

                foot: Legend {
                    items: [{ label: "Confirmed / on track", color: Theme.ok, round: true },
                            { label: "Behind / needs attention", color: Theme.warn, round: true },
                            { label: "Failing / overdue", color: Theme.danger, round: true }]
                }
            }
        }
    }
}
