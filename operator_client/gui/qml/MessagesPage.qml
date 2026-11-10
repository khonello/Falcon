import QtQuick
import QtQuick.Dialogs
import "."

// MESSAGES, as the version 1 concept draws it (docs/design/concepts-admin.html, AdminMessagesPage): the people an IT Admin talks to, the
// other Admins and whoever is signed in on a machine, one at a time or as the group of every Admin. The situation in a sentence; the
// conversations on the left (requests to talk first, then unread, then the rest); the one picked on the right with its thread and the
// box to write in; starting a conversation at the foot. On the Engine's version 1 conversations (`chat.*`, engine/resource/conversations.py).
// A person at a machine answers in a conversation an Admin started; a request to talk from them (the user, 2 Nov 2026) is listed first
// once the Engine keeps those (ENGINE-GAPS #19).
Page {
    id: page
    objectName: "messagesView"

    property var convs: []
    property var people: []
    property bool adminsGroup: false
    property var thread: null             // chat.get for the one picked
    property var requests: []             // requests to talk (chat.requests; ENGINE-GAPS #19: the section stays away until the Engine keeps them)
    property var flows: []                // what is open between you and someone, said above the conversation
    property var tasks: []
    property string reqWhy: ""
    property var many: []                 // who a new conversation is with
    property string sel: { var a = Nav.takeArrive("messages"); return a !== null ? String(a) : Nav.sub ? String(Nav.sub) : "" }
    property var drafts: ({})
    property string q: ""
    property string mtxt: ""
    readonly property int me: falcon.accountId

    function load() {
        falcon.call("chat.list", {}, function (ok, r) { page.convs = ok ? (r.conversations || []) : []; page.loadThread() })
        falcon.call("chat.people", {}, function (ok, r) { page.people = ok ? (r.people || []) : []; page.adminsGroup = ok && !!r.admins_group })
        falcon.call("chat.requests", {}, function (ok, r) { page.requests = ok ? (r.requests || []) : [] })
        falcon.call("flow.list", {}, function (ok, r) { page.flows = ok ? (r.flows || []) : [] })
        falcon.call("task.list", {}, function (ok, r) { page.tasks = ok ? (r.tasks || []) : [] })
    }
    function loadThread() {
        if (!c) { thread = null; return }
        var id = c.conversation_id
        falcon.call("chat.get", { conversation_id: id }, function (ok, r) { if (ok && page.c && page.c.conversation_id === id) page.thread = r })
        if (c.unread) falcon.call("chat.read", { conversation_id: id }, function () {})
    }
    Component.onCompleted: load()
    Connections { target: falcon; function onConnected() { page.load() } function onPushReceived(type, payload) { if (/^chat/.test(type)) again.restart() } }
    Timer { id: again; interval: 300; onTriggered: page.load() }

    // every conversation, as the Engine lists it, latest first; unread is the Engine's count
    readonly property var rows: convs.map(function (x) {
        return { id: String(x.conversation_id), conversation_id: x.conversation_id, kind: x.kind, title: x.title || "Someone", other: x.title || "Someone",
                 members: x.members || [], unread: x.unread || 0, last: x.last ? Time.ms(x.last.at) : 0,
                 line: x.last ? (x.last.from_account_id === page.me ? "You: " : x.kind === "admins" ? (x.last.from || "") + ": " : "") + x.last.body : "nothing said yet",
                 st: [x.unread ? "Waiting on you" : "Read", x.unread ? "bad" : "wait", x.unread ? "you" : "read"] }
    })
    // a request is picked first, as the concept opens on it; else the conversation picked, else the first
    readonly property var curReq: { for (var i = 0; i < requests.length; i++) if ("r" + requests[i].id === sel) return requests[i]; return sel === "" && requests.length ? requests[0] : null }
    readonly property var c: { if (curReq) return null; for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; return rows.length ? rows[0] : null }
    function ago(ms) { var h = (Time.now - ms) / 3600000; return h < 24 ? Time.dur(h) + " ago" : Time.dayName(ms) + " " + Time.hhmm(ms) }
    function others(x) { return (x.members || []).filter(function (m) { return m.account_id !== page.me }) }
    // what is open between you and someone: chips under their name (amBetween)
    function between(x) {
        if (!x) return []
        if (x.kind === "admins") return [[page.others(x).length + " Admins and you", "quiet"]]
        var o = page.personOf(x)
        if (o && o.role === "admin") {
            var w = flows.filter(function (f) { return f.consent_status === "pending" && (f.destinations || []).some(function (d) { return d.let_them_choose && d.owner_account_id === o.account_id }) }).length
            return [w ? [Theme.fmt(w) + " flow" + (w === 1 ? "" : "s") + " waiting for them to pick a folder", ""] : ["No flow waits on them", "quiet"]]
        }
        var open = tasks.filter(function (k) { return o && k.assignee_account_id === o.account_id && k.status !== "completed" }), late = open.filter(function (k) { return k.final_deadline_at && Time.ms(k.final_deadline_at) < Time.now })
        return [open.length ? [Theme.fmt(open.length) + " task" + (open.length === 1 ? "" : "s") + " with them", ""] : ["No task with them", "quiet"]].concat(late.length ? [[Theme.fmt(late.length) + " late", "hot"]] : [])
    }
    function acceptReq(r) { falcon.call("chat.request_accept", { request_id: r.id }, function (ok, x) { if (!ok) { Msg.failed(x && x.message ? x.message : "Not accepted"); return }
                                                                                                        Msg.ok("Accepted · the conversation with " + r.from + " is open"); page.sel = x.conversation ? String(x.conversation.conversation_id) : ""; page.load() }) }
    function closeReq(r) { falcon.call("chat.request_close", { request_id: r.id, why: reqWhy.trim() }, function (ok, x) { if (!ok) { Msg.failed(x && x.message ? x.message : "Not closed"); return }
                                                                                                                         Msg.ok("Closed · " + r.from + " is told: " + page.reqWhy.trim()); page.reqWhy = ""; page.sel = ""; page.load() }) }
    onCChanged: { thread = null; loadThread(); pickedId = c ? c.id : "" }
    property string pickedId: ""
    readonly property string draft: c ? (drafts[c.id] || "") : ""
    function setDraft(t) { var d = Object.assign({}, drafts); d[c.id] = t; drafts = d }
    // one file from this machine, sent once (chat.send_file): it arrives as a card they can save
    property string filePath: ""
    property string fileWhy: ""
    property bool fileBusy: false
    function sendTheFile() {
        if (!page.c || !filePath || fileBusy) return
        fileBusy = true
        var to = page.c.kind === "admins" ? "every Admin" : page.c.title
        falcon.call("chat.send_file", { conversation_id: page.c.conversation_id, path: filePath }, function (ok, r) {
            page.fileBusy = false
            if (!ok) { page.fileWhy = r && r.message ? r.message.charAt(0).toUpperCase() + r.message.slice(1) + "." : "It was not sent."; return }
            sendFile.close()
            if (r.state === "asked") Msg.ok("Waiting for " + (r.waits_for || "an IT Admin") + " to agree; " + to + " gets it then")
            else Msg.ok("Sent to " + to)
            page.load()
        })
    }
    FileDialog { id: pickFile; title: "A file on this machine"; onAccepted: { page.filePath = decodeURIComponent(String(selectedFile).replace(/^file:\/{3}/, "")); page.fileWhy = "" } }
    Modal {
        id: sendFile
        objectName: "sendFileModal"
        page: page
        title: page.c ? "Send a file to " + (page.c.kind === "admins" ? "every Admin" : page.c.title) : "Send a file"
        Column {
            width: sendFile.width - 2 * sendFile.pad
            spacing: 10
            bottomPadding: 6
            Row { width: parent.width; spacing: 8
                Field { width: parent.width - chooseB.width - 8; readOnly: true; text: page.filePath; placeholderText: "A file on your machine" }
                Btn { id: chooseB; text: "Choose…"; onClicked: pickFile.open() } }
            Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 13
                  text: "One file, sent once, up to 100 MB. It arrives as a card they can save. A restricted file waits for whoever restricted it to agree." }
            Decide { visible: page.fileWhy !== ""; c: Theme.crit; text: page.fileWhy }
        }
        footer: Row { spacing: 8
            Btn { text: "Cancel"; onClicked: sendFile.close() }
            Btn { objectName: "sendFileGo"; kind: "primary"; text: "Send it"; loading: page.fileBusy; enabled: page.filePath !== "" && !page.fileBusy; onClicked: page.sendTheFile() } }
    }
    function send() {
        var x = c, text = draft.trim()
        if (!text) return
        falcon.call("chat.send", { conversation_id: x.conversation_id, body: text }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not sent"); return }
            var d = Object.assign({}, page.drafts); d[x.id] = ""; page.drafts = d
            Msg.ok("Sent to " + x.title); page.load()
        })
    }
    function personOf(x) {
        if (!x || x.kind === "admins") return null
        var o = (x.members || []).filter(function (m) { return m.account_id !== page.me })[0]
        return o ? page.people.filter(function (p) { return p.account_id === o.account_id })[0] || null : null
    }
    function match(x) { return (x.title + " " + x.line).toLowerCase().indexOf(q.toLowerCase()) >= 0 }
    readonly property var unread: rows.filter(function (x) { return x.unread && page.match(x) })
    readonly property var read: rows.filter(function (x) { return !x.unread && page.match(x) })

    // starting a conversation: one person goes to your conversation with them; every Admin goes to their group, as several would, once the Engine keeps small groups
    readonly property var whoOptions: (adminsGroup ? [{ value: "admins", label: "Every Admin" }] : [])
        .concat(people.filter(function (p) { return p.role === "admin" }).map(function (p) { return { value: "a" + p.account_id, label: p.name } }))
        .concat(people.filter(function (p) { return p.role !== "admin" }).map(function (p) { return { value: "p" + p.pc_id, label: (p.name || "nobody signed in") + " · " + p.hostname + (p.online ? "" : " · offline") } }))
    readonly property bool several: many.length > 1 && many.indexOf("admins") < 0
    function startOne() {
        var w = String(many[0]), pl = w === "admins" ? { admins: true } : w.charAt(0) === "a" ? { account_id: Number(w.slice(1)) } : { pc_id: Number(w.slice(1)) }, text = mtxt.trim()
        falcon.call("chat.open", pl, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not opened"); return }
            var id = r.conversation.conversation_id
            page.sel = String(id)
            falcon.call("chat.send", { conversation_id: id, body: text }, function (ok2, r2) {
                if (!ok2) Msg.failed(r2 && r2.message ? r2.message : "Opened, but not sent"); else Msg.ok("Sent to " + (r.conversation.title || "them"))
                page.many = []; page.mtxt = ""; page.load()
            })
        })
    }

    situation: {
        if (!rows.length && !requests.length) return "No conversations yet. Start one below."
        var oldest = rows.filter(function (x) { return !x.unread && x.line.indexOf("You: ") === 0 }).sort(function (a, b) { return a.last - b.last })[0]
        return (requests.length ? (requests.length === 1 ? requests[0].from + " on " + requests[0].host + " asks" : Theme.fmt(requests.length) + " people at machines ask") + " to talk; every Admin sees " + (requests.length === 1 ? "it" : "them") + " until one accepts. " : "")
               + (unread.length ? Theme.listNames(unread.map(function (x) { return x.kind === "admins" ? "the Admins group" : x.title }), 2) + (unread.length === 1 ? " is" : " are") + " waiting on your answer." : "Nobody is waiting on you.")
               + (oldest ? " Your message to " + oldest.title + " has waited " + Time.span((Time.now - oldest.last) / 3600000) + "." : "")
    }
    situationAt: Time.now

    Confirm { id: confirm; page: page }

    function initials(n) { return String(n || "?").split(/[ .]+/).filter(function (x) { return x }).map(function (x) { return x[0] }).join("").slice(0, 2) }
    // a person as a round face (ib-av): their initials on surface-3; a group as two small ones (ms-stack), the second behind
    component Face: Item {
        property string name: ""
        property var group: null
        property real size: 36
        width: size; height: size
        Rectangle {
            visible: parent.group === null
            anchors.fill: parent; radius: width / 2; color: Theme.surface3
            Txt { anchors.centerIn: parent; text: page.initials(parent.parent.name); font.pixelSize: parent.width > 40 ? 14 : 12; font.weight: Font.DemiBold; color: Theme.text2; elide: Text.ElideNone }
        }
        Repeater {
            model: parent.group === null ? [] : [1, 0]
            Rectangle {
                required property int modelData
                readonly property real d: parent.size > 40 ? 29 : 22
                x: modelData ? parent.size - d : 0; y: modelData ? parent.size - d : 0
                width: d; height: d; radius: d / 2
                color: modelData ? Theme.surface2 : Theme.surface3
                border.width: 2; border.color: Theme.surface
                Txt { anchors.centerIn: parent; text: (parent.parent.group[parent.modelData] ? page.initials(parent.parent.group[parent.modelData].name) : ""); font.pixelSize: parent.d > 25 ? 10 : 9; font.weight: Font.DemiBold; color: Theme.text2; elide: Text.ElideNone }
            }
        }
    }
    component Section: Column {
        id: sec
        property string name: ""
        property string note: ""
        property var xs: []
        visible: xs.length > 0
        width: parent.width
        spacing: 0
        Item {
            width: parent.width
            height: sh.height + 14
            Txt { id: sh; x: 4; y: 10; text: sec.name; font.pixelSize: 12; font.weight: Font.DemiBold; color: Theme.text2; elide: Text.ElideNone }
            Txt { x: sh.x + sh.implicitWidth + 8; y: 10; text: Theme.fmt(sec.xs.length) + (sec.note ? " · " + sec.note : ""); color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
        }
        Repeater {
            model: sec.xs
            delegate: Rectangle {
                required property var modelData
                readonly property bool isReq: modelData.from !== undefined
                readonly property bool on: isReq ? page.curReq !== null && page.curReq.id === modelData.id : page.c !== null && page.c.id === modelData.id
                objectName: "conv_" + (isReq ? "r" : "") + modelData.id
                width: sec.width; height: Math.max(36, pt.height) + 16; radius: Theme.radiusLg
                color: on ? Theme.accentSoft : ma.containsMouse ? Theme.surface2 : "transparent"
                Face { x: 8; anchors.verticalCenter: parent.verticalCenter; name: parent.isReq ? modelData.from : modelData.title; group: !parent.isReq && modelData.kind === "admins" ? page.others(modelData) : null }
                Column {
                    id: pt
                    x: 54; y: 8; width: parent.width - 62
                    anchors.verticalCenter: parent.verticalCenter
                    Item { width: parent.width; height: nm.height
                        Txt { id: nm; textFormat: Text.StyledText; font.weight: Font.DemiBold; width: Math.min(implicitWidth, parent.width - tm.implicitWidth - 8)
                              text: parent.parent.parent.isReq ? modelData.from + " <font color='" + Theme.text3 + "'><span style='font-weight:400'>· " + modelData.host + "</span></font>" : modelData.title }
                        Txt { visible: !parent.parent.parent.isReq && modelData.kind === "admins"; x: nm.width + 6; y: nm.baselineOffset - baselineOffset; text: page.others(modelData).length; color: Theme.text3; font.pixelSize: 11; font.weight: Font.Medium; elide: Text.ElideNone }
                        Txt { id: tm; anchors.right: parent.right; y: nm.baselineOffset - baselineOffset; text: parent.parent.parent.isReq ? page.ago(Time.ms(modelData.at)) : modelData.last ? page.ago(modelData.last) : ""; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                    }
                    Item { width: parent.width; height: 18.75
                        Rectangle { id: rq; visible: parent.parent.parent.isReq; width: visible ? rqt.implicitWidth + 14 : 0; height: 18; radius: 9; color: Theme.accentSoft; anchors.verticalCenter: ln.verticalCenter
                                    Txt { id: rqt; anchors.centerIn: parent; text: "Request"; color: Theme.accent; font.pixelSize: 11; elide: Text.ElideNone } }
                        Txt { id: ln; x: rq.visible ? rq.width + 8 : 0; width: parent.width - x - (!parent.parent.parent.isReq && modelData.unread ? 28 : 0); text: modelData.line; font.pixelSize: 13
                              color: parent.parent.parent.isReq || modelData.unread ? Theme.text : Theme.text3; font.weight: parent.parent.parent.isReq || modelData.unread ? Font.Medium : Font.Normal }
                        Rectangle { visible: !parent.parent.parent.isReq && modelData.unread > 0; anchors.right: parent.right; anchors.verticalCenter: ln.verticalCenter; width: Math.max(20, cn.implicitWidth + 12); height: 20; radius: 10; color: Theme.accent
                                    Txt { id: cn; anchors.centerIn: parent; text: modelData.unread || ""; color: Theme.inverse; font.pixelSize: 11; font.weight: Font.DemiBold; elide: Text.ElideNone } }
                    }
                }
                MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.sel = (parent.isReq ? "r" : "") + modelData.id }
            }
        }
    }

    Row {
        width: parent.width
        spacing: 14
        readonly property real h: Math.max(listP.implicitHeight, conv.implicitHeight, 520 + 40)
        // --- conversations ---------------------------------------------------------------------------------------------------------------
        Box {
            id: listP
            objectName: "conversations"
            width: (parent.width - 14) * 4 / 12
            height: parent.h
            title: "Conversations"
            sub: "unread first"
            Field { width: parent.width; small: true; iconName: "search"; placeholderText: "Find a person or a group"; text: page.q; onTextEdited: page.q = text }
            Column {
                width: parent.width
                spacing: 2
                Section { name: "Requests to talk"; note: "any Admin may accept"; xs: page.requests }
                Section { name: "Unread"; xs: page.unread }
                Section { name: "Read"; xs: page.read }
                Quiet { visible: page.rows.length === 0; text: "No conversations yet. Start one below." }
            }
        }
        // --- the conversation picked ------------------------------------------------------------------------------------------------------
        Box {
            id: conv
            objectName: "conversation"
            width: (parent.width - 14) * 8 / 12
            height: parent.h
            fill: true
            readonly property var person: page.personOf(page.c)
            Quiet { visible: page.c === null && page.curReq === null; text: "Pick someone on the left." }
            // a request to talk: who, what they asked, accept it, or close it with a reason
            Column {
                visible: page.curReq !== null
                width: parent.width
                spacing: 0
                Item {
                    width: parent.width
                    height: 44 + 11
                    Face { size: 44; name: page.curReq ? page.curReq.from : "" }
                    Column { x: 54; width: parent.width - 54; spacing: 2
                             Txt { width: parent.width; text: page.curReq ? page.curReq.from + " asks to talk" : ""; font.pixelSize: 14; font.weight: Font.DemiBold; color: Theme.text3 }
                             Txt { width: parent.width; text: page.curReq ? "Signed in on " + page.curReq.host + " · sent " + page.ago(Time.ms(page.curReq.at)) + " · every Admin sees this request until one of you accepts it" : ""; font.pixelSize: 13; color: Theme.text3 } }
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
                }
                Column {
                    x: 20; topPadding: 18; bottomPadding: 18
                    width: parent.width - 40
                    spacing: 12
                    Rectangle { width: parent.width; height: rqq.height + 28; radius: 10; color: Theme.surface2; border.width: 1; border.color: Theme.border
                                Txt { id: rqq; x: 16; y: 14; width: parent.width - 32; text: page.curReq ? page.curReq.line : ""; font.pixelSize: 16; font.weight: Font.Medium; wrapMode: Text.WordWrap; elide: Text.ElideNone } }
                    Txt { width: parent.width; text: page.curReq ? "Accepting opens your conversation with " + page.curReq.from + ", with this line in it. The other Admins see that you accepted it." : ""; color: Theme.text3; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                    Btn { kind: "primary"; text: "Accept and open the conversation"; onClicked: page.acceptReq(page.curReq) }
                    Item { width: 1; height: 0.1 }
                    Rectangle { width: parent.width; height: 1; color: Theme.border }
                    Column { width: parent.width; spacing: 6
                             Txt { text: "Or close it"; font.weight: Font.DemiBold; elide: Text.ElideNone }
                             Txt { width: parent.width; text: page.curReq ? page.curReq.from + " is told it was closed, with your reason. They can ask again." : ""; color: Theme.text3; wrapMode: Text.WordWrap; elide: Text.ElideNone }
                             Row { width: parent.width; spacing: 8
                                   Field { width: parent.width - clB.width - 8; placeholderText: "Why, in a line they will read"; text: page.reqWhy; onTextEdited: page.reqWhy = text }
                                   Btn { id: clB; text: "Close the request"; enabled: page.reqWhy.trim() !== ""; onClicked: page.closeReq(page.curReq) } } }
                }
            }
            // the head (ms-head): their face, who and where, under a rule
            Item {
                visible: page.c !== null
                width: parent.width
                height: Math.max(44, hc.height) + 11
                Face { size: 44; name: page.c ? page.c.title : ""; group: page.c && page.c.kind === "admins" ? page.others(page.c) : null }
                Column {
                    id: hc
                    x: 56; width: parent.width - 56
                    spacing: 2
                    Txt { width: parent.width; text: page.c ? (page.c.kind === "admins" ? "Every Admin" : page.c.title) : ""; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Txt { width: parent.width; font.pixelSize: 13; color: Theme.text3; wrapMode: Text.WordWrap; elide: Text.ElideNone
                          text: !page.c ? "" : page.c.kind === "admins" ? "A group of " + page.others(page.c).length + " and you. Each of them sees what everyone writes."
                                : conv.person ? (conv.person.role === "admin" ? "Admin" : "Signed in on " + conv.person.hostname + (conv.person.online ? "" : " · offline")) : "" }
                    Row { spacing: 6; visible: page.c !== null
                          Repeater { model: page.between(page.c)
                                     Rectangle { required property var modelData; width: chT.implicitWidth + 16; height: 19; radius: 10; color: modelData[1] === "quiet" ? "transparent" : modelData[1] === "hot" ? Theme.alpha(Theme.crit, 0.14) : Theme.surface3
                                                 border.width: modelData[1] === "quiet" ? 1 : 0; border.color: Theme.borderStrong
                                                 Txt { id: chT; anchors.centerIn: parent; text: modelData[0]; font.pixelSize: 12; color: modelData[1] === "quiet" ? Theme.text3 : modelData[1] === "hot" ? Theme.crit : Theme.text2; elide: Text.ElideNone } } } }
                }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
            }
            // the thread (ms-thread), newest at the foot
            Flickable {
                id: th
                visible: page.c !== null
                width: parent.width
                height: Math.max(80, conv.height - conv.headerHeight - 16 - 66 - wr.height - 20)
                contentHeight: msgs.height + 16
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                onContentHeightChanged: contentY = Math.max(0, contentHeight - height)
                Column {
                    id: msgs
                    x: 2; y: 8
                    width: th.width - 4
                    spacing: 8
                    Repeater {
                        model: page.thread ? page.thread.messages || [] : []
                        delegate: Column {
                            required property var modelData
                            required property int index
                            readonly property var prev: index > 0 ? page.thread.messages[index - 1] : null
                            readonly property bool newDay: !prev || !Time.sameDay(Time.ms(prev.at), Time.ms(modelData.at))
                            width: msgs.width
                            spacing: 8
                            Txt { visible: parent.newDay; anchors.horizontalCenter: parent.horizontalCenter; topPadding: 6; text: Time.sameDay(Time.ms(modelData.at), Time.now) ? "Today" : Time.dayName(modelData.at) + " " + Time.day(modelData.at); font.pixelSize: 12; color: Theme.text3; elide: Text.ElideNone }
                            Item {
                                width: parent.width
                                height: bub.height
                                Rectangle {
                                    id: bub
                                    readonly property bool mine: !!modelData.mine
                                    x: mine ? parent.width - width : 0
                                    width: Math.min(parent.width * 0.72, Math.max(bt.implicitWidth, bf.visible ? bf.implicitWidth : 0, bs.implicitWidth) + 24)
                                    height: bc.height + 16
                                    radius: 12
                                    bottomLeftRadius: mine ? 12 : 4
                                    bottomRightRadius: mine ? 4 : 12
                                    color: mine ? Theme.accent : Theme.surface2
                                    border.width: mine ? 0 : 1
                                    border.color: Theme.border
                                    Column {
                                        id: bc
                                        x: 12; y: 8
                                        width: parent.width - 24
                                        spacing: 4
                                        Txt { id: bf; visible: !bub.mine && page.c && page.c.kind === "admins"; text: modelData.from || ""; font.weight: Font.DemiBold; font.pixelSize: 12; color: Theme.text2; elide: Text.ElideNone }
                                        Txt { id: bt; width: parent.width; visible: text !== ""; text: modelData.body || ""; lh: 1.45; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: bub.mine ? Theme.inverse : Theme.text }
                                        // a file sent in the conversation (ms-file): its name, its size, and Save for the one it came to
                                        Rectangle {
                                            visible: !!modelData.file
                                            width: Math.min(parent.width, 300); height: 46; radius: 8
                                            color: bub.mine ? Theme.alpha(Theme.inverse, 0.14) : Theme.surface
                                            border.width: bub.mine ? 0 : 1; border.color: Theme.border
                                            Icon { x: 10; anchors.verticalCenter: parent.verticalCenter; name: "file"; size: 13; color: bub.mine ? Theme.inverse : Theme.text2 }
                                            Column { x: 33; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 33 - (bub.mine ? 10 : 62)
                                                Txt { width: parent.width; text: modelData.file ? modelData.file.name : ""; font.pixelSize: 13; font.weight: Font.DemiBold; color: bub.mine ? Theme.inverse : Theme.text }
                                                Txt { width: parent.width; font.pixelSize: 12; color: bub.mine ? Theme.alpha(Theme.inverse, 0.8) : Theme.text3
                                                      text: modelData.file && modelData.file.size_bytes ? (modelData.file.size_bytes >= 1048576 ? (modelData.file.size_bytes / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(modelData.file.size_bytes / 1024)) + " KB") : "" } }
                                            Btn { visible: !bub.mine && !!modelData.file && modelData.file.state !== "waiting"; anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter; small: true; text: "Save"
                                                  onClicked: falcon.call("chat.file_save", { file_id: modelData.file.id }, function (ok, r) { if (ok) Msg.ok("Saved to Downloads\\From Falcon\\" + modelData.file.name); else Msg.failed(r && r.message ? r.message : "Not saved") }) }
                                        }
                                        Txt { id: bs; anchors.right: parent.right; text: Time.hhmm(modelData.at); font.pixelSize: 11; color: bub.mine ? Theme.alpha(Theme.inverse, 0.75) : Theme.text3; elide: Text.ElideNone }
                                    }
                                }
                            }
                        }
                    }
                    Quiet { visible: page.c !== null && (!page.thread || !(page.thread.messages || []).length); text: page.thread ? (page.c && page.c.kind === "admins" ? "Nothing has been said in the Admins group yet." : "Nothing has passed between you and " + (page.c ? page.c.title : "them") + " yet.") : "Loading" }
                }
            }
            // the box to write in (ms-write: a rounded composer under a rule)
            Column {
                id: wr
                visible: page.c !== null
                width: parent.width
                spacing: 10
                Rectangle { width: parent.width; height: 1; color: Theme.border }
                Rectangle {
                    width: parent.width
                    height: Math.max(36, ta.height + 8)
                    radius: 20
                    color: Theme.surface2
                    border.width: 1
                    border.color: Theme.borderStrong
                    Btn { id: clipB; objectName: "msgFile"; x: 4; anchors.verticalCenter: parent.verticalCenter; kind: "text"; circle: true; iconName: "paperclip"
                          tip: "Send a file"; onClicked: { page.fileWhy = ""; page.filePath = ""; sendFile.open() } }
                    TextArea2 {
                        id: ta
                        x: clipB.x + clipB.width + 2
                        width: parent.width - x - sendB.width - 8
                        anchors.verticalCenter: parent.verticalCenter
                        minRows: 1
                        borderless: true
                        placeholder: page.c ? (page.c.kind === "admins" ? "Write to every Admin; all see it" : "Write to " + page.c.title) : ""
                        text: page.draft
                        enterSends: true
                        onEdited: function (t) { page.setDraft(t) }
                    }
                    Btn { id: sendB; objectName: "msgSend"; anchors.right: parent.right; anchors.rightMargin: 4; anchors.verticalCenter: parent.verticalCenter; kind: "primary"; circle: true; iconName: "send"; enabled: page.draft.trim() !== ""; onClicked: page.send() }
                }
            }
            Pulse { parent: conv; key: page.pickedId || null }
        }
    }

    // --- start a conversation ------------------------------------------------------------------------------------------------------------
    Box {
        objectName: "startConversation"
        width: parent.width
        accentFoot: true
        title: "Start a conversation"
        sub: "one person goes to your conversation with them; several people, or every Admin, make a group where everyone sees each other's answers"
        Row {
            width: parent.width
            spacing: 8
            Select { width: 380; search: true; multiple: true; placeholder: "With whom: people, or every Admin"; values: page.many; options: page.whoOptions; onPicked: function (v) { var x = page.many.slice(), i = x.indexOf(v); if (i >= 0) x.splice(i, 1); else x.push(v); page.many = x } }
            Field { width: parent.width - 380 - goB.width - 16; placeholderText: "The message"; text: page.mtxt; onTextEdited: page.mtxt = text }
            Btn { id: goB; kind: "primary"; text: page.many.length > 1 ? "Start the group" : "Send"; enabled: page.many.length > 0 && !page.several && page.mtxt.trim() !== ""; tip: page.several ? "The Engine keeps the group of every Admin only, for now" : ""; onClicked: page.startOne() }
        }
        Rectangle {
            visible: page.many.length > 0
            width: parent.width
            height: visible ? sp.height + 20 : 0
            radius: Theme.radius
            color: Theme.surface2
            Txt { id: sp; x: 12; y: 10; width: parent.width - 24; wrapMode: Text.WordWrap; elide: Text.ElideNone
                  text: page.many.length === 0 ? "" : page.many.indexOf("admins") >= 0 ? "Goes to the Admins group; each of them sees it, and each other's answers." : page.several ? "Starts a group; each of them sees what everyone writes."
                        : "Goes to your conversation with " + ((page.whoOptions.filter(function (o) { return o.value === page.many[0] })[0] || { label: "them" }).label.split(" · ")[0]) + "." }
        }
    }
}
