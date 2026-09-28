import QtQuick
import QtQuick.Layouts
import "."

// Authority, opened (board K03). The composition belongs to THIS cell, not to the Overview: a big
// chart, two told panels in a row beneath it, and one tall reading panel down the right for the
// whole height. Rollout opens into a different shape entirely, because its subject is a fleet.
//
// The subject is the department that needs attention -- the one with nobody governing it. If every
// department has an Admin there is nothing to explain, and the cell does not open at all.
Item {
    id: page
    objectName: "openedAuthority"
    property var view: null

    readonly property var subject: page.view.gapDept
    // one department's machines, read the way every other page reads them (Fleet), and drawn as the
    // one mark at full size -- the row pages sideways rather than shrinking (PATTERNS 2, 3)
    readonly property var marks: subject ? Fleet.machines(subject.workers, page.view.rollout, page.view.violations) : []
    readonly property var hosts: page.marks.map(function (m) {
        return { hostname: m.host, state: m.status === "danger" ? "danger" : m.status === "warn" ? "warn" : "ok" }
    })
    readonly property int biggest: {
        var m = 0
        for (var i = 0; i < page.view.tree.length; i++)
            m = Math.max(m, page.view.tree[i].workers.length)
        return m
    }
    // the map carries ONE mark per department: its count, in the worst tone among its machines
    function deptMark(dept) {
        var ms = Fleet.machines(dept.workers, page.view.rollout, page.view.violations)
        var bad = ms.filter(function (m) { return m.status === "danger" })
        var warn = ms.filter(function (m) { return m.status === "warn" || m.status === "entered" })
        return { label: String(ms.length),
                 status: bad.length ? "danger" : warn.length ? "warn" : ms.length ? "ok" : "free",
                 line: bad.length ? bad.length + " need you" : warn.length ? warn.length + " behind"
                       : ms.length === 1 ? "one machine" : ms.length + " machines" }
    }
    readonly property var scopedSessions: {
        if (!subject) return []
        return page.view.sessions.filter(function (s) { return s.department_id === subject.department_id })
    }
    readonly property var scopedLanes: {
        if (!subject) return []
        return subject.workers.map(function (w) {
            return { name: w.name || w.hostname, blocks: page.view.blocksFor(w.pc_id) }
        })
    }

    readonly property var fleetSays: falcon.narrate("dept_fleet", {
        hosts: page.hosts.map(function (h) {
            return { hostname: h.hostname, state: h.state === "danger" ? "failing"
                                                 : h.state === "warn" ? "behind" : "confirmed" }
        }),
        biggest: page.biggest })
    readonly property var daySays: falcon.narrate("the_day", {
        sessions: page.scopedSessions, pc_count: page.hosts.length,
        quiet_pcs: page.scopedLanes.filter(function (l) { return l.blocks.length === 0 }).length })
    readonly property var gapSays: falcon.narrate("hierarchy", { tree: page.view.tree })

    RowLayout {
        anchors.fill: parent
        spacing: 20

        ColumnLayout {
            Layout.fillWidth: true
            Layout.preferredWidth: page.width - Theme.laneWidth - 20
            Layout.fillHeight: true
            spacing: 20

            // --- the hero: the same map, with the department in question the only one lit
            GridCell {
                objectName: "openedHero"
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "The hierarchy"
                narration: page.gapSays

                OrgMap {
                    width: parent.width
                    height: Math.max(160, page.height * 0.44)
                    departments: page.view.tree
                    markFor: function (d) { return page.deptMark(d) }
                    focusId: page.subject ? page.subject.department_id : 0
                    selectedId: page.subject ? page.subject.department_id : 0
                    // single click inspects -- the panels beside the map already re-scope to the
                    // subject -- and double click is what leaves for that department's own page
                    onEntered: function (id) { shell.enterDepartment(id) }
                }
            }

            RowLayout {
                // a nested layout fills by default, which starves the hero above it
                Layout.fillWidth: true
                Layout.fillHeight: false
                Layout.preferredHeight: Math.max(210, page.height * 0.34)
                spacing: 20

                // --- told: how many machines, against the largest department
                GridCell {
                    objectName: "openedFleet"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: "Its client PCs"
                    narration: page.fleetSays

                    PagedRow {
                        objectName: "openedFleetRow"
                        width: parent.width
                        height: 96
                        itemWidth: 68
                        spacing: 12
                        model: page.marks
                        attention: function (m) { return Fleet.needsSomeone(m) ? m.host : "" }
                        delegate: MachineMark {
                            property var modelData: ({})
                            size: 56
                            label: modelData.label || ""
                            status: modelData.status || "ok"
                            name: modelData.host || ""
                            line: modelData.line || ""
                            lineTone: modelData.lineTone || ""
                            onDoubleClicked: if (modelData.pc_id) shell.enterPc(modelData.pc_id)
                        }
                    }
                    Sentence {
                        width: parent.width
                        text: page.fleetSays.sentence
                    }
                }

                // --- told: the same timeline, scoped to this department
                GridCell {
                    objectName: "openedSessions"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: "Sessions there"
                    narration: page.daySays

                    DayTimeline {
                        width: parent.width
                        laneGap: 8
                        laneHeight: 18
                        lanes: page.scopedLanes.length > 0 ? page.scopedLanes : page.view.skeletonLanes
                        fromHour: page.view.windowStart
                        toHour: page.view.windowEnd
                    }
                    Sentence {
                        width: parent.width
                        text: page.daySays.sentence
                    }
                }
            }
        }

        // --- the words: what the map cannot say, for the whole height. A GridCell like the
        //     others, so its title sits above it on the frame and the page reads as one thing.
        GridCell {
            objectName: "openedReading"
            Layout.fillWidth: false
            Layout.preferredWidth: Theme.laneWidth
            Layout.fillHeight: true
            title: "What the gap means"
            topAlign: true
            narration: page.gapSays

            ReadingBody {
                width: parent.width
                narration: page.gapSays
                maxFacts: 4
                onActionTriggered: shell.notify(narration.action + " — not wired yet", false)
            }
        }
    }
}
