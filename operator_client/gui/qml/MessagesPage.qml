import QtQuick
import "."

// MESSAGES (Help Ping & Message Channel, at both levels). One row per conversation between a lower and
// a higher party: Worker -> Admin, or Admin -> Super User. It starts as a ping (attention only,
// repeatable); answering opens the channel; then one message each way at a time. Only the higher party
// closes it.
Page {
    id: page
    objectName: "messagesView"

    property var chans: []            // channel summaries
    property var detail: ({})         // channel id -> {channel, messages}
    property var pings: []            // unanswered pings to me
    property string f: ""
    property string sel: Nav.sub ? String(Nav.sub) : ""
    property var drafts: ({})
    property var askFor: []           // who I may ping
    readonly property int me: falcon.accountId

    function load() {
        falcon.call("assistance.channels", {}, function (ok, r) {
            page.chans = ok ? (r.channels || []) : []
            page.chans.forEach(function (c) {
                falcon.call("assistance.channel", { channel_id: c.id }, function (ok2, r2) {
                    if (!ok2) return
                    var d = Object.assign({}, page.detail); d[c.id] = r2; page.detail = d
                })
            })
        })
        falcon.call("assistance.ping_status", {}, function (ok, r) { page.pings = ok ? (r.pings || []) : [] })
        falcon.call("assistance.my_admins", {}, function (ok, r) {
            var up = ok ? (r.admins || []).map(function (a) { return { account: a.account_id, name: a.name, sub: a.role === "super_user" ? "the Super User" : "Admin" } }) : []
            var down = []
            if (Nav.boss) Fleet.depts.forEach(function (d) { d.admins.forEach(function (a) { down.push({ account: a.account_id, name: a.name, sub: "Admin, " + d.name }) }) })
            else Fleet.machines.forEach(function (m) { if (m.user && m.account) down.push({ account: m.account, name: m.user, sub: "on " + m.host }) })
            page.askFor = up.concat(down)
        })
    }
    Component.onCompleted: load()
    Connections { target: falcon; function onPushReceived(type, payload) { if (/^assistance/.test(type)) again.restart() } }
    Timer { id: again; interval: 300; onTriggered: page.load() }

    // every conversation as the person at this console sees it
    readonly property var rows: {
        var out = []
        chans.forEach(function (c) {
            var d = detail[c.id], ch = d ? d.channel : c, names = ch.names || {}
            var hi = c.superior_account_id, lo = ch.subordinate_account_id || c.initiator_account_id
            var party = true      // the Engine lists only the conversations this person is in
            var other = names[String(hi === me ? lo : hi)] || (hi === me ? c.initiator_name : "the Super User")
            var msgs = d ? (d.messages || []).map(function (m) { return { t: Time.ms(m.sent_at || m.created_at), who: names[String(m.sender_account_id)] || "", mine: m.sender_account_id === me, text: m.body } }) : []
            var closed = !!c.closed_at
            var turnIsMine = party && !closed && (d ? !!ch.my_turn : ((c.turn === "superior") === (hi === me)))
            var st = closed ? ["Closed", "good", "closed"] : turnIsMine ? ["Your turn", "bad", "you"] : ["Their turn", "wait", "them"]
            out.push({ id: "c" + c.id, cid: c.id, kind: "channel", title: other,
                       other: other, iHigh: hi === me, party: party, msgs: msgs, closed: closed, myTurn: turnIsMine, st: st,
                       started: c.opened_at, last: msgs.length ? msgs[msgs.length - 1].t : Time.ms(c.closed_at || c.opened_at),
                       pings: 1, line: msgs.length ? (msgs[msgs.length - 1].mine ? "You" : msgs[msgs.length - 1].who) + ": " + msgs[msgs.length - 1].text : "no messages yet" })
        })
        // the Engine answers one row per unanswered ping (id, sender_account_id, sent_at), oldest first: one sender's
        // pings are one conversation-to-be, with every time it pinged (answering addresses them all)
        var bySender = {}, senders = []
        pings.forEach(function (p) {
            var k = String(p.sender_account_id)
            if (!bySender[k]) { bySender[k] = []; senders.push(k) }
            bySender[k].push(p)
        })
        senders.forEach(function (k) {
            var ps = bySender[k], first = ps[0], n0 = ps.length, name = first.from_name || "Someone"
            if (out.some(function (x) { return x.party && x.other === name && !x.closed })) return
            out.push({ id: "p" + first.id, pid: first.id, kind: "ping", title: name, other: name, iHigh: true, party: true, msgs: [], closed: false,
                       myTurn: true, st: ["Pinged you" + (n0 > 1 ? " " + n0 + " times" : ""), "bad", "you"], started: first.sent_at,
                       times: ps.map(function (p) { return p.sent_at }),
                       last: Time.ms(ps[n0 - 1].sent_at), pings: n0, line: (n0 === 1 ? "a ping" : n0 + " pings") + ", no answer yet" })
        })
        var order = { you: 0, them: 1, closed: 2 }
        return out.sort(function (a, b) { return order[a.st[2]] - order[b.st[2]] || b.last - a.last })
    }
    function n(k) { return rows.filter(function (x) { return x.st[2] === k }).length }
    readonly property var shown: rows.filter(function (x) {
        return (f === "" || (f === "ping" ? x.kind === "ping" : x.st[2] === f)) && (x.title + " " + x.msgs.map(function (m) { return m.text }).join(" ")).toLowerCase().indexOf(list.query.toLowerCase()) >= 0
    })
    readonly property var c: { for (var i = 0; i < shown.length; i++) if (shown[i].id === sel) return shown[i]; return shown.length ? shown[0] : null }
    readonly property string draft: c ? (drafts[c.id] || "") : ""
    function setDraft(t) { var d = Object.assign({}, drafts); d[c.id] = t; drafts = d }

    function send() {
        var x = c, text = draft.trim()
        if (!text) return
        if (x.kind === "ping") {
            falcon.call("assistance.respond", { ping_id: x.pid }, function (ok, r) {
                if (!ok) { Msg.failed(r && r.message ? r.message : "Not answered"); return }
                falcon.call("assistance.message", { channel_id: r.channel_id, text: text }, function (ok2) {
                    Msg.ok(ok2 ? "Answered " + x.other + " · the channel is open" : "The channel is open · " + x.other + " writes first")
                    page.sel = "c" + r.channel_id; page.setDraftFor(x.id, ""); page.load()
                })
            })
            return
        }
        falcon.call("assistance.message", { channel_id: x.cid, text: text }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not sent"); return }
            Msg.ok("Sent · now " + x.other + "'s turn"); page.setDraftFor(x.id, ""); page.load()
        })
    }
    function setDraftFor(id, t) { var d = Object.assign({}, drafts); d[id] = t; drafts = d }

    Confirm { id: confirm; page: page }

    MessageTabs {}

    Strip {
        width: parent.width
        on: page.f === "" ? null : page.f
        onPick: function (k) { page.f = k === null ? "" : k }
        items: [
            { key: "you", label: "Waiting on you", value: Theme.fmt(page.n("you")), delta: page.n("you") ? "pinged you, or your turn" : "nothing waiting", dc: page.n("you") ? Theme.crit : undefined },
            { key: "them", label: "Waiting on them", value: Theme.fmt(page.n("them")), delta: "your ping, or their turn" },
            { key: "ping", label: "Pings", value: Theme.fmt(page.rows.filter(function (x) { return x.kind === "ping" }).length), delta: "not answered yet" },
            { key: "closed", label: "Closed", value: Theme.fmt(page.n("closed")), delta: "this week" }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            more: 2
            title: page.f === "" ? "Conversations" : ({ you: "Waiting on you", them: "Waiting on them", ping: "Pings", closed: "Closed" })[page.f]
            sub: "waiting on you first · click one to see it on the right"
            placeholder: "Find a person or a word"
            actionLabel: "New ping"
            onAction: pingDrawer.open()
            rows: page.shown
            pick: page.c ? page.c.id : null
            onPicked: function (k) { page.sel = k }
            icon: function (x) { return x.kind === "ping" ? "bell" : "message" }
            nameTitle: "With"
            nameText: function (x) { return x.title }
            nameLine: function (x) { return x.line }
            cols: [{ title: "Pings", width: 70, text: function (x) { return Theme.fmt(x.pings) } },
                   { title: "Last", width: 100, text: function (x) { return Time.at(x.last) } }]
            now: function (x) { return [x.st[0], x.st[1]] }
            showEmpty: page.rows.length === 0
            emptyIcon: "message"
            emptyTitle: "No conversations yet"
            emptyText: "A ping asks for attention; answering it opens a conversation, one message each way at a time."
            emptyAct: "New ping"
            onEmptyAction: pingDrawer.open()
        }

        SidePanel {
            id: side
            width: (parent.width - 14) * 4 / 12
            implicitHeight: Theme.listHeight + 56 * 2 + 64
            showEmpty: page.c === null
            emptyIcon: "message"
            emptyTitle: "No conversations yet"
            emptyText: Nav.boss ? "When an Admin pings you, or you ping one, it appears here." : "When a worker or the Super User pings you, or you ping them, it appears here."
            title: page.c ? page.c.title : ""
            sub: page.c ? (page.askFor.filter(function (p) { return p.name === page.c.other })[0] || { sub: "" }).sub : ""
            facts: page.c ? [["Now", page.c.st[0], page.c.st[1] === "bad" ? Theme.crit : page.c.st[1] === "good" ? Theme.ok : Theme.text4, false, true],
                             ["Started by", (page.c.kind === "ping" ? page.c.other : page.c.iHigh ? page.c.other : "You") + ", " + Time.at(page.c.started)],
                             ["Who closes it", page.c.iHigh ? "You" : page.c.party ? page.c.other : "the higher party"]] : []
            extra: Btn {
                visible: page.c !== null && page.c.kind === "channel" && page.c.party && !page.c.closed && page.c.iHigh
                small: true; kind: "text"; danger: true; iconName: "closecircle"; tip: "Close the conversation"
                onClicked: confirm.ask({ title: "Close the conversation with " + page.c.other + "?", ok: "Close it", cancel: "Keep it open",
                                         text: "Only you can close it. " + page.c.other + " cannot write in it again; a new ping opens a new one. It stays in the audit log." },
                                       function () { falcon.call("assistance.close_channel", { channel_id: page.c.cid }, function (ok, r) {
                                           if (!ok) { Msg.failed(r && r.message ? r.message : "Not closed"); return }
                                           Msg.ok("Closed · recorded"); page.load() }) })
            }

            // the thread
            Column {
                width: parent.width
                spacing: 6
                Txt { text: page.c && page.c.kind === "ping" ? "PINGED" : "THE CONVERSATION"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Txt { anchors.horizontalCenter: parent.horizontalCenter; color: Theme.text3; font.pixelSize: 12
                      text: page.c ? (page.c.kind === "ping" ? page.c.other + " pinged " + page.c.times.map(function (t) { return Time.at(t) }).join(", ") : "Opened " + Time.at(page.c.started)) : "" }
                Repeater {
                    model: page.c ? page.c.msgs : []
                    Item {
                        required property var modelData
                        width: parent.width
                        height: bub.height
                        Rectangle {
                            id: bub
                            x: modelData.mine ? parent.width - width : 0
                            width: Math.min(parent.width * 0.86, bt.implicitWidth + 22)
                            height: bc.height + 14
                            radius: 10
                            color: modelData.mine ? Theme.accent : Theme.surface2
                            border.width: modelData.mine ? 0 : 1
                            border.color: Theme.border
                            Column {
                                id: bc
                                x: 11; y: 7
                                width: parent.width - 22
                                Txt { visible: !modelData.mine; text: modelData.who + " · " + Time.at(modelData.t); color: Theme.text3; font.pixelSize: 11 }
                                Txt { id: bt; width: Math.min(implicitWidth, side.width * 0.86 - 54); text: modelData.text; wrapMode: Text.Wrap; elide: Text.ElideNone
                                      color: modelData.mine ? Theme.inverse : Theme.text }
                            }
                        }
                    }
                }
                Txt { visible: page.c !== null && page.c.closed; anchors.horizontalCenter: parent.horizontalCenter; text: "Closed"; color: Theme.text3; font.pixelSize: 12; topPadding: 4 }
            }

            footShown: false
            dockShown: page.c !== null && !page.c.closed

            // the composer, docked under the thread
            dock: Item {
                visible: page.c !== null && !page.c.closed
                width: side.width - 32
                height: !page.c ? 0 : (page.c.party && page.c.myTurn) ? composer.height : lockLine.height
                Rectangle {
                    id: composer
                    visible: page.c !== null && page.c.party && page.c.myTurn
                    width: parent.width
                    height: Math.max(40, ta.height + 8)
                    radius: 20
                    color: Theme.surface2
                    border.width: 1
                    border.color: Theme.borderStrong
                    TextArea2 {
                        id: ta
                        x: 4; y: 4
                        width: parent.width - 48
                        minRows: 1
                        maxRows: 5
                        borderless: true
                        enterSends: true
                        text: page.draft
                        placeholder: page.c && page.c.kind === "ping" ? "Answer " + page.c.other + " · answering opens the conversation" : "Write to " + (page.c ? page.c.other : "") + " · then it is their turn"
                        onEdited: function (t) { page.setDraft(t) }
                        onSubmitted: page.send()
                    }
                    Btn { objectName: "msgSend"; circle: true; kind: "primary"; iconName: "send"; tip: "Send · Enter"
                          enabled: page.draft.trim() !== ""; anchors.right: parent.right; anchors.rightMargin: 4; anchors.bottom: parent.bottom; anchors.bottomMargin: 4; onClicked: page.send() }
                }
                Txt {
                    id: lockLine
                    visible: !composer.visible
                    width: parent.width
                    wrapMode: Text.WordWrap; elide: Text.ElideNone
                    color: Theme.text3; font.pixelSize: 12
                    text: !page.c ? "" : page.c.other + "'s turn. You can write again once they answer."
                }
            }
        }
    }

    // --- a new ping ---------------------------------------------------------------------------------
    Drawer {
        id: pingDrawer
        page: page
        width: 420
        title: "Ping someone"
        property var who: null
        note: who === null ? "Pick a person." : ""
        footer: [
            Btn { text: "Cancel"; onClicked: pingDrawer.close() },
            Btn { kind: "primary"; text: "Ping"; enabled: pingDrawer.who !== null
                  onClicked: falcon.call("assistance.ping", { to_account_id: pingDrawer.who }, function (ok, r) {
                      if (!ok) { Msg.failed(r && r.message ? r.message : "Not sent"); return }
                      Msg.ok("Pinged · they see it until they answer"); pingDrawer.close(); page.load()
                  }) }
        ]
        Column {
            width: parent.width
            spacing: 8
            Txt { text: "WHO"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
            Select { width: parent.width; search: true; placeholder: "Pick a person"; value: pingDrawer.who
                     options: page.askFor.map(function (p) { return { value: p.account, label: p.name + " · " + p.sub } })
                     onPicked: function (v) { pingDrawer.who = v } }
        }
        Rectangle {
            width: parent.width; height: pn.height + 20; radius: 6; color: Theme.surface2
            Txt { id: pn; x: 12; y: 10; width: parent.width - 24; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                  text: "A ping carries no message: it only says you need them. They see it, bright and pulsing, until they answer; their answer opens the conversation." }
        }
    }
}
