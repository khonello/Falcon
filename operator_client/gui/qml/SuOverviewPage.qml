import QtQuick
import "."

// THE SUPER USER'S OVERVIEW. Not the Admin's console: the Admin looks after machines, the Super User looks after the organisation. So it opens on what is waiting on
// them (decisions only they can make), then the four things Falcon is sold on as a 2 x 2 -- Tasks, Flows, Restricted, Detective, each with its three figures and the
// few that most need a look, each opening its own page -- and last, a slim line on the organisation itself (machines, departments, versions, broken rules).
Page {
    id: page
    objectName: "overviewView"

    readonly property var q: Desk.queue
    readonly property int urgent: q.filter(function (x) { return x.sev === "high" || x.sev === "critical" }).length

    // --- the four, each asked of the Engine by itself; every one keeps what it last said if the Engine is slow -------------------------------------------------
    property var cases: []
    property var ov: ({ by_level: { noted: 0, "case": 0, urgent: 0 }, by_intent: {}, reviewed: 0 })
    property var flows: []
    property var marks: []
    property var tasks: []
    function loadCore() {
        if (!falcon.isConnected || falcon.role !== "super_user") return
        falcon.call("detective.cases", { include_noted: false, status: "open" }, function (ok, r) { if (ok && r) page.cases = r.cases || [] })
        falcon.call("detective.overview", {}, function (ok, r) { if (ok && r && r.by_level) page.ov = r })
        falcon.call("flow.list", {}, function (ok, r) { if (ok && r) page.flows = r.flows || [] })
        falcon.call("marks.list", { scope: "all" }, function (ok, r) { if (ok && r) page.marks = r.marks || [] })
        falcon.call("task.dept_list", {}, function (ok, r) { if (ok && r) page.tasks = r.tasks || [] })
    }
    Component.onCompleted: loadCore()
    Connections {
        target: falcon
        function onConnected() { page.loadCore() }
        function onPushReceived(type, payload) { if (/^(detective|flow|mark|task|proposal)/.test(type)) again.restart() }
    }
    Timer { id: again; interval: 500; onTriggered: page.loadCore() }

    // tasks: yours to close are the ones every Admin told has marked done
    readonly property var openTasks: tasks.filter(function (t) { return !t.completed_at })
    readonly property var toClose: openTasks.filter(function (t) { return t.standing === "done" })
    readonly property var late: openTasks.filter(function (t) { return t.deadline_at && Time.ms(t.deadline_at) < Time.now && t.standing !== "done" })
    readonly property var taskRows: openTasks.slice().sort(function (a, b) {
        return (b.standing === "done" ? 1 : 0) - (a.standing === "done" ? 1 : 0) || Time.ms(a.deadline_at || "2100-01-01") - Time.ms(b.deadline_at || "2100-01-01") }).slice(0, 3)
    readonly property var standingWord: ({ told: "Told", seen: "Seen", ongoing: "Ongoing", done: "Done · yours to close" })

    // flows
    readonly property var running: flows.filter(function (f) { return f.status === "active" })
    readonly property var held: flows.filter(function (f) { return f.status !== "active" && f.status !== "inactive" })
    readonly property var asking: flows.filter(function (f) { return f.pause_reason === "restricted:consent" || f.pause_reason === "consent:pending" || f.consent_status === "pending" })
    readonly property var flowRows: held.slice(0, 3)
    function flowWhy(f) {
        var r = f.pause_reason || ""
        return r === "restricted:consent" ? "waiting for the owner of something restricted" : r === "consent:pending" ? "waiting for the other side to agree"
             : r.indexOf("destination:") === 0 ? "its destination is not there" : r.indexOf("source:") === 0 ? "its source is not there" : f.status === "paused" ? "paused" : f.status
    }

    // restricted
    readonly property int copies: marks.reduce(function (a, m) { return a + (m.copies || 0) }, 0)
    readonly property int carried: marks.filter(function (m) { return m.carried_by && m.carried_by.length > 0 }).length
    readonly property var markRows: marks.slice().sort(function (a, b) { return (b.copies || 0) - (a.copies || 0) }).slice(0, 3)

    // the organisation itself
    readonly property var devs: Fleet.deviations
    readonly property var week: devs.filter(function (d) { return Time.ms(d.detected_at) >= Time.now - 7 * 86400000 })
    readonly property int openWeek: week.filter(function (d) { return !d.resolved_at }).length
    readonly property var off: Fleet.machines.filter(function (m) { return !m.online })
    readonly property int behind: Fleet.machines.filter(function (m) { return m.behind }).length
    readonly property string nextVer: Fleet.rollout && Fleet.rollout.version ? Fleet.rollout.version.version_string : "the next version"
    readonly property var noAdmin: Fleet.depts.filter(function (d) { return !d.admins.length })

    Drawer {
        id: decide
        page: page
        width: Math.min(980, (page.Window.window ? page.Window.window.width : 1200) - 32)
        title: "Decide"
        property string id0: ""
        readonly property var d: { for (var i = 0; i < Desk.queue.length; i++) if (Desk.queue[i].id === id0) return Desk.queue[i]; return null }
        Work { width: parent.width; d: decide.d; onDecided: function (id) { var next = Desk.queue.filter(function (x) { return x.id !== id })[0]; if (next) decide.id0 = next.id } }
        Txt { visible: decide.d === null; text: "Decided. Nothing else is waiting here."; color: Theme.text3 }
    }

    // one figure of a quadrant, and one line of it
    component Fig: Column {
        property string value: "0"
        property string label: ""
        property color tone: Theme.text
        spacing: 1
        Txt { text: parent.value; font.pixelSize: 26; font.weight: Font.DemiBold; color: parent.tone; elide: Text.ElideNone }
        Txt { text: parent.label; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
    }
    component Line: Rectangle {
        property string text: ""
        property string aside: ""
        property color dot: Theme.text4
        property color rightTone: Theme.text3
        signal clicked()
        width: parent.width; height: 38
        color: la.containsMouse ? Theme.surface2 : "transparent"
        Rectangle { x: 14; width: 8; height: 8; radius: 2; color: parent.dot; anchors.verticalCenter: parent.verticalCenter }
        Txt { x: 32; width: parent.width - 32 - rightLabel.width - 28; anchors.verticalCenter: parent.verticalCenter; text: parent.text }
        Txt { id: rightLabel; anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter; text: parent.aside; color: parent.rightTone; font.pixelSize: 12; elide: Text.ElideNone }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
        MouseArea { id: la; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: parent.clicked() }
    }
    component Figures: Row {
        width: parent.width
        spacing: 0
        leftPadding: 14
        topPadding: 14
        bottomPadding: 12
    }

    // --- 1. what is waiting on you ------------------------------------------------------------------------------------------------------------------------
    Panel {
        id: waitP
        objectName: "waitingBand"
        width: parent.width
        flush: true
        title: "Waiting on you"
        sub: page.q.length ? Theme.fmt(page.q.length) + (page.urgent ? " · " + page.urgent + " urgent" : "") + " · click one to decide it" : "decisions only you can make"
        Column {
            width: parent.width
        Empty { visible: page.q.length === 0; width: parent.width; h: 120; icon: "check"; title: "Nothing is waiting on you"; text: "Reports nobody below you can take, Detective's suggestions and decisions only you can make appear here." }
        Grid {
            visible: page.q.length > 0
            width: parent.width
            columns: 2
            Repeater {
                model: page.q.slice(0, 6)
                Rectangle {
                    required property var modelData
                    width: waitP.width / 2 - 1; height: 44
                    color: wa.containsMouse ? Theme.surface2 : "transparent"
                    Rectangle { x: 14; width: 8; height: 8; radius: 2; color: Fleet.sevColor(modelData.sev); anchors.verticalCenter: parent.verticalCenter }
                    Txt { x: 32; width: parent.width - 120; anchors.verticalCenter: parent.verticalCenter; text: modelData.short }
                    Txt { anchors.right: parent.right; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter; text: modelData.age; mono: true; color: Theme.text3; font.pixelSize: 11; elide: Text.ElideNone }
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    MouseArea { id: wa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { decide.id0 = modelData.id; decide.open() } }
                }
            }
        }
        Item { visible: page.q.length > 6; width: parent.width; height: 38
               More { x: 14; anchors.verticalCenter: parent.verticalCenter; n: page.q.length - 6; what: "waiting"; onClicked: { decide.id0 = page.q[6].id; decide.open() } } }
        }
    }

    // --- 2. the four, two by two (each row one height) -------------------------------------------------------------------------------------------------
    Row {
        width: parent.width
        spacing: 14
        readonly property real h: Math.max(tp.implicitHeight, fp.implicitHeight)
        Panel {
            id: tp
            objectName: "quadTasks"
            width: (parent.width - 14) / 2
            height: parent.h
            flush: true
            title: "Tasks"
            sub: "what you have given departments"
            extra: Btn { small: true; kind: "link"; text: "Tasks →"; onClicked: Nav.go("tasks") }
            Column {
                width: parent.width
            Figures {
                Fig { width: 120; value: Theme.fmt(page.openTasks.length); label: "open" }
                Fig { width: 150; value: Theme.fmt(page.toClose.length); label: "done, yours to close"; tone: page.toClose.length ? Theme.accent : Theme.text }
                Fig { width: 120; value: Theme.fmt(page.late.length); label: "past their date"; tone: page.late.length ? Theme.crit : Theme.text }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.grid }
            Empty { visible: page.taskRows.length === 0; width: parent.width; h: 130; icon: "checksquare"; title: "No open tasks"; text: "Give a department a piece of work and follow it here." }
            Repeater {
                model: page.taskRows
                Line { required property var modelData; text: modelData.title; aside: page.standingWord[modelData.standing] || modelData.standing
                       dot: modelData.standing === "done" ? Theme.accent : Theme.text4; rightTone: modelData.standing === "done" ? Theme.accent : Theme.text3; onClicked: Nav.go("tasks") }
            }
            }
        }
        Panel {
            id: fp
            objectName: "quadFlows"
            width: (parent.width - 14) / 2
            height: parent.h
            flush: true
            title: "Flows"
            sub: "files moving between machines"
            extra: Btn { small: true; kind: "link"; text: "Flows →"; onClicked: Nav.go("flows") }
            Column {
                width: parent.width
            Figures {
                Fig { width: 120; value: Theme.fmt(page.running.length); label: "running" }
                Fig { width: 120; value: Theme.fmt(page.held.length); label: "held up"; tone: page.held.length ? Theme.med : Theme.text }
                Fig { width: 150; value: Theme.fmt(page.asking.length); label: "waiting for a yes"; tone: page.asking.length ? Theme.accent : Theme.text }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.grid }
            Empty { visible: page.flowRows.length === 0; width: parent.width; h: 130; icon: "branches"; title: page.flows.length ? "Every flow is running" : "No flows yet"; text: "A flow that is held up, and why, shows here." }
            Repeater {
                model: page.flowRows
                Line { required property var modelData; text: modelData.source_hostname + " → " + (modelData.destinations.length ? (modelData.destinations[0].destination_hostname || "a folder") : "nowhere")
                       aside: page.flowWhy(modelData); dot: Theme.med; onClicked: Nav.go("flows") }
            }
            }
        }
    }
    Row {
        width: parent.width
        spacing: 14
        readonly property real h: Math.max(rp.implicitHeight, dtp.implicitHeight)
        Panel {
            id: rp
            objectName: "quadRestricted"
            width: (parent.width - 14) / 2
            height: parent.h
            flush: true
            title: "Restricted"
            sub: "what must stay where it belongs"
            extra: Btn { small: true; kind: "link"; text: "Restricted →"; onClicked: Nav.go("restricted") }
            Column {
                width: parent.width
            Figures {
                Fig { width: 120; value: Theme.fmt(page.marks.length); label: "marked" }
                Fig { width: 150; value: Theme.fmt(page.copies); label: "copies found elsewhere"; tone: page.copies ? Theme.crit : Theme.text }
                Fig { width: 120; value: Theme.fmt(page.carried); label: "carried by flows" }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.grid }
            Empty { visible: page.markRows.length === 0; width: parent.width; h: 130; icon: "fileprotect"; title: "Nothing is marked"; text: "Mark a file or folder and Falcon follows its content wherever it is copied." }
            Repeater {
                model: page.markRows
                Line { required property var modelData; text: modelData.name + " · " + modelData.host
                       aside: modelData.copies ? Theme.many(modelData.copies, "copy", "copies") + " elsewhere" : "only in its place"
                       dot: modelData.copies ? Theme.crit : Theme.ok; rightTone: modelData.copies ? Theme.crit : Theme.text3; onClicked: Nav.go("restricted") }
            }
            }
        }
        Panel {
            id: dtp
            objectName: "quadDetective"
            width: (parent.width - 14) / 2
            height: parent.h
            flush: true
            title: "Detective"
            sub: "what people seem to be trying to do"
            extra: Btn { small: true; kind: "link"; text: "Detective →"; onClicked: Nav.go("detective") }
            Column {
                width: parent.width
            Figures {
                Fig { width: 120; value: Theme.fmt(page.ov.by_level.urgent); label: "urgent"; tone: page.ov.by_level.urgent ? Theme.crit : Theme.text }
                Fig { width: 120; value: Theme.fmt(page.ov.by_level["case"]); label: "cases"; tone: page.ov.by_level["case"] ? Theme.med : Theme.text }
                Fig { width: 150; value: Theme.fmt(page.ov.by_level.noted); label: "noted quietly" }
            }
            Rectangle { width: parent.width; height: 1; color: Theme.grid }
            Empty { visible: page.cases.length === 0; width: parent.width; h: 130; icon: "filesearch"; title: "Nothing to look at"; text: "When several small things add up to a pattern, the strongest show here." }
            Repeater {
                model: page.cases.slice(0, 3)
                Line { required property var modelData; text: modelData.intent + " · " + modelData.host
                       aside: modelData.level === "urgent" ? "Urgent" : "Case"; dot: modelData.level === "urgent" ? Theme.crit : Theme.med
                       rightTone: modelData.level === "urgent" ? Theme.crit : Theme.med; onClicked: Nav.go("detective") }
            }
            }
        }
    }

    // --- 3. the organisation itself, one slim line ------------------------------------------------------------------------------------------------------------
    Strip {
        objectName: "orgStrip"
        width: parent.width
        items: [
            { label: "Machines online", value: Theme.fmt(Fleet.machines.length - page.off.length) + " / " + Theme.fmt(Fleet.machines.length),
              delta: page.off.length ? (page.off.length === 1 ? page.off[0].host + " is" : Theme.fmt(page.off.length) + " are") + " offline" : "all online", dc: page.off.length ? Theme.crit : undefined },
            { label: "Departments", value: Theme.fmt(Fleet.depts.length), delta: page.noAdmin.length ? page.noAdmin.map(function (d) { return d.name }).join(", ") + " has no Admin" : "every one has an Admin", dc: page.noAdmin.length ? Theme.crit : undefined },
            { label: "Broken rules this week", value: Theme.fmt(page.week.length), delta: page.week.length ? Theme.fmt(page.openWeek) + " still open" : "every rule kept", dc: page.openWeek ? Theme.med : undefined },
            { label: "On current version", value: String(Fleet.machines.length ? Math.round((Fleet.machines.length - page.behind) / Fleet.machines.length * 100) : 0) + "%",
              delta: page.behind ? Theme.fmt(page.behind) + " holding " + page.nextVer + " back" : page.nextVer + " can be approved", dc: page.behind ? Theme.med : undefined }
        ]
    }
}
