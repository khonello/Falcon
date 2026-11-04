import QtQuick
import "."

// ANNOUNCEMENTS: what is said to many people at once. What went out and what is waiting, a click reads it on the right; sending one is the drawer. A Worker reads it in the
// Falcon program, and an emergency covers their screen until it is read. Delivered is enough: nothing here tracks who read it.
Page {
    id: page
    objectName: "announcements"

    property var sent: []
    property var sel: null
    function refresh() { if (falcon.isConnected) falcon.call("alerts.sent", {}, function (ok, r) { if (ok) page.sent = r.alerts || [] }) }
    Component.onCompleted: refresh()
    Connections { target: falcon; function onConnected() { page.refresh() } function onPushReceived(type) { if (/^alert/.test(type)) page.refresh() } }
    Timer { running: Nav.sub === null && page.visible; interval: 800; onTriggered: page.refresh() }
    Confirm { id: confirm; page: page }

    readonly property var words: ({ announcement: "Announcement", warning: "Warning", emergency: "Emergency", routine: "Announcement" })
    readonly property var icons: ({ announcement: "notification", warning: "warning", emergency: "alert", routine: "notification" })
    readonly property var waiting: sent.filter(function (a) { return a.status === "scheduled" })
    readonly property var out: sent.filter(function (a) { return a.status === "delivered" })
    readonly property var gone: sent.filter(function (a) { return a.status === "withdrawn" })
    readonly property var cur: { for (var i = 0; i < sent.length; i++) if (sent[i].id === sel) return sent[i]; return out[0] || sent[0] || null }
    readonly property real weekAgo: Time.now - 7 * 86400000
    function whenWord(x) {
        var d = Math.round((Time.startOfDay(Time.ms(x)) - Time.startOfDay(Time.now)) / 86400000)
        return (d === 0 ? "today " : d === 1 ? "tomorrow " : Time.dayName(x) + " ") + Time.hhmm(x)
    }
    function who(a) { return a.from_you ? "you" : a.from_name || "an Admin" }
    function toWord(a) { return a.audience_label === "Everyone" ? "everyone" : a.audience_label }
    situation: {
        if (!sent.length) return "Nothing has been announced yet."
        var week = out.filter(function (a) { return Time.ms(a.deliver_at) > page.weekAgo })
        return Theme.fmt(week.length) + " sent this week" + (week.some(function (a) { return a.alert_type === "emergency" }) ? ", one of them an emergency" : "") + ". "
               + (waiting.length ? Theme.fmt(waiting.length) + " waiting to go out, " + whenWord(waiting[0].deliver_at) + "." : "Nothing is waiting to go out.")
    }
    situationAt: Time.now
    function withdraw(a) {
        confirm.ask({ title: "Withdraw " + (a.title || "this announcement") + "?", text: "It does not go out. It stays listed as withdrawn.", ok: "Withdraw it", cancel: "Keep it", danger: true },
                    function () { falcon.call("alerts.cancel", { alert_id: a.id }, function (ok, r) {
                        if (!ok) { Msg.failed(r && r.message ? r.message : "Could not withdraw it"); return }
                        Msg.ok("Withdrawn"); page.refresh() }) })
    }

    Row {
        width: parent.width
        spacing: 14
        Box {
            id: listP
            objectName: "announcementList"
            width: (parent.width - 14) * 8 / 12
            height: Math.max(implicitHeight, readP.implicitHeight)
            title: "What was announced · " + page.sent.length
            sub: "every Admin's; click one to read it on the right"
            Repeater {
                model: [["Waiting to go out", "they go at their time; withdraw one to stop it", page.waiting], ["Sent", "newest first", page.out], ["Withdrawn", "they did not go out", page.gone]]
                delegate: Group {
                    id: ag
                    required property var modelData
                    required property int index
                    visible: modelData[2].length > 0
                    spaced: index > 0
                    cardGap: 5
                    width: listP.innerW
                    title: modelData[0] + " · " + modelData[2].length
                    sub: modelData[1]
                    Repeater {
                        model: ag.modelData[2]
                        delegate: Card {
                            id: ac
                            required property var modelData
                            width: ag.cardW
                            midW: 260
                            padV: 7
                            actW: 0
                            icon: page.icons[modelData.alert_type] || "notification"
                            hot: modelData.alert_type === "emergency"
                            title: modelData.title || modelData.body
                            line: "To " + page.toWord(modelData) + " · by " + page.who(modelData)
                            picked: page.cur !== null && page.cur.id === modelData.id
                            onOpen: page.sel = modelData.id
                            mid: Row {
                                anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right
                                spacing: 18
                                Txt { text: page.words[ac.modelData.alert_type] || ""; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                                Txt { text: page.whenWord(ac.modelData.deliver_at); mono: true; color: Theme.text3; elide: Text.ElideNone }
                            }
                        }
                    }
                }
            }
            Quiet { visible: page.sent.length === 0; text: "Nothing has been announced yet." }
        }
        Box {
            id: readP
            objectName: "announcementRead"
            width: (parent.width - 14) * 4 / 12
            height: Math.max(implicitHeight, listP.implicitHeight)
            title: page.cur ? page.words[page.cur.alert_type] || "" : "Nothing picked"
            sub: page.cur ? (page.cur.status === "scheduled" ? "waiting to go out" : page.cur.status === "withdrawn" ? "withdrawn" : "sent") : ""
            gap: 10
            Txt { visible: page.cur !== null; width: parent.width; text: page.cur ? page.cur.title || "" : ""; font.pixelSize: 17; font.weight: Font.Medium; lh: 1.45; wrapMode: Text.WordWrap; elide: Text.ElideNone }
            Txt { visible: page.cur !== null; width: parent.width; text: page.cur ? page.cur.body : ""; color: Theme.text2; wrapMode: Text.WordWrap; elide: Text.ElideNone }
            FactRows { visible: page.cur !== null
                       rows: page.cur ? [["To", page.cur.audience_label], ["From", page.who(page.cur)], [page.cur.status === "scheduled" ? "Goes out" : "Went out", page.whenWord(page.cur.deliver_at)]] : [] }
            Item { visible: page.cur !== null && page.cur.status === "scheduled"; width: parent.width; height: 26
                   Btn { anchors.right: parent.right; small: true; danger: true; text: "Withdraw it"; onClicked: page.withdraw(page.cur) } }
        }
    }

    Box {
        width: parent.width
        accentFoot: true
        title: "Send an announcement"
        sub: "nothing goes out until you confirm"
        GiveSteps {
            steps: [["Say who it is for", "everyone, a department, the Admins, or people you name"], ["Write it", "an announcement, a warning, or an emergency that covers the screen"], ["Say when", "now, or at a time you pick"]]
            act: "Send an announcement"
            onGo: Nav.go("announcements", "new")
        }
    }
}
