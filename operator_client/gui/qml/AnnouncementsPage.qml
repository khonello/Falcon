import QtQuick
import "."

// ANNOUNCEMENTS. Say something to the people it concerns: everyone, a department, the Admins, or chosen people (an
// Admin: their own department). It lands in the small Falcon program on each Worker's machine, and in an Admin's
// console; an emergency also covers the screen until it is dismissed. Delivered is enough: nothing here tracks who read it.
// On the right, what was sent, what is scheduled, and what was withdrawn.
Page {
    id: page
    objectName: "announcements"
    bare: false

    property string kind: "announcement"
    property string title: ""
    property string body: ""
    property string audience: Nav.boss ? "all_users" : "department"
    property int dept: 0
    property var some: []
    property string when: "now"
    property string at: new Date(Time.now + 3600000).toISOString()
    property var sent: []
    property bool busy: false

    readonly property var myDept: Fleet.depts.length ? Fleet.depts[0] : null
    readonly property int deptId: Nav.boss ? dept : (myDept ? myDept.id : 0)
    readonly property var people: {
        var out = []
        Fleet.machines.forEach(function (m) { if (m.user && m.account && (Nav.boss || !myDept || m.dept === myDept.id)) out.push({ value: m.account, label: m.user + " · " + m.host }) })
        return out
    }
    readonly property var audiences: Nav.boss
        ? [{ value: "all_users", label: "Everyone" }, { value: "department", label: "A department" }, { value: "admin_only", label: "All Admins" }, { value: "specific_users", label: "Chosen people" }]
        : [{ value: "department", label: myDept ? "Everyone in " + myDept.name : "My department" }, { value: "specific_users", label: "Chosen people" }]
    readonly property string problem: !body.trim() ? "Write the announcement."
        : audience === "department" && !deptId ? "Pick a department."
        : audience === "specific_users" && !some.length ? "Pick at least one person."
        : ""

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("alerts.sent", {}, function (ok, r) { if (ok) page.sent = r.alerts || [] })
    }
    function send() {
        var p = { type: kind, audience: audience, body: body.trim() }
        if (title.trim()) p.title = title.trim()
        if (audience === "department") p.department_id = deptId
        if (audience === "specific_users") p.account_ids = some
        if (when === "later") p.deliver_at = at
        busy = true
        falcon.call("alerts.create", p, function (ok, r) {
            page.busy = false
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not sent"); return }
            Msg.ok(page.when === "later" ? "Scheduled for " + Time.date(page.at) : "Sent")
            page.title = ""; page.body = ""; page.when = "now"
            page.refresh()
        })
    }
    function withdraw(id) {
        falcon.call("alerts.cancel", { alert_id: id }, function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Could not withdraw it"); return }
            Msg.ok("Withdrawn")
            page.refresh()
        })
    }
    Component.onCompleted: if (falcon.isConnected) refresh()
    Connections { target: falcon; function onConnected() { page.refresh() } }

    component Head: Txt { color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66; elide: Text.ElideNone }

    Row {
        width: parent.width
        spacing: 14

        Panel {
            id: compose
            width: (parent.width - 14) * 7 / 12
            title: "New announcement"
            sub: "goes out the moment you send it, or at the time you choose"
            pad: 20
            Column {
                width: parent.width
                spacing: 20
                Column {
                    width: parent.width; spacing: 8
                    Head { text: "TO" }
                    Segmented { objectName: "annAudience"; options: page.audiences; value: page.audience; onPicked: function (v) { page.audience = v } }
                    Select { visible: page.audience === "department" && Nav.boss; width: Math.min(420, parent.width); search: true; placeholder: "Which department?"; value: page.dept || null
                             options: Fleet.depts.map(function (d) { return { value: d.id, label: d.name } }); onPicked: function (v) { page.dept = v } }
                    Select { visible: page.audience === "specific_users"; width: Math.min(420, parent.width); multiple: true; search: true; placeholder: "Who?"; values: page.some
                             options: page.people; onPicked: function (v) { page.some = v } }
                }
                Column {
                    width: parent.width; spacing: 8
                    Head { text: "KIND" }
                    Segmented { objectName: "annKind"; options: [{ value: "announcement", label: "Announcement" }, { value: "warning", label: "Warning" }, { value: "emergency", label: "Emergency" }]
                                value: page.kind; onPicked: function (v) { page.kind = v } }
                    Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: page.kind === "emergency" ? Theme.crit : Theme.text3; font.pixelSize: 12
                          text: page.kind === "emergency" ? "An emergency covers the screen on every machine it reaches until the person dismisses it. Use it only when it cannot wait."
                              : page.kind === "warning" ? "Shown first in the person's list, marked as a warning." : "Waits in the person's Falcon program. It does not interrupt anyone." }
                }
                Column {
                    width: parent.width; spacing: 8
                    Head { text: "MESSAGE" }
                    Field { objectName: "annTitle"; width: parent.width; text: page.title; placeholderText: "A short title (optional)"; maximumLength: 120; onTextEdited: page.title = text }
                    TextArea2 { objectName: "annBody"; width: parent.width; minRows: 4; maxRows: 10; maxLength: 1500; placeholder: "What do they need to know?"
                                text: page.body; onEdited: function (t) { page.body = t } }
                }
                Column {
                    width: parent.width; spacing: 8
                    Head { text: "WHEN" }
                    Segmented { objectName: "annWhen"; options: [{ value: "now", label: "Now" }, { value: "later", label: "Later" }]; value: page.when; onPicked: function (v) { page.when = v } }
                    DateTimeField { visible: page.when === "later"; width: 220; value: page.at; onChanged: function (v) { page.at = v } }
                }
                Row {
                    spacing: 12
                    Btn { objectName: "annSend"; kind: "primary"; text: page.when === "later" ? "Schedule it" : "Send it"; enabled: page.problem === "" && !page.busy; loading: page.busy; onClicked: page.send() }
                    Txt { visible: page.problem !== ""; text: page.problem; color: Theme.text3; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideNone }
                }
            }
        }

        Panel {
            width: (parent.width - 14) * 5 / 12
            title: "Sent"
            sub: Nav.boss ? "everything sent" : "what you have sent"
            pad: 0
            flush: true
            Column {
                width: parent.width
                Empty { visible: page.sent.length === 0; width: parent.width; icon: "notification"; title: "Nothing sent yet"; text: "What you send, and what is scheduled, is listed here." }
                Repeater {
                    model: page.sent
                    delegate: Rectangle {
                        required property var modelData
                        width: parent.width
                        height: row.height + 20
                        color: "transparent"
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
                        Column {
                            id: row
                            x: 16; y: 10
                            width: parent.width - 32
                            spacing: 3
                            Row {
                                spacing: 8
                                Txt { text: modelData.title || modelData.body; font.weight: Font.Medium; width: Math.min(implicitWidth, row.width - 120); elide: Text.ElideRight }
                                Tag { text: modelData.status === "scheduled" ? "Scheduled" : modelData.status === "withdrawn" ? "Withdrawn" : "Delivered"
                                      tone: modelData.status === "scheduled" ? "wait" : "" }
                                Tag { visible: modelData.alert_type !== "announcement"; text: modelData.alert_type === "emergency" ? "Emergency" : "Warning"; tone: modelData.alert_type === "emergency" ? "bad" : "wait" }
                            }
                            Txt { width: parent.width; text: modelData.audience_label + " · " + (modelData.status === "scheduled" ? "goes out " : "") + Time.at(modelData.deliver_at)
                                  color: Theme.text3; font.pixelSize: 12; elide: Text.ElideRight }
                            Txt { visible: !!modelData.title; width: parent.width; text: modelData.body; color: Theme.text2; font.pixelSize: 12; maximumLineCount: 2; wrapMode: Text.WordWrap; elide: Text.ElideRight }
                            Link { visible: modelData.status === "scheduled"; text: "Withdraw it"; font.pixelSize: 12; topPadding: 2; onClicked: page.withdraw(modelData.id) }
                        }
                    }
                }
            }
        }
    }
}
