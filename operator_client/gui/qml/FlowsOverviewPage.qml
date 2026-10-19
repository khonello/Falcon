import QtQuick
import "."

// FLOWS, AT THE SUPER USER'S LEVEL: every flow in the organisation, by the department it starts in, and whether it is copying. A view, not a workbench: making, editing, pausing and
// repairing a flow is the department's Admin's work (the Super User enters their console to do it). The one decision that is theirs is a flow asking to carry something *they* marked
// restricted: a bar above the cards, Allow or Keep it paused. A click on a line opens the flow in a narrow drawer, with what it is waiting to carry and the way to take that back.
Page {
    id: page
    objectName: "flowsView"

    property var flows: []
    property var cur: null                       // the flow open in the drawer
    property var rAsks: []                       // flows waiting for this person to say something restricted may be carried
    property var consents: []
    property var canDecide: []

    function load() {
        falcon.call("flow.list", {}, function (ok, r) {
            page.flows = ok ? (r.flows || []) : []
            var held = page.flows.filter(function (f) { return f.pause_reason === "restricted:consent" })
            var found = [], left = held.length
            if (!left) { page.rAsks = []; return }
            held.forEach(function (f) {
                falcon.call("flow.restricted", { flow_id: f.id }, function (ok2, r2) {
                    if (ok2 && r2) (r2.consents || []).forEach(function (c) { if (c.state === "asked" && (r2.can_decide || []).indexOf(c.id) >= 0) found.push(Object.assign({ flow: f }, c)) })
                    if (--left === 0) page.rAsks = found
                })
            })
        })
    }
    function answerRestricted(c, grant) {
        falcon.call("flow.restricted_consent", { consent_id: c.id, grant: grant }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not answered"); return }
            Msg.ok(grant ? "Allowed · the flow goes on" : "Declined · the flow stays paused")
            page.load(); page.loadConsents()
        })
    }
    function loadConsents() {
        if (!cur) { consents = []; return }
        var id = cur.id
        falcon.call("flow.restricted", { flow_id: id }, function (ok, r) {
            if (page.cur && page.cur.id === id) { page.consents = ok && r ? (r.consents || []) : []; page.canDecide = ok && r ? (r.can_decide || []) : [] }
        })
    }
    function takeBack(c) {
        falcon.call("flow.restricted_revoke", { consent_id: c.id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not taken back"); return }
            Msg.ok("Taken back · the flow stops, and the places it allowed are not allowed any more")
            page.load(); page.loadConsents()
        })
    }
    function show(f) { page.cur = f; page.consents = []; page.canDecide = []; page.loadConsents(); drawer.open() }
    Component.onCompleted: load()
    Connections { target: falcon; function onConnected() { page.load() } function onPushReceived(type) { if (/^flow/.test(type)) again.restart() } }
    Timer { id: again; interval: 300; onTriggered: page.load() }

    function folder(p) { var x = String(p || "").replace(/[\\\/]+$/, "").split(/[\\\/]/); return x[x.length - 1] || p }
    function nameOf(f) { return folder(f.source_path) + "-" + f.id }
    function creator(f) { return f.created_by_account_id === falcon.accountId ? "You" : (f.created_by_name || Fleet.adminName(f.created_by_account_id) || "—") }
    // [words, tone, kind]: copying, waiting for someone, or held up
    function stateOf(f) {
        var paused = (f.destinations || []).filter(function (d) { return d.paused_reason })
        if (f.consent_status === "pending") return ["Waiting for agreement", "wait", "wait"]
        if (f.pause_reason === "restricted:consent") return ["Waiting for consent to carry something restricted", "wait", "wait"]
        if (f.status === "inactive") return ["Retired", "wait", "off"]
        if (f.status === "paused" || paused.length) return ["A branch is paused", "bad", "deg"]
        return ["Copying", "good", "act"]
    }
    readonly property var tone: ({ act: Theme.ok, wait: Theme.accent, deg: Theme.med, off: Theme.text4 })
    readonly property var shortWord: ({ act: "Copying", wait: "Waiting for a yes", deg: "Held up", off: "Retired" })
    function pathOf(f) { return f.source_hostname + " → " + (f.destinations || []).map(function (d) { return d.destination_hostname || "storage" }).filter(function (v, i, a) { return a.indexOf(v) === i }).join(", ") }
    function deptOf(f) { var m = Fleet.byHost[f.source_hostname]; return m ? m.dept : null }
    function inDept(id) {
        var o = { deg: 0, wait: 1, act: 2, off: 3 }
        return flows.filter(function (f) { return page.deptOf(f) === id }).sort(function (a, b) { return o[page.stateOf(a)[2]] - o[page.stateOf(b)[2]] })
    }
    readonly property var elsewhere: flows.filter(function (f) { return !Fleet.dept(page.deptOf(f)) })
    function segsOf(list) { return ["act", "wait", "deg"].map(function (k) { return { n: list.filter(function (f) { return page.stateOf(f)[2] === k }).length, c: page.tone[k] } }) }
    readonly property int nAct: flows.filter(function (f) { return page.stateOf(f)[2] === "act" }).length
    readonly property int nDeg: flows.filter(function (f) { return page.stateOf(f)[2] === "deg" }).length
    readonly property int nWait: flows.filter(function (f) { return page.stateOf(f)[2] === "wait" }).length
    readonly property var steps: cur ? Sync.steps(cur) : []

    // a flow wants to carry something restricted, and the Super User made the restriction (or it is theirs to answer)
    Repeater {
        model: page.rAsks
        Rectangle {
            required property var modelData
            objectName: "restrictedAsk_" + modelData.id
            width: page.w
            height: 52
            radius: Theme.radius
            color: Theme.alpha(Theme.med, 0.10)
            border.width: 1
            border.color: Theme.alpha(Theme.med, 0.5)
            Row {
                x: 14
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10
                Icon { name: "lock"; size: 15; color: Theme.med; anchors.verticalCenter: parent.verticalCenter }
                Txt { anchors.verticalCenter: parent.verticalCenter; width: page.w - 330; wrapMode: Text.WordWrap; elide: Text.ElideNone; textFormat: Text.RichText
                      text: "<b>Flow " + modelData.flow_id + "</b> wants to carry <b>" + modelData.name + "</b>, which is restricted <span style='color:" + Theme.text3 + "'>· from <span style='font-family:" + Theme.mono + "'>"
                            + (modelData.sample_path || "") + "</span>. Nothing moves until you say so.</span>" }
            }
            Row {
                anchors.right: parent.right
                anchors.rightMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Btn { objectName: "restrictedDecline"; small: true; text: "Keep it paused"; onClicked: page.answerRestricted(modelData, false) }
                Btn { objectName: "restrictedAllow"; small: true; kind: "primary"; text: "Allow this flow"; onClicked: page.answerRestricted(modelData, true) }
            }
        }
    }

    // --- the head: where things stand, as a line ------------------------------------------------------------------------------------------------------------
    Item {
        width: parent.width
        height: 30
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 18
            Txt { text: Theme.fmt(page.flows.length) + (page.flows.length === 1 ? " flow" : " flows"); font.weight: Font.DemiBold; elide: Text.ElideNone }
            Row { spacing: 6; Rectangle { width: 8; height: 8; radius: 2; color: Theme.ok; anchors.verticalCenter: parent.verticalCenter } Txt { text: page.nAct + " copying"; color: Theme.text2; elide: Text.ElideNone } }
            Row { spacing: 6; visible: page.nWait > 0; Rectangle { width: 8; height: 8; radius: 2; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter } Txt { text: page.nWait + " waiting for a yes"; color: Theme.text2; elide: Text.ElideNone } }
            Row { spacing: 6; visible: page.nDeg > 0; Rectangle { width: 8; height: 8; radius: 2; color: Theme.med; anchors.verticalCenter: parent.verticalCenter } Txt { text: page.nDeg + " held up"; color: Theme.text2; elide: Text.ElideNone } }
        }
        Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "Flows are made and mended in the department's own console"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
    }

    // --- a card a department, by where its flows start ------------------------------------------------------------------------------------------------------
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
                readonly property var mine: page.inDept(modelData.id)
                width: (page.w - 14) / 2
                title: modelData.name
                sub: modelData.admins.length ? Theme.listNames(modelData.admins.map(function (a) { return a.name })) : ""
                noAdmin: modelData.admins.length === 0
                segs: page.segsOf(mine)
                total: mine.length ? Theme.many(mine.length, "flow") : ""
                Column {
                    width: parent.width
                    Repeater {
                        model: mine.slice(0, 4)
                        DeptLine { required property var modelData; dot: page.tone[page.stateOf(modelData)[2]]; text: page.pathOf(modelData); aside: page.shortWord[page.stateOf(modelData)[2]]
                                   asideTone: page.stateOf(modelData)[2] === "deg" ? Theme.med : Theme.text3; onClicked: page.show(modelData) }
                    }
                    Item { visible: mine.length > 4; width: parent.width; height: 26
                           More { x: 6; anchors.verticalCenter: parent.verticalCenter; n: mine.length - 4; what: "flows"; onClicked: page.show(mine[4]) } }
                    Item { visible: mine.length === 0; width: parent.width; height: 60
                           Txt { anchors.centerIn: parent; text: "No flow starts here"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
                }
            }
        }
        DeptCard {
            visible: page.elsewhere.length > 0
            width: (page.w - 14) / 2
            title: "Head office"
            sub: "flows that start on an Admin's workstation"
            segs: page.segsOf(page.elsewhere)
            total: Theme.many(page.elsewhere.length, "flow")
            Column {
                width: parent.width
                Repeater {
                    model: page.elsewhere.slice(0, 4)
                    DeptLine { required property var modelData; dot: page.tone[page.stateOf(modelData)[2]]; text: page.pathOf(modelData); aside: page.shortWord[page.stateOf(modelData)[2]]; onClicked: page.show(modelData) }
                }
            }
        }
    }
    Empty { visible: page.flows.length === 0; width: parent.width; h: 200; icon: "branches"; title: "No flows yet"; text: "A flow copies files one way, from one machine to others. A department's Admin makes it." }

    // --- one flow, in a narrow drawer ----------------------------------------------------------------------------------------------------------------------
    Drawer {
        id: drawer
        page: page
        width: 460
        title: page.cur ? page.nameOf(page.cur) : ""
        Column {
            width: parent.width
            spacing: 14
            Column {
                width: parent.width
                Repeater {
                    model: page.cur ? [["Made by", page.creator(page.cur)], ["Now", page.stateOf(page.cur)[0]], ["From", page.cur.source_hostname + " " + page.cur.source_path],
                                       ["To", (page.cur.destinations || []).map(function (d) { return (d.destination_hostname || "storage") + " " + d.destination_path }).join("\n")],
                                       ["Along the way", page.steps.length ? page.steps.map(function (s) { return s.op }).join(", ") : "Copied as they are"]] : []
                    Item {
                        required property var modelData
                        width: parent.width; height: Math.max(30, v.implicitHeight + 12)
                        Txt { width: 100; y: 6; text: modelData[0]; color: Theme.text3 }
                        Txt { id: v; x: 112; y: 6; width: parent.width - 112; text: modelData[1]; wrapMode: Text.WordWrap; elide: Text.ElideNone; mono: modelData[0] === "From" || modelData[0] === "To" }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    }
                }
            }
            Column {
                objectName: "flowRestricted"
                visible: page.consents.length > 0
                width: parent.width
                spacing: 8
                Txt { text: "RESTRICTED MATERIAL"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Txt { width: parent.width; text: "A flow carries nothing restricted unless the person who restricted it says so."; color: Theme.text3; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                Repeater {
                    model: page.consents
                    Row {
                        required property var modelData
                        objectName: "consent_" + modelData.id
                        width: parent.width
                        spacing: 10
                        Txt { width: parent.width - 100; anchors.verticalCenter: parent.verticalCenter; wrapMode: Text.WordWrap; elide: Text.ElideNone
                              text: modelData.name + " · " + (modelData.state === "asked" ? "waiting for the person who restricted it" : modelData.state === "granted" ? "allowed" + (modelData.expires_at ? " until " + Time.atDay(modelData.expires_at) : "")
                                                              : modelData.state === "declined" ? "declined" : "taken back") }
                        Btn { objectName: "takeBack_" + modelData.id; visible: modelData.state === "granted" && page.canDecide.indexOf(modelData.id) >= 0; small: true; danger: true; text: "Take back"; onClicked: page.takeBack(modelData) }
                    }
                }
            }
            Btn {
                objectName: "openInConsole"
                visible: page.cur !== null && Fleet.dept(page.deptOf(page.cur)) !== null && Fleet.dept(page.deptOf(page.cur)).admins.length > 0
                iconName: "login"
                text: page.cur && Fleet.dept(page.deptOf(page.cur)) && Fleet.dept(page.deptOf(page.cur)).admins.length ? "Open in " + Fleet.dept(page.deptOf(page.cur)).admins[0].name + "'s console →" : ""
                onClicked: { var a = Fleet.dept(page.deptOf(page.cur)).admins[0]; drawer.close(); Nav.enter(a, ["flows", String(page.cur.id)]) }
            }
        }
    }
}
