import QtQuick
import "."

// ONE AT A TIME. A Message Channel is not a chat: it takes turns, and when it is not your turn there
// is nothing to type into. That is the whole feature, so the page shows it as the state of the box
// rather than as a rule written somewhere.
Item {
    id: root

    property var channels: []
    property var pings: []
    property bool loaded: false
    property var chosen: null
    property var channel: null           // what assistance.channel answered: state + messages
    property var mine: []                // only the Listeners I added -- never the other party's

    readonly property var rows: channels.map(function (c) {
        var open = c.closed_at === null || c.closed_at === undefined
        // whose turn it is comes out of the row, not out of a field the Engine does not send
        var turnAccount = c.turn === "superior" ? c.superior_account_id : c.initiator_account_id
        var mineNow = open && turnAccount === falcon.accountId
        var theirs = c.superior_account_id === falcon.accountId ? c.initiator_account_id
                                                                : c.superior_account_id
        return { channel_id: c.id,
                 who: c.other_name || c.initiator_name || c.superior_name || ("account " + theirs),
                 opened: Task.when(c.opened_at),
                 open: open,
                 mineNow: mineNow,
                 superior: c.superior_account_id,
                 stateWord: !open ? "closed" : mineNow ? "your turn" : "waiting on them",
                 stateTone: !open ? "" : mineNow ? "warn" : "",
                 channel: c }
    })
    readonly property int waiting: rows.filter(function (r) { return r.mineNow }).length

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("assistance.channels", {}, function (ok, r) {
            root.loaded = true
            if (ok) root.channels = r.channels || []
        })
        falcon.call("assistance.ping_status", {}, function (ok, r) {
            if (ok) root.pings = r.pings || []
        })
    }
    function openChannel(row) {
        chosen = row
        channel = null
        mine = []
        detail.open()
        falcon.call("assistance.channel", { channel_id: row.channel_id }, function (ok, r) {
            if (ok) root.channel = r
        })
        falcon.call("assistance.my_listeners", { channel_id: row.channel_id }, function (ok, r) {
            if (ok) root.mine = r.listeners || []
        })
    }
    function say() {
        if (!chosen || reply.text.trim() === "") return
        var body = reply.text.trim()
        falcon.call("assistance.message", { channel_id: chosen.channel_id, body: body },
                    function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not sent"); return }
            reply.text = ""
            root.openChannel(root.chosen)
            root.refresh()
        })
    }
    function respond(pingId) {
        falcon.call("assistance.respond", { ping_id: pingId }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not opened"); return }
            Msg.ok("Channel open")
            root.refresh()
        })
    }
    function closeChannel() {
        falcon.call("assistance.close_channel", { channel_id: chosen.channel_id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not closed"); return }
            Msg.ok("Channel closed")
            detail.close()
            root.refresh()
        })
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onDisconnected() { root.channels = []; root.pings = []; root.loaded = false }
        function onPushReceived(type) { if (String(type).indexOf("assistance.") === 0) root.refresh() }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    Column {
        anchors.fill: parent
        anchors.margins: Theme.s5
        spacing: Theme.s3

        PageHeader {
            width: parent.width
            title: "Assistance"
            subtitle: root.rows.length + " conversations"
                      + (root.waiting > 0 ? " · " + root.waiting + " waiting on you" : "")
        }

        // somebody asked for you and nothing is open yet: the one thing on this page that needs an act
        Column {
            width: parent.width
            spacing: Theme.s2
            visible: root.pings.length > 0

            Repeater {
                model: root.pings
                delegate: Rectangle {
                    required property var modelData
                    width: parent.width
                    height: 52
                    radius: Theme.radiusLg
                    color: Theme.warnSoft
                    border.width: 1
                    border.color: "#ffe58f"

                    Txt {
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.s4
                        anchors.right: answer.left
                        anchors.rightMargin: Theme.s3
                        anchors.verticalCenter: parent.verticalCenter
                        text: (modelData.from_name || "Somebody") + " asked for you"
                              + (modelData.count > 1 ? ", " + modelData.count + " times" : "")
                        tone: "warn"
                    }
                    Btn {
                        id: answer
                        objectName: "respondPing"
                        kind: "primary"
                        text: "Answer"
                        anchors.right: parent.right
                        anchors.rightMargin: Theme.s3
                        anchors.verticalCenter: parent.verticalCenter
                        onClicked: root.respond(modelData.ping_id || modelData.id)
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: parent.height - y
            radius: Theme.radiusLg
            color: Theme.surface
            border.width: 1
            border.color: Theme.split

            Table {
                objectName: "channelsTable"
                anchors.fill: parent
                anchors.margins: Theme.s1
                loading: !root.loaded
                pageSize: 10
                rows: root.rows
                emptyText: "Nobody is asking"
                emptyHint: "A conversation opens when somebody pings their superior and the superior answers."
                onRowActivated: function (row) { root.openChannel(row) }
                columns: [
                    { title: "With", key: "who", strong: true },
                    { title: "State", key: "stateWord", width: 180, tag: true,
                      filters: ["your turn", "waiting on them", "closed"],
                      tone: function (r) { return r.stateTone } },
                    { title: "Opened", key: "opened", width: 160, mono: true,
                      tone: function () { return "mid" } }
                ]
            }
        }
    }

    Drawer {
        id: detail
        objectName: "channelDrawer"
        page: root
        title: root.chosen ? root.chosen.who : ""
        subtitle: root.chosen ? root.chosen.stateWord : ""

        // the conversation, oldest first, because that is how it was said
        Column {
            width: parent.width
            spacing: Theme.s2

            Repeater {
                model: root.channel && root.channel.messages ? root.channel.messages : []
                delegate: Column {
                    required property var modelData
                    width: parent.width
                    spacing: 1

                    readonly property bool byMe: modelData.sender_account_id === falcon.accountId

                    Txt {
                        text: parent.byMe ? "You" : (root.chosen ? root.chosen.who : "them")
                        tone: "quiet"
                        font.pixelSize: 11
                    }
                    Rectangle {
                        width: parent.width
                        height: line.contentHeight + 2 * Theme.s2
                        radius: Theme.radius
                        color: parent.byMe ? Theme.primarySoft : Theme.fill
                        border.width: 1
                        border.color: Theme.split
                        Txt {
                            id: line
                            anchors.fill: parent
                            anchors.margins: Theme.s2
                            text: modelData.body
                            wrapMode: Text.WordWrap
                            elide: Text.ElideNone
                            font.pixelSize: Theme.fSmall
                        }
                    }
                }
            }
        }
        Empty {
            width: parent.width
            visible: root.channel !== null && (root.channel.messages || []).length === 0
            text: "Nothing said yet"
            hint: "Whoever asked speaks first."
        }

        // the turn, as the state of the box rather than as a sentence about a rule
        Area {
            id: reply
            objectName: "replyBox"
            width: parent.width
            implicitHeight: 84
            enabled: root.chosen && root.chosen.mineNow
            placeholderText: root.chosen && !root.chosen.open ? "This conversation is closed."
                             : root.chosen && root.chosen.mineNow ? "Your turn."
                             : "Waiting for them. You can write again once they have replied."
        }

        Txt {
            width: parent.width
            visible: root.mine.length > 0
            text: root.mine.length === 1 ? "You added one Listener" : "You added " + root.mine.length + " Listeners"
            tone: "mid"
            font.pixelSize: Theme.fSmall
        }
        Txt {
            width: parent.width
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
            tone: "quiet"
            font.pixelSize: 11
            text: "Either side may bring an Admin in to read along, and the other side is not told. "
                  + "You only ever see the ones you brought."
        }

        // the Drawer's footer is a Row: order places these, not anchors
        footer: [
            Btn {
                objectName: "closeChannel"
                danger: true
                text: "Close"
                visible: root.channel !== null && root.chosen && root.chosen.superior === falcon.accountId
                         && root.chosen && root.chosen.open
                onClicked: root.closeChannel()
            },
            Btn {
                objectName: "sendMessage"
                kind: "primary"
                text: "Send"
                enabled: root.chosen && root.chosen.mineNow && reply.text.trim() !== ""
                onClicked: root.say()
            }
        ]
    }
}
