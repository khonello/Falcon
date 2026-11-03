import QtQuick
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
    property var requests: []             // requests to talk, when the Engine has them
    property string sel: { var a = Nav.takeArrive("messages"); return a !== null ? String(a) : Nav.sub && Nav.sub !== "announcements" ? String(Nav.sub) : "" }
    property var drafts: ({})
    property string q: ""
    property var who: null
    property string mtxt: ""
    readonly property int me: falcon.accountId

    function load() {
        falcon.call("chat.list", {}, function (ok, r) { page.convs = ok ? (r.conversations || []) : []; page.loadThread() })
        falcon.call("chat.people", {}, function (ok, r) { page.people = ok ? (r.people || []) : []; page.adminsGroup = ok && !!r.admins_group })
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
    readonly property var c: { for (var i = 0; i < rows.length; i++) if (rows[i].id === sel) return rows[i]; return rows.length ? rows[0] : null }
    onCChanged: { thread = null; loadThread(); pickedId = c ? c.id : "" }
    property string pickedId: ""
    readonly property string draft: c ? (drafts[c.id] || "") : ""
    function setDraft(t) { var d = Object.assign({}, drafts); d[c.id] = t; drafts = d }
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

    // starting a conversation: one person goes to your conversation with them; every Admin goes to their group
    readonly property var whoOptions: (adminsGroup ? [{ value: "admins", label: "Every Admin" }] : [])
        .concat(people.filter(function (p) { return p.role === "admin" }).map(function (p) { return { value: "a" + p.account_id, label: p.name + " · Admin" } }))
        .concat(people.filter(function (p) { return p.role !== "admin" }).map(function (p) { return { value: "p" + p.pc_id, label: (p.name || "nobody signed in") + " · " + p.hostname + (p.online ? "" : " · offline") } }))
    function startOne() {
        var w = String(who), pl = w === "admins" ? { admins: true } : w.charAt(0) === "a" ? { account_id: Number(w.slice(1)) } : { pc_id: Number(w.slice(1)) }, text = mtxt.trim()
        falcon.call("chat.open", pl, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not opened"); return }
            var id = r.conversation.conversation_id
            page.sel = String(id)
            if (!text) { Msg.ok("The conversation with " + (r.conversation.title || "them") + " is open"); page.load(); return }
            falcon.call("chat.send", { conversation_id: id, body: text }, function (ok2, r2) {
                if (!ok2) Msg.failed(r2 && r2.message ? r2.message : "Opened, but not sent"); else Msg.ok("Sent to " + (r.conversation.title || "them"))
                page.who = null; page.mtxt = ""; page.load()
            })
        })
    }

    situation: {
        if (!rows.length && !requests.length) return "No conversations yet. Start one below."
        var oldest = rows.filter(function (x) { return !x.unread && x.line.indexOf("You: ") === 0 }).sort(function (a, b) { return a.last - b.last })[0]
        return (requests.length ? (requests.length === 1 ? requests[0].from + " asks" : Theme.fmt(requests.length) + " people ask") + " to talk; every Admin sees " + (requests.length === 1 ? "it" : "them") + " until one accepts. " : "")
               + (unread.length ? Theme.listNames(unread.map(function (x) { return x.title }), 2) + (unread.length === 1 ? " is" : " are") + " waiting on your answer." : "Nobody is waiting on you.")
               + (oldest ? " Your message to " + oldest.title + " has waited " + Time.age(oldest.last) + "." : "")
    }
    situationAt: Time.now

    Confirm { id: confirm; page: page }

    function initials(n) { var p = String(n || "?").replace(/[^A-Za-z. ]/g, " ").split(/[\s.]+/).filter(function (x) { return x }); return (p.length > 1 ? p[0][0] + p[p.length - 1][0] : (p[0] || "?").slice(0, 2)).toUpperCase() }
    // a person or a group as a round face (ib-av): their initials on surface-3
    component Face: Rectangle {
        property string name: ""
        property real size: 34
        width: size; height: size; radius: size / 2
        color: Theme.surface3
        Txt { anchors.centerIn: parent; text: page.initials(parent.name); font.pixelSize: parent.size > 40 ? 14 : parent.size < 28 ? 9 : 11; font.weight: Font.DemiBold; color: Theme.text2; elide: Text.ElideNone }
    }
    component Section: Column {
        id: sec
        property string name: ""
        property string note: ""
        property var xs: []
        visible: xs.length > 0
        width: parent.width
        spacing: 2
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
                objectName: "conv_" + modelData.id
                width: sec.width; height: pt.height + 16; radius: Theme.radiusLg
                color: page.c && page.c.id === modelData.id ? Theme.accentSoft : ma.containsMouse ? Theme.surface2 : "transparent"
                Face { x: 8; anchors.verticalCenter: parent.verticalCenter; name: modelData.title }
                Column {
                    id: pt
                    x: 54; y: 8; width: parent.width - 62
                    Item { width: parent.width; height: nm.height
                        Txt { id: nm; text: modelData.title + (modelData.kind === "admins" ? "" : ""); font.weight: Font.DemiBold; width: Math.min(implicitWidth, parent.width - tm.implicitWidth - 8) }
                        Txt { visible: modelData.kind === "admins"; x: nm.width + 6; y: nm.baselineOffset - baselineOffset; text: modelData.members.length; color: Theme.text3; font.pixelSize: 11; font.weight: Font.Medium; elide: Text.ElideNone }
                        Txt { id: tm; anchors.right: parent.right; y: nm.baselineOffset - baselineOffset; text: modelData.last ? Time.ago(modelData.last) : ""; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone } }
                    Item { width: parent.width; height: ln.height
                        Txt { id: ln; width: parent.width - (modelData.unread ? 28 : 0); text: modelData.line; font.pixelSize: 13; color: modelData.unread ? Theme.text : Theme.text3; font.weight: modelData.unread ? Font.Medium : Font.Normal }
                        Rectangle { visible: modelData.unread > 0; anchors.right: parent.right; anchors.verticalCenter: ln.verticalCenter; width: Math.max(20, cn.implicitWidth + 12); height: 20; radius: 10; color: Theme.accent
                                    Txt { id: cn; anchors.centerIn: parent; text: modelData.unread; color: Theme.inverse; font.pixelSize: 11; font.weight: Font.DemiBold; elide: Text.ElideNone } } }
                }
                MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.sel = modelData.id }
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
            Quiet { visible: page.c === null; text: "Pick someone on the left." }
            // the head (ms-head): their face, who and where, under a rule
            Item {
                visible: page.c !== null
                width: parent.width
                height: Math.max(44, hc.height) + 11
                Face { size: 44; name: page.c ? page.c.title : "" }
                Column {
                    id: hc
                    x: 56; width: parent.width - 56
                    spacing: 2
                    Txt { width: parent.width; text: page.c ? (page.c.kind === "admins" ? "Every Admin" : page.c.title) : ""; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Txt { width: parent.width; font.pixelSize: 13; color: Theme.text3; wrapMode: Text.WordWrap; elide: Text.ElideNone
                          text: !page.c ? "" : page.c.kind === "admins" ? "A group of " + page.c.members.length + " and you. Each of them sees what everyone writes."
                                : conv.person ? (conv.person.role === "admin" ? "Admin" : "Signed in on " + conv.person.hostname + (conv.person.online ? "" : " · offline")) : "" }
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
                                        Txt { id: bt; width: parent.width; text: modelData.body + (modelData.file ? "\nFile: " + modelData.file.name : ""); lh: 1.45; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: bub.mine ? Theme.inverse : Theme.text }
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
                    TextArea2 {
                        id: ta
                        x: 6
                        width: parent.width - 6 - sendB.width - 8
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
        sub: "one person goes to your conversation with them; every Admin goes to the group where everyone sees each other's answers"
        Row {
            width: parent.width
            spacing: 8
            Select { width: 380; search: true; placeholder: "With whom: a person, or every Admin"; value: page.who; options: page.whoOptions; onPicked: function (v) { page.who = v } }
            Field { width: parent.width - 380 - goB.width - 16; placeholderText: "The message"; text: page.mtxt; onTextEdited: page.mtxt = text }
            Btn { id: goB; kind: "primary"; text: "Send"; enabled: page.who !== null; onClicked: page.startOne() }
        }
        Rectangle {
            visible: page.who !== null
            width: parent.width
            height: visible ? sp.height + 20 : 0
            radius: Theme.radius
            color: Theme.surface2
            Txt { id: sp; x: 12; y: 10; width: parent.width - 24; wrapMode: Text.WordWrap; elide: Text.ElideNone
                  text: String(page.who) === "admins" ? "Goes to the Admins group; each of them sees it, and each other's answers." : "Goes to your conversation with " + ((page.whoOptions.filter(function (o) { return o.value === page.who })[0] || { label: "them" }).label.split(" · ")[0]) + "; only the two of you see it." }
        }
    }
}
