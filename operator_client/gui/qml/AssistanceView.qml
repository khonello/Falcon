import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// ASSISTANCE (board AS03), three columns:
//
//   left    who is asking for you (a ping is a warm banner that stays lit until you answer), then everyone you
//           have a channel with, by person: your turn / waiting for them / closed
//   middle  the chosen channel: one reply each, in turn; the Listeners YOU added (never the other side's), and
//           only the superior closes it
//   right   find a file, the results grouped by where they sit -- only what you may see is ever shown
//
// Names and hostnames come from hierarchy.tree, which already speaks in the requester's own Display Names.
Item {
    id: root

    property var pings: []
    property var channels: []
    property var tree: []
    property int chosenId: 0
    property var channel: null
    property var messages: []
    property var listeners: []
    property var results: []
    property string query: ""
    property string clock: ""

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("assistance.ping_status", {}, function (ok, r) { if (ok) root.pings = r.pings })
        falcon.call("assistance.channels", {}, function (ok, r) {
            if (!ok) return
            root.channels = r.channels
            if (!root.chosenId && r.channels.length) root.choose(r.channels[0].id)
            else if (root.chosenId) root.load()
        })
        falcon.call("hierarchy.tree", {}, function (ok, r) { if (ok) root.tree = r.departments })
    }
    // --- ASSISTED ACCESS (board T06) -- an Admin's only way to be helped by another department.
    // It is CONSENT, not eviction: nobody is forced out, no clock is imposed on the helper, and what
    // they may do is said in words before either side agrees. The Engine owns the ceiling; the page
    // reads the scope it is given and may only narrow it. Admin-only, by the handlers' own roles.
    property bool available: false
    property var offers: []                 // offers made TO me, from the pushes
    property var askAnswer: null            // what my own last ask came back with
    property var helpSession: null          // the assistance running now, either side of it
    property int askDept: 0                 // which department to ask, 0 = anyone

    readonly property bool isAdmin: falcon && falcon.role === "admin"
    readonly property var otherDepts: {
        var mine = falcon ? falcon.departmentId : 0
        return (tree || []).filter(function (d) { return d.department_id !== mine })
    }
    function scopeWords(scope) {
        if (!scope) return "run control actions"
        var yes = []
        if (scope.control_actions) yes.push("control actions")
        if (scope.monitoring_actions) yes.push("monitoring checks")
        if (scope.custom_actions) yes.push("your own scripts")
        if (scope.tasks) yes.push("your tasks")
        if (scope.flows) yes.push("your flows")
        return yes.length === 0 ? "nothing yet" : yes.join(", ")
    }
    readonly property var helpSays: falcon.narrate("helping", {
        available: root.available,
        offers: root.offers.map(function (o) {
            return { requester_name: o.requester_name, allowed: root.scopeWords(o.scope) } }),
        answer: root.askAnswer,
        session: root.helpSession ? { with_name: root.helpSession.with_name,
                                      allowed: root.scopeWords(root.helpSession.scope) } : null })

    function setAvailable(on) {
        falcon.call("assisted_access.set_available", { available: on }, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            root.available = r.available
            shell.notify(r.available ? "Other departments can ask you now" : "You are not available", false)
        })
    }
    function askForHelp() {
        var payload = root.askDept ? { department_id: root.askDept } : {}
        falcon.call("assisted_access.request", payload, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            root.askAnswer = r
            shell.notify(r.matched ? r.helper_name + " was asked" : "Nobody is free right now", !r.matched)
        })
    }
    function acceptOffer(o) {
        shell.ask({ title: "Help " + (o.requester_name || "them") + "?",
                    lead: "You will be working on their machine, with their agreement.",
                    body: "You may " + root.scopeWords(o.scope) + ". Either of you can end it.",
                    act: "Help them", actIcon: "assistance", cancel: "Not now" }, function () {
            falcon.call("assisted_access.accept", { request_id: o.request_id }, function (ok, r) {
                if (!ok) { shell.notify(r.message, true); return }
                root.offers = root.offers.filter(function (x) { return x.request_id !== o.request_id })
                root.helpSession = { request_id: o.request_id, with_name: o.requester_name, scope: o.scope }
                shell.notify("You are helping " + (o.requester_name || "them"), false)
            })
        })
    }
    function declineOffer(o) {
        falcon.call("assisted_access.decline", { request_id: o.request_id }, function (ok, r) {
            root.offers = root.offers.filter(function (x) { return x.request_id !== o.request_id })
            shell.notify(ok ? "You said no" : r.message, !ok)
        })
    }
    function closeHelp() {
        if (!root.helpSession) return
        falcon.call("assisted_access.close", { request_id: root.helpSession.request_id }, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            root.helpSession = null
            root.askAnswer = null
            shell.notify("The help has ended", false)
        })
    }

    function choose(id) { chosenId = id; channel = null; messages = []; listeners = []; load() }
    function load() {
        if (!chosenId) return
        var id = chosenId
        falcon.call("assistance.channel", { channel_id: id }, function (ok, r) {
            if (!ok || id !== root.chosenId) return
            root.channel = r.channel
            root.messages = r.messages
        })
        falcon.call("assistance.my_listeners", { channel_id: id }, function (ok, r) { if (ok && id === root.chosenId) root.listeners = r.listeners })
    }
    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onScopeChanged() { if (falcon.isConnected) root.refresh() }
        function onPushReceived(type, p) {
            if (type.indexOf("assistance.") === 0) root.refresh()
            else if (type === "assisted_access.offer") root.offers = root.offers.concat([p])
            else if (type === "assisted_access.declined") {
                root.askAnswer = { matched: false }
                root.offers = root.offers.filter(function (x) { return x.request_id !== p.request_id })
            } else if (type === "assisted_access.closed") {
                root.helpSession = null
                root.askAnswer = null
                root.offers = root.offers.filter(function (x) { return x.request_id !== p.request_id })
            }
        }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    // --- people -------------------------------------------------------------------------------------------
    readonly property int me: falcon ? falcon.accountId : 0
    function person(accountId) {
        for (var i = 0; i < tree.length; i++) {
            var all = tree[i].admins.concat(tree[i].workers)
            for (var j = 0; j < all.length; j++) if (all[j].account_id === accountId) return all[j]
        }
        return null
    }
    // an Admin's tree holds their department, not the Super User above them: that one is named by role
    function nameOf(id, fallback) {
        var p = person(id)
        if (p) return p.name
        if (fallback) return fallback
        return falcon && falcon.role === "admin" && channels.some(function (c) { return c.superior_account_id === id }) ? "the Super User" : "Someone"
    }
    function initialsOf(id) { var n = nameOf(id); return n === "the Super User" ? "SU" : Theme.initials(n) }
    function hostOf(id) { var p = person(id); return p && p.hostname ? p.hostname : "" }
    function hostOfPc(pcId) {
        for (var i = 0; i < tree.length; i++) {
            var all = tree[i].admins.concat(tree[i].workers)
            for (var j = 0; j < all.length; j++) if (all[j].pc_id === pcId) return all[j].hostname
        }
        return ""
    }
    function otherOf(c) { return c.superior_account_id === me ? c.initiator_account_id : c.superior_account_id }
    function myTurn(c) {
        if (c.closed_at) return false
        return (c.turn === "superior") === (c.superior_account_id === me)
    }
    function timeOf(iso) { return iso ? Qt.formatDateTime(new Date(iso), "HH:mm") : "" }
    function whenOf(iso) {
        if (!iso) return ""
        var d = new Date(iso), now = new Date()
        return d.toDateString() === now.toDateString() ? (d.getHours() < 12 ? "this morning" : "today at " + timeOf(iso))
                                                       : Qt.formatDateTime(d, "ddd d MMM")
    }
    function stateOf(c) {
        var who = nameOf(otherOf(c))
        return c.closed_at ? "closed " + whenOf(c.closed_at) : myTurn(c) ? "your turn to reply" : "waiting for " + who
    }
    // pings grouped by who sent them: "Kojo is asking for you", twice
    readonly property var asking: {
        var by = {}, order = []
        for (var i = 0; i < pings.length; i++) {
            var p = pings[i]
            if (!by[p.sender_account_id]) { by[p.sender_account_id] = { sender: p.sender_account_id, name: p.from_name, pings: [] }; order.push(p.sender_account_id) }
            by[p.sender_account_id].pings.push(p)
        }
        return order.map(function (k) { return by[k] })
    }
    readonly property var sorted: channels.slice().sort(function (a, b) {
        var ra = a.closed_at ? 2 : root.myTurn(a) ? 0 : 1, rb = b.closed_at ? 2 : root.myTurn(b) ? 0 : 1
        return ra !== rb ? ra - rb : String(b.opened_at).localeCompare(String(a.opened_at))
    })
    readonly property var admins: {
        var out = []
        for (var i = 0; i < tree.length; i++)
            for (var j = 0; j < tree[i].admins.length; j++) {
                var a = tree[i].admins[j]
                if (a.account_id !== me && channel && a.account_id !== channel.initiator_account_id && a.account_id !== channel.superior_account_id)
                    out.push({ account_id: a.account_id, name: a.name, dept: tree[i].name })
            }
        return out
    }
    function answer(group) {
        falcon.call("assistance.respond", { ping_id: group.pings[0].id }, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            root.chosenId = r.channel_id
            root.refresh()
        })
    }
    function send(text) {
        if (!text.trim() || !channel) return
        falcon.call("assistance.message", { channel_id: channel.id, body: text.trim() }, function (ok, r) {
            if (!ok) { shell.notify(r.message, true); return }
            reply.text = ""
            root.refresh()
        })
    }
    function search(text) {
        query = text
        if (text.trim().length < 2) { results = []; return }
        falcon.call("assistance.search", { query: text.trim() }, function (ok, r) { if (ok && text === root.query) root.results = r.results })
    }
    // search results grouped by where they sit, in the order a person would look
    readonly property var groups: {
        var order = [["common", "Common — everyone", "ok"], ["worker_dept", tree.length === 1 ? tree[0].name + " — your department" : "Your department", "accent"],
                     ["restricted", "Restricted", "danger"], ["admin", "Admin", "warn"], ["", "On the machines", ""]]
        var out = []
        for (var i = 0; i < order.length; i++) {
            var key = order[i][0]
            var items = results.filter(function (f) { return (f.resource_tag || "") === key })
            if (items.length) out.push({ title: order[i][1], tone: order[i][2], items: items })
        }
        return out
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 22
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 16

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Column {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4
                Txt { text: "Assistance"; color: "#ffffff"; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                Row {
                    spacing: 12
                    Txt { text: "Assistance"; color: "#ffffff"; font.pixelSize: Theme.fTitle; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                    Txt { anchors.verticalCenter: parent.verticalCenter; font.pixelSize: Theme.fBody
                          color: root.asking.length ? Theme.warn : Qt.rgba(1, 1, 1, 0.55)
                          text: root.asking.length === 0 ? "no one is asking for you"
                                : root.asking.length === 1 ? "one person asking for you" : root.asking.length + " people asking for you" }
                }
            }
            Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: root.clock
                  color: Qt.rgba(1, 1, 1, 0.45); font.pixelSize: Theme.fBody }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            // --- left: asking for you, then by person ---------------------------------------------------
            ColumnLayout {
                Layout.preferredWidth: 400
                Layout.maximumWidth: 400
                Layout.fillHeight: true
                spacing: 20
                GridCell {
                    objectName: "assistAsking"
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.max(150, 90 + Math.min(2, root.asking.length) * 126)
                    Layout.fillHeight: false
                    topAlign: true
                    title: "Asking for you"
                    narration: ({ brief: root.asking.length ? (root.asking.length === 1 ? "a ping" : root.asking.length + " pings") : "",
                                  tone: "warn", state: "ok" })
                    Column {
                        width: parent.width
                        spacing: 10
                        Txt { visible: root.asking.length === 0; text: "No one is asking for you."; color: Theme.faint; font.pixelSize: Theme.fBody }
                        Repeater {
                            model: root.asking.slice(0, 2)
                            delegate: Rectangle {
                                required property var modelData
                                width: parent.width; height: 114; radius: 14; color: Theme.warnSoft
                                Column {
                                    anchors.fill: parent; anchors.margins: 16; spacing: 8
                                    Row { spacing: 10
                                          Icon { name: "ping"; size: 17; color: Theme.warn; anchors.verticalCenter: parent.verticalCenter }
                                          Txt { text: (modelData.name || root.nameOf(modelData.sender)) + " is asking for you"; color: Theme.ink
                                                font.pixelSize: Theme.fSection; font.weight: Font.DemiBold } }
                                    Txt { width: parent.width; elide: Text.ElideRight; color: Theme.warn; font.pixelSize: Theme.fMeta
                                          text: (modelData.pings.length === 1 ? "Pinged at " + root.timeOf(modelData.pings[0].sent_at)
                                                 : "Pinged " + (modelData.pings.length === 2 ? "twice" : modelData.pings.length + " times") + " — "
                                                   + root.timeOf(modelData.pings[0].sent_at) + ", again at " + root.timeOf(modelData.pings[modelData.pings.length - 1].sent_at))
                                                + (root.hostOf(modelData.sender) ? " · " + root.hostOf(modelData.sender) : "") }
                                    Item { width: parent.width; height: 28
                                        TBtn { objectName: "answerPing"; tone: "warn"; small: true; text: "Answer " + (modelData.name || root.nameOf(modelData.sender)).split(" ")[0]
                                               onClicked: root.answer(modelData) }
                                        Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "stays lit until you answer"
                                              color: Theme.faint; font.pixelSize: Theme.fMeta } }
                                }
                            }
                        }
                        Txt { visible: root.asking.length > 2; text: "+ " + (root.asking.length - 2) + " more asking"; color: Theme.warn; font.pixelSize: Theme.fMeta }
                    }
                }
                GridCell {
                    objectName: "assistPeople"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    topAlign: true
                    title: "By person"
                    narration: ({ brief: root.channels.length + (root.channels.length === 1 ? " channel" : " channels"),
                                  state: root.channels.length ? "ok" : "empty", note: "No channels yet",
                                  sentence: "A channel opens when a ping is answered." })
                    PagedColumn {
                        id: peoplePager
                        width: parent.width
                        height: Math.max(140, peopleCell.room)
                        itemHeight: 60
                        model: root.sorted
                        attention: function (c) { return root.myTurn(c) ? root.nameOf(root.otherOf(c)) + " waits" : "" }
                        delegate: InfoCard {
                            initials: modelData ? root.initialsOf(root.otherOf(modelData)) : ""
                            title: modelData ? root.nameOf(root.otherOf(modelData)) : ""
                            line: modelData ? [root.hostOf(root.otherOf(modelData)), root.stateOf(modelData)].filter(function (x) { return !!x }).join(" · ") : ""
                            lineTone: modelData && root.myTurn(modelData) ? "accent" : ""
                            stateWord: modelData && root.myTurn(modelData) ? "your turn" : ""
                            stateTone: "accent"
                            selected: modelData && modelData.id === root.chosenId
                            onClicked: root.choose(modelData.id)
                        }
                    }
                    id: peopleCell
                }
            }

            // --- middle: the channel ---------------------------------------------------------------------
            GridCell {
                id: talkCell
                objectName: "assistChannel"
                Layout.fillWidth: true
                Layout.preferredWidth: 3
                Layout.fillHeight: true
                topAlign: true
                title: root.channel ? root.nameOf(root.otherOf(root.channel)) : "A channel"
                narration: ({ brief: !root.channel ? "" : root.channel.closed_at ? "closed" : root.channel.my_turn ? "your turn" : "their turn",
                              tone: root.channel && root.channel.my_turn ? "accent" : "", state: root.channel ? "ok" : "empty",
                              note: "No channel open", sentence: "Answer a ping, or pick someone on the left." })
                ColumnLayout {
                    visible: root.channel !== null
                    width: parent.width
                    height: talkCell.room
                    spacing: 10
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        Rectangle { id: av; width: 38; height: 38; radius: 10; color: Qt.rgba(1, 1, 1, 0.08); anchors.verticalCenter: parent.verticalCenter
                                    Txt { anchors.centerIn: parent; text: root.channel ? root.initialsOf(root.otherOf(root.channel)) : ""
                                          color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.Bold } }
                        Column {
                            anchors.left: av.right; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter
                            Txt { text: root.channel ? root.nameOf(root.otherOf(root.channel)) : ""; color: Theme.ink; font.pixelSize: Theme.fBody; font.weight: Font.DemiBold }
                            Txt { color: Theme.faint; font.pixelSize: Theme.fMeta
                                  text: root.channel ? [root.hostOf(root.otherOf(root.channel)), "opened " + root.timeOf(root.channel.opened_at)].filter(function (x) { return !!x }).join(" · ") : "" }
                        }
                        // the Listeners you added -- an eye on a soft pill; you alone see it
                        Row {
                            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                            spacing: 8
                            Repeater {
                                model: root.listeners
                                delegate: Rectangle {
                                    required property var modelData
                                    width: lt.implicitWidth + 40; height: 28; radius: 14
                                    gradient: Gradient { orientation: Gradient.Horizontal
                                                         GradientStop { position: 0; color: Qt.rgba(0.54, 0.65, 0.88, 0.22) }
                                                         GradientStop { position: 1; color: Qt.rgba(0.66, 0.52, 0.88, 0.22) } }
                                    Icon { x: 11; anchors.verticalCenter: parent.verticalCenter; name: "eye"; size: 13; color: Theme.accent }
                                    Txt { id: lt; x: 30; anchors.verticalCenter: parent.verticalCenter; text: (modelData.name || "An Admin") + " is listening"
                                          color: Theme.accent; font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
                                }
                            }
                            GBtn { visible: root.channel && !root.channel.closed_at && root.admins.length > 0; text: "Add a listener"; iconName: "eye"; small: true
                                   onClicked: listenMenu.open()
                                   Menu { id: listenMenu; y: parent.height + 4
                                          Repeater { model: root.admins
                                                     delegate: MenuItem { required property var modelData; text: modelData.name + "  ·  " + modelData.dept
                                                                          onTriggered: falcon.call("assistance.add_listener", { channel_id: root.channel.id, admin_account_id: modelData.account_id },
                                                                                                   function (ok, r) { shell.notify(ok ? modelData.name + " is listening" : r.message, !ok); root.load() }) } } } }
                        }
                    }
                    Txt { Layout.fillWidth: true; visible: root.listeners.length > 0; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta
                          text: "Only you see who you added. " + (root.channel ? root.nameOf(root.otherOf(root.channel)) : "They") + " is not told; the audit trail records it." }
                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
                    ListView {
                        id: talk
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 12
                        model: root.messages
                        onCountChanged: positionViewAtEnd()
                        delegate: Item {
                            required property var modelData
                            readonly property bool mine: modelData.sender_account_id === root.me
                            width: talk.width
                            height: bubble.height
                            Rectangle {
                                id: bubble
                                x: parent.mine ? parent.width - width : 0
                                width: Math.min(talk.width * 0.62, body.implicitWidth + 28)
                                height: body.implicitHeight + meta.implicitHeight + 24
                                radius: 12
                                color: parent.mine ? Theme.accentSoft : "transparent"
                                Txt { id: body; x: 14; y: 10; width: Math.min(talk.width * 0.62 - 28, implicitWidth); wrapMode: Text.WordWrap
                                      text: modelData.body; color: Theme.ink; font.pixelSize: Theme.fBody }
                                Txt { id: meta; x: 14; anchors.top: body.bottom; anchors.topMargin: 4; color: Theme.faint; font.pixelSize: Theme.fMeta - 1
                                      text: (parent.parent.mine ? "you" : root.nameOf(modelData.sender_account_id)) + " · " + root.timeOf(modelData.sent_at) }
                            }
                        }
                    }
                    Field {
                        id: reply
                        objectName: "assistReply"
                        Layout.fillWidth: true
                        enabled: root.channel && root.channel.my_turn
                        placeholderText: !root.channel ? "" : root.channel.closed_at ? "This channel is closed."
                                         : root.channel.my_turn ? "Your turn — one reply, then " + root.nameOf(root.otherOf(root.channel)).split(" ")[0] + "'s"
                                         : "Waiting for " + root.nameOf(root.otherOf(root.channel)).split(" ")[0] + " to reply"
                        onAccepted: root.send(text)
                    }
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        GBtn { visible: root.channel && !root.channel.closed_at && root.channel.superior_account_id === root.me; text: "Close the channel"; small: true
                               anchors.verticalCenter: parent.verticalCenter
                               onClicked: falcon.call("assistance.close_channel", { channel_id: root.channel.id }, function (ok, r) {
                                   shell.notify(ok ? "Closed" : r.message, !ok); root.refresh() }) }
                        Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; color: Theme.faint; font.pixelSize: Theme.fMeta
                              text: !root.channel || root.channel.closed_at ? "" : root.channel.superior_account_id === root.me ? "only you can close it"
                                    : "only " + root.nameOf(root.channel.superior_account_id) + " can close it" }
                    }
                }
            }

            // --- right: help from another department, then find a file ------------------------------------
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 2
                Layout.fillHeight: true
                spacing: 20

            // Assisted access is an Admin's affair: a Super User traverses instead, and every one of
            // these handlers refuses anyone else. So the cell is simply not there for them.
            GridCell {
                id: helpCell
                objectName: "assistHelp"
                visible: root.isAdmin
                Layout.fillWidth: true
                Layout.fillHeight: false
                Layout.preferredHeight: root.isAdmin ? Math.max(250, root.height * 0.42) : 0
                topAlign: true
                title: "Help from another department"
                narration: root.helpSays

                Column {
                    width: parent.width
                    spacing: 12

                    // --- an offer made to you: who, what they would let you do, and the two answers
                    Repeater {
                        model: root.offers
                        delegate: Rectangle {
                            required property var modelData
                            width: parent.width
                            height: 112
                            radius: 14
                            color: Theme.accentSoft
                            Column {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8
                                Row {
                                    spacing: 10
                                    Icon { name: "assistance"; size: 17; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter }
                                    Txt { text: (modelData.requester_name || "An Admin") + " needs help"
                                          color: Theme.ink; font.pixelSize: Theme.fSection; font.weight: Font.DemiBold }
                                }
                                Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.accent; font.pixelSize: Theme.fMeta
                                      text: "They would let you " + root.scopeWords(modelData.scope) + " on their machine." }
                                Row {
                                    spacing: 8
                                    TBtn { objectName: "acceptHelp"; text: "Help them"; tone: "accent"; small: true
                                           onClicked: root.acceptOffer(modelData) }
                                    GBtn { text: "Not now"; small: true; onClicked: root.declineOffer(modelData) }
                                }
                            }
                        }
                    }

                    // --- the help running now, either side of it. No clock: it ends by consent
                    Rectangle {
                        visible: root.helpSession !== null
                        width: parent.width
                        height: 92
                        radius: 14
                        color: Theme.pane
                        Column {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 6
                            Txt { text: "Helping " + (root.helpSession ? (root.helpSession.with_name || "them") : "")
                                  color: Theme.ink; font.pixelSize: Theme.fRow; font.weight: Font.DemiBold }
                            Txt { width: parent.width; wrapMode: Text.WordWrap; color: Theme.faint; font.pixelSize: Theme.fMeta
                                  text: "You may " + root.scopeWords(root.helpSession ? root.helpSession.scope : null)
                                        + ". It ends when either of you closes it." }
                            GBtn { objectName: "endHelp"; text: "End it"; iconName: "stop"; small: true; onClicked: root.closeHelp() }
                        }
                    }

                    // --- asking for yourself: who to ask, said as words, then the one act
                    Column {
                        visible: root.offers.length === 0 && root.helpSession === null
                        width: parent.width
                        spacing: 10

                        ReadingBody {
                            width: parent.width
                            narration: root.helpSays
                            maxFacts: 2
                            showAction: false
                        }
                        Row {
                            spacing: 8
                            Txt { text: "Ask"; color: Theme.dim; font.pixelSize: Theme.fBody
                                  height: 30; verticalAlignment: Text.AlignVCenter }
                            SentenceSlot {
                                objectName: "askWho"
                                text: {
                                    for (var i = 0; i < root.otherDepts.length; i++)
                                        if (root.otherDepts[i].department_id === root.askDept) return root.otherDepts[i].name
                                    return "anyone free"
                                }
                                onClicked: whoMenu.open()
                                Menu {
                                    id: whoMenu
                                    y: parent.height + 4
                                    MenuItem { text: "anyone free"; onTriggered: root.askDept = 0 }
                                    Repeater {
                                        model: root.otherDepts
                                        delegate: MenuItem {
                                            required property var modelData
                                            text: modelData.name
                                            onTriggered: root.askDept = modelData.department_id
                                        }
                                    }
                                }
                            }
                            TBtn { objectName: "askForHelp"; text: "Ask for help"; iconName: "assistance"; small: true
                                   anchors.verticalCenter: parent.verticalCenter
                                   onClicked: root.askForHelp() }
                        }
                        Rectangle { width: parent.width; height: 1; color: Theme.line }
                        Row {
                            spacing: 14
                            Txt { text: "You are"; color: Theme.faint; font.pixelSize: Theme.fMeta
                                  height: 22; verticalAlignment: Text.AlignVCenter }
                            // choosing between two states is plain words, never a lineup of pills (PATTERNS 10)
                            Txt {
                                objectName: "availableOn"
                                text: "available to help"
                                color: root.available ? Theme.ok : Theme.faint
                                font.pixelSize: Theme.fMeta
                                font.weight: root.available ? Font.DemiBold : Font.Normal
                                height: 22; verticalAlignment: Text.AlignVCenter
                                MouseArea { anchors.fill: parent; anchors.margins: -4; cursorShape: Qt.PointingHandCursor
                                            onClicked: root.setAvailable(true) }
                            }
                            Txt {
                                objectName: "availableOff"
                                text: "not available"
                                color: root.available ? Theme.faint : Theme.ink
                                font.pixelSize: Theme.fMeta
                                font.weight: root.available ? Font.Normal : Font.DemiBold
                                height: 22; verticalAlignment: Text.AlignVCenter
                                MouseArea { anchors.fill: parent; anchors.margins: -4; cursorShape: Qt.PointingHandCursor
                                            onClicked: root.setAvailable(false) }
                            }
                        }
                    }
                }
            }

            GridCell {
                objectName: "assistFind"
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "Find a file"
                narration: ({ brief: "grouped by where", state: "ok" })
                Column {
                    width: parent.width
                    spacing: 10
                    Field { objectName: "assistSearch"; width: parent.width; placeholderText: "a few letters of its name"; onTextEdited: root.search(text) }
                    Repeater {
                        model: root.groups
                        delegate: Column {
                            required property var modelData
                            width: parent.width
                            spacing: 8
                            Txt { topPadding: 4; text: modelData.title; color: modelData.tone ? Theme.tone(modelData.tone) : Theme.dim
                                  font.pixelSize: Theme.fMeta; font.weight: Font.DemiBold }
                            Repeater {
                                model: modelData.items.slice(0, 4)
                                delegate: InfoCard {
                                    required property var modelData
                                    width: parent.width
                                    iconName: "file"; iconTone: "ok"
                                    title: modelData.filename
                                    line: [root.hostOfPc(modelData.pc_id), "in " + Automate.folderName(String(modelData.path).replace(/[\\/][^\\/]*$/, ""))]
                                          .filter(function (x) { return !!x }).join(" · ")
                                }
                            }
                        }
                    }
                    Txt { visible: root.query.length >= 2 && root.results.length === 0; text: "Nothing by that name you may see."
                          color: Theme.faint; font.pixelSize: Theme.fBody }
                    Txt { text: "Only what you may see is ever shown."; color: Theme.faint; font.pixelSize: Theme.fMeta }
                }
            }
            }
        }
    }
}
