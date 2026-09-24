import QtQuick
import QtQuick.Layouts
import "."

// Page 2, composed (board P03). Its signature is an equal quartet: four boxes the same size, the
// density rising 2 → 3 → 3 → 4 across the reading order. A different shape from page 1 on purpose
// — pages that all share one shape stop telling you which page you are on.
//
// Descending into a department keeps the quartet and changes what fills it: the map stays and
// quietens everything but that department, so descent is a change of attention, not a new screen.
Item {
    id: page
    property var view: null
    readonly property bool descended: page.view.focusDept !== 0

    readonly property var hierarchySays: falcon.narrate("hierarchy", { tree: page.view.tree })
    readonly property var assistSays: falcon.narrate("assistance", { pairs: page.view.assistPairs })
    readonly property var routingSays: falcon.narrate("routing", {
        categories: (page.view.routing.categories || []), routing: (page.view.routing.routing || []) })
    // scoped to the department you descended into, not the whole system
    readonly property var workSays: falcon.narrate("work", {
        tasks: page.descended ? page.view.tasksIn(page.view.focusDept) : page.view.tasks,
        flows: page.descended ? page.view.flowsIn(page.view.focusDept) : page.view.flows,
        overdue: page.descended ? page.view.overdueIn(page.view.focusDept) : page.view.overdueTasks })

    GridLayout {
        anchors.fill: parent
        columns: 2
        rowSpacing: 16
        columnSpacing: 16

        // --- density 2: the map. The page's subject, and the only thing here you act on by
        //     pointing at it.
        Panel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: "The hierarchy"
            note: page.descended ? (page.view.focused ? page.view.focused.name + ", in place" : "")
                                 : "every department, Admin and PC you govern"
            notice: page.hierarchySays.state === "empty" ? page.hierarchySays.note : ""
            noticeSub: page.hierarchySays.state === "empty" ? page.hierarchySays.sentence : ""

            OrgMap {
                width: parent.width
                height: Math.max(140, page.height / 2 - 150)
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

        // --- density 3: a shape with the one sentence it is making.
        Panel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !page.descended
            title: "Assistance"
            note: "across departments, today"

            Arcs {
                width: parent.width
                height: Math.max(110, page.height / 2 - 190)
                nodes: page.view.assistNodes
                links: page.view.assistLinks
            }
            Sentence { width: parent.width; text: page.assistSays.sentence }
        }

        Panel {
            id: herePanel
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: page.descended
            title: "Sessions here"
            note: "who held each PC today"

            DayTimeline {
                width: parent.width
                laneHeight: Math.max(16, Math.min(30, (herePanel.height - 150)
                                                      / Math.max(1, lanes.length) - laneGap))
                lanes: page.view.timelineLanes.length > 0 ? page.view.timelineLanes : page.view.skeletonLanes
                fromHour: page.view.windowStart
                toHour: page.view.windowEnd
            }
        }

        // --- density 3 again: the other relationship this page is responsible for.
        Panel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !page.descended
            title: "Report routing"
            note: "additive, always"
            notice: page.routingSays.state === "empty" ? page.routingSays.note : ""
            noticeSub: page.routingSays.state === "empty" ? page.routingSays.sentence : ""

            RoutingMap {
                width: parent.width
                height: implicitHeight
                categories: page.view.routingRows
                destinations: page.view.routingDests
            }
            Sentence {
                width: parent.width
                text: page.routingSays.state === "ok" ? page.routingSays.sentence : ""
            }
        }

        Panel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: page.descended
            title: page.view.focused ? (page.view.focused.name + ", in numbers") : ""
            note: "its rollout, and its work"

            StackedBars {
                width: parent.width
                labelWidth: 72
                rows: page.view.focused
                      ? [{ label: "Rollout", parts: page.view.rolloutParts(page.view.focusDept) }]
                      : page.view.skeletonRows
            }
            HealthCard {
                width: parent.width * 0.62
                name: "Tasks and flows"
                tint: Theme.series(page.view.deptIndex(page.view.focusDept))
                tasks: page.view.taskParts(page.view.focusDept)
                flows: page.view.flowParts(page.view.focusDept)
            }
        }

        // --- density 4: the words. What the map cannot say — what the gap actually means.
        ReadingPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            title: page.descended ? "This department" : "Where authority is thin"
            narration: page.descended ? page.workSays : page.hierarchySays
            onActionTriggered: shell.notify(narration.action + " — not wired yet", false)
        }

        // the quartet's fourth box once you are inside a department: its Admins, a list not a chart
        Panel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: page.descended
            title: "Its Admins"
            note: "who governs here"
            notice: page.descended && page.view.focused && page.view.focused.admins.length === 0
                    ? "No Admin governs this department" : ""
            noticeSub: page.descended && page.view.focused && page.view.focused.admins.length === 0
                       ? "its client PCs answer to nobody below you" : ""

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
            }
        }
    }
}
