import QtQuick
import "."

// DETECTIVE, AT THE SUPER USER'S LEVEL: what people seem to be trying to do, by department. A view, not a workbench: a department's Admin reviews the cases on their department's machines
// (that is the Admin's Detective page, with the picture, the rules and the suggestions). The Super User sees every case by department and decides only the two kinds that are theirs: a case an Admin
// sent up, and a case on an Admin's own workstation (nobody below them can judge it). Any other case offers a way into the Admin's console. A case is a pattern and its evidence, never an accusation.
Page {
    id: page
    objectName: "detectiveOverview"

    property var cases: []
    property var ov: ({ by_level: { noted: 0, "case": 0, urgent: 0 }, by_intent: {}, reviewed: 0 })
    property var cur: null                       // the case open in the drawer
    property var det: null                       // detective.case for it
    property string note: ""

    function load() {
        if (!falcon.isConnected) return
        falcon.call("detective.cases", { include_noted: true, status: "open" }, function (ok, r) {
            if (!ok) return
            var open = r.cases || []
            falcon.call("detective.cases", { status: "escalated" }, function (ok2, r2) {
                var up = ok2 && r2 ? (r2.cases || []) : [], ids = {}
                open.forEach(function (c) { ids[c.id] = true })
                page.cases = open.concat(up.filter(function (c) { return !ids[c.id] }))
            })
        })
        falcon.call("detective.overview", {}, function (ok, r) { if (ok && r.by_level) page.ov = r })
    }
    Component.onCompleted: load()
    Connections { target: falcon; function onConnected() { page.load() } function onPushReceived(type) { if (/^detective/.test(type)) again.restart() } }
    Timer { id: again; interval: 400; onTriggered: page.load() }

    function onAdmin(c) {
        for (var i = 0; i < Fleet.depts.length; i++) for (var j = 0; j < Fleet.depts[i].admins.length; j++) if (Fleet.depts[i].admins[j].hostname === c.host) return true
        return false
    }
    function mine(c) { return c.status === "escalated" || onAdmin(c) }        // the cases that are the Super User's to decide
    readonly property var levelWord: ({ urgent: "Urgent", "case": "Case", noted: "Noted" })
    function tone(c) { return c.level === "urgent" ? Theme.crit : c.level === "case" ? Theme.med : Theme.text4 }
    function inDept(id) {
        var o = { urgent: 0, "case": 1, noted: 2 }
        return cases.filter(function (c) { return c.department_id === id })
            .sort(function (a, b) { return (page.mine(b) ? 1 : 0) - (page.mine(a) ? 1 : 0) || o[a.level] - o[b.level] || b.weight - a.weight })
    }
    readonly property var headOffice: cases.filter(function (c) { return !Fleet.dept(c.department_id) })
    function segsOf(list) { return ["urgent", "case", "noted"].map(function (k) { return { n: list.filter(function (c) { return c.level === k }).length, c: k === "urgent" ? Theme.crit : k === "case" ? Theme.med : Theme.text4 } }) }
    function asideOf(c) { return c.status === "escalated" ? "Sent up to you" : page.onAdmin(c) ? "Admin's machine" : page.levelWord[c.level] }
    function adminOf(c) { var d = Fleet.dept(c.department_id); return d && d.admins.length ? d.admins[0] : null }
    readonly property int toDecide: cases.filter(function (c) { return page.mine(c) }).length

    function show(c) { page.note = ""; page.det = null; page.cur = c; drawer.open()
        falcon.call("detective.case", { case_id: c.id }, function (ok, r) { if (ok && page.cur && page.cur.id === c.id) page.det = r }) }
    function review(outcome) {
        falcon.call("detective.review", { case_id: cur.id, outcome: outcome, note: note }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Could not record that"); return }
            Msg.ok("Recorded: " + outcome); page.note = ""; drawer.close(); page.load()
        })
    }

    Strip {
        width: parent.width
        items: [
            { label: "Urgent", value: Theme.fmt(page.ov.by_level.urgent), delta: page.ov.by_level.urgent ? "worth looking at now" : "nothing urgent", dc: page.ov.by_level.urgent ? Theme.crit : undefined },
            { label: "Cases", value: Theme.fmt(page.ov.by_level["case"]), delta: page.ov.by_level["case"] ? "several things add up" : "none open", dc: page.ov.by_level["case"] ? Theme.med : undefined },
            { label: "Yours to decide", value: Theme.fmt(page.toDecide), delta: page.toDecide ? "sent up, or on an Admin's machine" : "nothing waiting", dc: page.toDecide ? Theme.accent : undefined },
            { label: "Reviewed", value: Theme.fmt(page.ov.reviewed), delta: "by a person, with their note" }
        ]
    }
    Txt { text: "By department · the department's Admin reviews its cases; you decide the ones sent up and those on an Admin's own machine"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }

    Grid {
        objectName: "deptCards"
        width: parent.width
        columns: 2
        columnSpacing: 14
        rowSpacing: 14
        Repeater {
            model: Fleet.depts
            DeptCard {
                required property var modelData
                readonly property var list: page.inDept(modelData.id)
                width: (page.w - 14) / 2
                title: modelData.name
                sub: modelData.admins.length ? Theme.listNames(modelData.admins.map(function (a) { return a.name })) : ""
                noAdmin: modelData.admins.length === 0
                segs: page.segsOf(list)
                total: list.length ? Theme.many(list.length, "case") : ""
                Column {
                    width: parent.width
                    Repeater {
                        model: list.slice(0, 4)
                        DeptLine { required property var modelData; dot: page.tone(modelData); text: modelData.intent + " · " + modelData.host; aside: page.asideOf(modelData)
                                   asideTone: page.mine(modelData) ? Theme.accent : modelData.level === "urgent" ? Theme.crit : Theme.text3; onClicked: page.show(modelData) }
                    }
                    Item { visible: list.length > 4; width: parent.width; height: 26
                           More { x: 6; anchors.verticalCenter: parent.verticalCenter; n: list.length - 4; what: "cases"; onClicked: page.show(list[4]) } }
                    Item { visible: list.length === 0; width: parent.width; height: 60
                           Txt { anchors.centerIn: parent; text: "Nothing to look at here"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
                }
            }
        }
        DeptCard {
            visible: page.headOffice.length > 0
            width: (page.w - 14) / 2
            title: "Head office"
            sub: "machines that belong to no department"
            segs: page.segsOf(page.headOffice)
            total: Theme.many(page.headOffice.length, "case")
            Column {
                width: parent.width
                Repeater {
                    model: page.headOffice.slice(0, 4)
                    DeptLine { required property var modelData; dot: page.tone(modelData); text: modelData.intent + " · " + modelData.host; aside: page.asideOf(modelData); onClicked: page.show(modelData) }
                }
            }
        }
    }

    // --- one case, in a narrow drawer ------------------------------------------------------------------------------------------------------------------------------
    Drawer {
        id: drawer
        page: page
        width: 460
        title: page.cur ? page.cur.intent : ""
        Column {
            width: parent.width
            spacing: 14
            Txt { objectName: "caseHeadline"; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; text: page.cur ? page.cur.headline : "" }
            Txt { visible: !!page.cur && page.cur.model_says !== null && page.cur.model_says !== undefined && page.cur.model_says !== ""; width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                  text: page.cur && page.cur.model_says ? "The local model reads it as: " + page.cur.model_says.toLowerCase() + ". That is its opinion, not the rules'." : "" }
            Column {
                width: parent.width
                Repeater {
                    model: page.cur ? [["Level", page.levelWord[page.cur.level]], ["Machine", page.cur.host], ["Began", Time.at(page.cur.first_at)], ["Last seen", Time.at(page.cur.last_at)],
                                       ["Status", page.cur.status === "open" ? "Open" : page.cur.status === "escalated" ? "Sent up to you" : page.cur.status.charAt(0).toUpperCase() + page.cur.status.slice(1)]] : []
                    Item {
                        required property var modelData
                        width: parent.width; height: 30
                        Txt { width: 100; anchors.verticalCenter: parent.verticalCenter; text: modelData[0]; color: Theme.text3 }
                        Txt { x: 112; width: parent.width - 112; anchors.verticalCenter: parent.verticalCenter; text: modelData[1]; mono: modelData[0] === "Machine" }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
            }
            Column {
                visible: !!page.det && !!page.det.board && page.det.board.length > 0
                width: parent.width
                spacing: 6
                Txt { text: "WHAT IT COVERS"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Repeater {
                    model: page.det && page.det.board ? page.det.board : []
                    Flow {
                        required property var modelData
                        width: parent.width
                        spacing: 6
                        Repeater {
                            model: modelData.areas.filter(function (a) { return a.covered })
                            Rectangle {
                                required property var modelData
                                width: al.implicitWidth + 20; height: 26; radius: 13
                                color: Theme.alpha(page.cur && page.cur.level === "urgent" ? Theme.crit : Theme.med, 0.16)
                                border.width: 1; border.color: page.cur && page.cur.level === "urgent" ? Theme.crit : Theme.med
                                Txt { id: al; anchors.centerIn: parent; text: parent.modelData.name; font.pixelSize: 12; elide: Text.ElideNone }
                            }
                        }
                    }
                }
            }
            Column {
                visible: page.cur !== null
                width: parent.width
                spacing: 4
                Txt { text: "IN ORDER"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Repeater {
                    model: page.cur ? page.cur.story.slice(0, 8) : []
                    Row {
                        required property string modelData
                        spacing: 10
                        Txt { text: modelData.slice(0, modelData.indexOf("  ")); mono: true; color: Theme.text3; width: 64; font.pixelSize: 12; elide: Text.ElideNone }
                        Txt { text: modelData.slice(modelData.indexOf("  ") + 2); width: drawer.width - 64 - 70; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                    }
                }
                Txt { visible: !!page.cur && page.cur.story.length > 8; text: "and " + (page.cur ? page.cur.story.length - 8 : 0) + " more, on the department's Detective page"; color: Theme.text3; font.pixelSize: 12 }
            }
            // theirs to decide: a case sent up, or one on an Admin's own machine
            Column {
                objectName: "detDecision"
                visible: page.cur !== null && page.mine(page.cur) && (page.cur.status === "open" || page.cur.status === "escalated")
                width: parent.width
                spacing: 8
                Txt { text: "YOUR DECISION"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text2; font.pixelSize: 12
                      text: page.cur && page.cur.status === "escalated" ? "An Admin sent this up to you." : "It is on an Admin's own workstation, so nobody below you can judge it." }
                Field { objectName: "detNote"; width: parent.width; placeholderText: "A note (optional): what you found out"; maximumLength: 500; text: page.note; onTextEdited: page.note = text }
                Row {
                    spacing: 8
                    Btn { objectName: "detExplained"; text: "It is explained"; onClicked: page.review("explained") }
                    Btn { objectName: "detAccepted"; text: "Accept it"; onClicked: page.review("accepted") }
                    Btn { objectName: "detDismissed"; text: "Dismiss"; onClicked: page.review("dismissed") }
                }
            }
            Column {
                visible: page.cur !== null && !page.mine(page.cur)
                width: parent.width
                spacing: 8
                Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                      text: page.cur && page.cur.status !== "open" ? "Reviewed: " + page.cur.status + (page.cur.note ? " · " + page.cur.note : "") + "." : "The department's Admin reviews this case." }
                Btn { objectName: "openInConsole"; visible: page.cur !== null && page.adminOf(page.cur) !== null; iconName: "login"
                      text: page.cur && page.adminOf(page.cur) ? "Open in " + page.adminOf(page.cur).name + "'s console →" : ""
                      onClicked: { var a = page.adminOf(page.cur); drawer.close(); Nav.enter(a, ["detective", String(page.cur.id)]) } }
            }
        }
    }
}
