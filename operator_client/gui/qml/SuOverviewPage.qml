import QtQuick
import QtQuick.Shapes
import "."

// THE SUPER USER'S OVERVIEW, drawn rather than listed. What is waiting on you comes first, as a few large cards; then the organisation as a map of its machines, and
// beside it the four things Falcon is sold on (Tasks, Flows, Restricted, Detective), each as one tile: a picture, one number, and one dot for every task, flow, mark
// or case, coloured by how it stands. Nothing here is a table; a click on anything opens the page it belongs to.
Page {
    id: page
    objectName: "overviewView"

    readonly property var q: Desk.queue
    readonly property int urgent: q.filter(function (x) { return x.sev === "high" || x.sev === "critical" }).length

    property var cases: []
    property var ov: ({ by_level: { noted: 0, "case": 0, urgent: 0 }, by_intent: {}, reviewed: 0 })
    property var flows: []
    property var marks: []
    property var tasks: []
    function loadCore() {
        if (!falcon.isConnected || falcon.role !== "super_user") return
        falcon.call("detective.cases", { include_noted: true, status: "open" }, function (ok, r) { if (ok && r) page.cases = r.cases || [] })
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
    function taskTone(t) { return t.standing === "done" ? Theme.accent : (t.deadline_at && Time.ms(t.deadline_at) < Time.now) ? Theme.crit : t.standing === "told" ? Theme.text4 : Theme.ok }

    // flows
    readonly property var running: flows.filter(function (f) { return f.status === "active" })
    readonly property var held: flows.filter(function (f) { return f.status !== "active" && f.status !== "inactive" })
    readonly property var asking: flows.filter(function (f) { return f.pause_reason === "restricted:consent" || f.pause_reason === "consent:pending" || f.consent_status === "pending" })
    function flowTone(f) { return f.status === "active" ? Theme.ok : (f.pause_reason === "restricted:consent" || f.pause_reason === "consent:pending") ? Theme.accent : Theme.med }

    // restricted
    readonly property int copies: marks.reduce(function (a, m) { return a + (m.copies || 0) }, 0)
    readonly property int carried: marks.filter(function (m) { return m.carried_by && m.carried_by.length > 0 }).length
    function markTone(m) { return m.copies ? Theme.crit : Theme.ok }

    // detective
    readonly property var openCases: cases.filter(function (c) { return c.level !== "noted" })
    function caseTone(c) { return c.level === "urgent" ? Theme.crit : c.level === "case" ? Theme.med : Theme.text4 }

    Drawer {
        id: decide
        page: page
        width: Math.min(460, (page.Window.window ? page.Window.window.width : 1200) - 32)
        title: "Decide"
        property string id0: ""
        readonly property var d: { for (var i = 0; i < Desk.queue.length; i++) if (Desk.queue[i].id === id0) return Desk.queue[i]; return null }
        Work { width: parent.width; d: decide.d; onDecided: function (id) { var next = Desk.queue.filter(function (x) { return x.id !== id })[0]; if (next) decide.id0 = next.id } }
        Txt { visible: decide.d === null; text: "Decided. Nothing else is waiting here."; color: Theme.text3 }
    }

    // --- 1. what is waiting on you: a few large cards, the worst first --------------------------------------------------------------------------------------
    Column {
        id: waitCol
        objectName: "waitingBand"
        width: parent.width
        spacing: 10
        Row {
            spacing: 10
            Txt { text: "WAITING ON YOU"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66; elide: Text.ElideNone }
            Txt { visible: page.q.length > 0; text: page.q.length + (page.urgent ? " · " + page.urgent + " urgent" : ""); color: page.urgent ? Theme.crit : Theme.text3; font.pixelSize: 11; elide: Text.ElideNone }
        }
        // a card is always the same size, however many there are; more than fit are reached by the chevrons or by dragging
        Item {
            id: rail
            width: parent.width
            height: 96
            readonly property int cardW: 300
            readonly property int gap: 12
            Flickable {
                id: fl
                anchors.fill: parent
                contentWidth: cards.width
                contentHeight: height
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: Flickable.HorizontalFlick
                Behavior on contentX { NumberAnimation { duration: Theme.durBase; easing.type: Easing.OutCubic } }
                Row {
                    id: cards
                    spacing: rail.gap
                    Repeater {
                        model: page.q
                        Rectangle {
                            required property var modelData
                            objectName: "waitCard"
                            width: rail.cardW; height: rail.height; radius: Theme.radius; color: wa.containsMouse ? Theme.surface2 : Theme.surface
                            border.width: 1; border.color: Theme.mix(Fleet.sevColor(modelData.sev), Theme.border, 0.35)
                            Rectangle { x: 14; y: 14; width: 34; height: 34; radius: 17; color: Theme.alpha(Fleet.sevColor(modelData.sev), 0.14)
                                        Icon { anchors.centerIn: parent; name: modelData.icon || "alert"; size: 18; color: Fleet.sevColor(modelData.sev) } }
                            Txt { x: 58; y: 12; width: parent.width - 72; text: modelData.short; font.weight: Font.DemiBold; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
                            Txt { x: 58; anchors.bottom: parent.bottom; anchors.bottomMargin: 12; text: modelData.age; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                            MouseArea { id: wa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { decide.id0 = modelData.id; decide.open() } }
                        }
                    }
                    // nothing waiting: the same card, dotted, so the space is held and says so
                    Item {
                        objectName: "waitEmpty"
                        visible: page.q.length === 0
                        width: rail.cardW; height: rail.height
                        Shape {
                            anchors.fill: parent
                            ShapePath {
                                strokeWidth: 1.5; strokeColor: Theme.border2 !== undefined ? Theme.border2 : Theme.border; fillColor: "transparent"
                                strokeStyle: ShapePath.DashLine; dashPattern: [3, 3]
                                startX: Theme.radius; startY: 1
                                PathLine { x: rail.cardW - Theme.radius; y: 1 }
                                PathArc { x: rail.cardW - 1; y: Theme.radius; radiusX: Theme.radius; radiusY: Theme.radius }
                                PathLine { x: rail.cardW - 1; y: rail.height - Theme.radius }
                                PathArc { x: rail.cardW - Theme.radius; y: rail.height - 1; radiusX: Theme.radius; radiusY: Theme.radius }
                                PathLine { x: Theme.radius; y: rail.height - 1 }
                                PathArc { x: 1; y: rail.height - Theme.radius; radiusX: Theme.radius; radiusY: Theme.radius }
                                PathLine { x: 1; y: Theme.radius }
                                PathArc { x: Theme.radius; y: 1; radiusX: Theme.radius; radiusY: Theme.radius }
                            }
                        }
                        Row { anchors.centerIn: parent; spacing: 10
                              Icon { name: "checkcircle"; size: 22; color: Theme.ok; anchors.verticalCenter: parent.verticalCenter }
                              Column { anchors.verticalCenter: parent.verticalCenter
                                       Txt { text: "Nothing is waiting on you"; font.weight: Font.DemiBold; elide: Text.ElideNone }
                                       Txt { text: "Decisions only you can make appear here"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } } }
                    }
                }
            }
            // the chevrons appear only when there is more to reveal on that side
            Rectangle {
                objectName: "waitLeft"
                visible: fl.contentX > 2
                x: 6; anchors.verticalCenter: parent.verticalCenter
                width: 30; height: 30; radius: 15; color: la.containsMouse ? Theme.surface2 : Theme.surface; border.width: 1; border.color: Theme.border
                Icon { anchors.centerIn: parent; name: "chevl"; size: 14; color: Theme.text2 }
                MouseArea { id: la; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: fl.contentX = Math.max(0, fl.contentX - (rail.cardW + rail.gap)) }
            }
            Rectangle {
                objectName: "waitRight"
                visible: fl.contentX + fl.width < fl.contentWidth - 2
                x: parent.width - width - 6; anchors.verticalCenter: parent.verticalCenter
                width: 30; height: 30; radius: 15; color: ra.containsMouse ? Theme.surface2 : Theme.surface; border.width: 1; border.color: Theme.border
                Icon { anchors.centerIn: parent; name: "chevr"; size: 14; color: Theme.text2 }
                MouseArea { id: ra; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: fl.contentX = Math.min(fl.contentWidth - fl.width, fl.contentX + (rail.cardW + rail.gap)) }
            }
        }
    }

    // one of the four: a picture, one number, one dot per thing
    component Tile: Rectangle {
        id: tile
        property string icon: ""
        property string title: ""
        property string number: "0"
        property string caption: ""
        property color tone: Theme.text
        property var dots: []                 // one colour per thing
        property string go: ""
        width: 100; height: 168; radius: Theme.radius; color: ta.containsMouse ? Theme.surface2 : Theme.surface; border.width: 1; border.color: Theme.border
        Row { x: 16; y: 14; spacing: 8
              Icon { name: tile.icon; size: 16; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
              Txt { text: tile.title; color: Theme.text2; font.weight: Font.DemiBold; elide: Text.ElideNone } }
        Txt { x: 16; y: 40; text: tile.number; font.pixelSize: 40; font.weight: Font.DemiBold; color: tile.tone; elide: Text.ElideNone }
        Txt { x: 16; y: 90; width: parent.width - 32; text: tile.caption; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideRight }
        Flow {
            x: 16; y: 120; width: parent.width - 32; spacing: 5
            Repeater {
                model: tile.dots.slice(0, 28)
                Rectangle { required property var modelData; width: 12; height: 12; radius: 3; color: modelData }
            }
            Txt { visible: tile.dots.length > 28; text: "+" + (tile.dots.length - 28); color: Theme.text3; font.pixelSize: 11; elide: Text.ElideNone }
        }
        MouseArea { id: ta; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: Nav.go(tile.go) }
    }

    // --- 2. the organisation as a map, and the four beside it -----------------------------------------------------------------------------------------------------
    Row {
        width: parent.width
        spacing: 14
        readonly property real h: Math.max(mapP.implicitHeight, 2 * 168 + 12)
        Panel {
            id: mapP
            objectName: "orgMap"
            width: (parent.width - 14) * 7 / 12
            height: parent.h
            title: "The organisation"
            sub: Theme.fmt(Fleet.machines.length) + " machines · " + (Fleet.machines.length - Fleet.machines.filter(function (m) { return !m.online }).length) + " online"
            extra: Btn { small: true; kind: "link"; text: "Departments →"; onClicked: Nav.go("departments") }
            HostMap {
                visible: Fleet.machines.length > 0
                width: parent.width
                by: "Status"
                openLabel: "See {h}'s department →"
                moreLabel: "on Departments →"
                onOpen: function (h) { var m = Fleet.byHost[h]; Nav.go("departments", m ? m.dept : null) }
                onMore: Nav.go("departments")
            }
            Empty { visible: Fleet.loaded && Fleet.machines.length === 0; width: parent.width; h: 220; icon: "desktop"; title: "No machines yet"; text: "Machines appear here by department as they are registered."; act: "Open Departments →"; onActed: Nav.go("departments") }
        }
        Grid {
            id: four
            width: (parent.width - 14) * 5 / 12
            columns: 2
            columnSpacing: 12
            rowSpacing: 12
            readonly property real tw: (width - 12) / 2
            Tile { objectName: "quadTasks"; width: four.tw; icon: "checksquare"; title: "Tasks"; go: "tasks"; number: Theme.fmt(page.openTasks.length)
                   caption: page.toClose.length ? page.toClose.length + " done, yours to close" : page.late.length ? page.late.length + " past their date" : "all on track"
                   tone: page.toClose.length ? Theme.accent : page.late.length ? Theme.crit : Theme.text; dots: page.openTasks.map(page.taskTone) }
            Tile { objectName: "quadFlows"; width: four.tw; icon: "branches"; title: "Flows"; go: "flows"; number: Theme.fmt(page.running.length)
                   caption: page.held.length ? page.held.length + " held up" + (page.asking.length ? " · " + page.asking.length + " waiting for a yes" : "") : "all running"
                   tone: page.held.length ? Theme.med : Theme.text; dots: page.flows.map(page.flowTone) }
            Tile { objectName: "quadRestricted"; width: four.tw; icon: "fileprotect"; title: "Restricted"; go: "restricted"; number: Theme.fmt(page.marks.length)
                   caption: page.copies ? page.copies + " cop" + (page.copies === 1 ? "y" : "ies") + " found elsewhere" : "all where they belong"
                   tone: page.copies ? Theme.crit : Theme.text; dots: page.marks.map(page.markTone) }
            Tile { objectName: "quadDetective"; width: four.tw; icon: "filesearch"; title: "Detective"; go: "detective"; number: Theme.fmt(page.openCases.length)
                   caption: page.ov.by_level.urgent ? page.ov.by_level.urgent + " urgent" : page.openCases.length ? "worth a look" : "nothing to look at"
                   tone: page.ov.by_level.urgent ? Theme.crit : page.openCases.length ? Theme.med : Theme.text; dots: page.cases.map(page.caseTone) }
        }
    }
}
