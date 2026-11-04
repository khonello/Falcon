import QtQuick
import "."

// SEND AN ANNOUNCEMENT, in three steps: who it is for, what it says, when it goes. The sentence on top changes as it is filled in; nothing goes out until the last word.
Editor {
    id: page
    objectName: "newAnnouncement"
    drawerTitle: "Send an announcement"
    drawerNote: "nothing goes out until you confirm"
    names: ["Who it is for", "What it says", "When it goes"]
    nameNow: title
    noName: "No title yet"
    confirmText: later ? "Schedule it" : "Send it"
    confirmDanger: kind === "emergency"

    property string audience: "all_users"
    property var dept: null
    property var some: []
    property string kind: "announcement"
    property string title: ""
    property string message: ""
    property bool later: false
    property var at: null
    property bool busy: false
    confirmDisabled: busy

    readonly property var kinds: [["announcement", "Announcement", "It waits in their Falcon program, with a quiet note in the corner. It does not interrupt anyone."],
                                  ["warning", "Warning", "The same, marked as a warning, for something they should watch out for."],
                                  ["emergency", "Emergency", "It covers the screen on every machine it reaches until the person has read it. Use it only when it cannot wait."]]
    readonly property var kindWord: kinds.filter(function (k) { return k[0] === page.kind })[0][1]
    readonly property var people: {
        var out = []
        Fleet.machines.forEach(function (m) { if (m.user && m.account) out.push({ value: m.account, label: m.user + " · " + m.host }) })
        return out
    }
    readonly property string toWord: audience === "all_users" ? "everyone" : audience === "admin_only" ? "all Admins"
        : audience === "department" ? (Fleet.depts.filter(function (d) { return d.id === page.dept }).map(function (d) { return d.name })[0] || "the department you pick")
        : some.length ? Theme.listNames(people.filter(function (p) { return page.some.indexOf(p.value) >= 0 }).map(function (p) { return p.label.split(" · ")[0] }), 3) : "the people you name"
    readonly property string whenWord: later ? (at ? Time.date(at) : "at a time") : "now"
    prob: step === 0 && audience === "department" && !dept ? "Pick a department." : step === 0 && audience === "specific_users" && !some.length ? "Pick at least one person."
          : step === 1 && !message.trim() ? "Write the announcement." : step === 2 && later && !at ? "Pick when it goes." : ""

    onConfirmed: {
        var p = { type: kind, audience: audience, body: message.trim() }
        if (title.trim()) p.title = title.trim()
        if (audience === "department") p.department_id = dept
        if (audience === "specific_users") p.account_ids = some
        if (later) p.deliver_at = at
        busy = true
        falcon.call("alerts.create", p, function (ok, r) {
            page.busy = false
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not sent"); return }
            Msg.ok(page.later ? "Waiting to go out" : "Sent"); Nav.go("announcements")
        })
    }

    function part(t, on) { return "<font color='" + (on ? Theme.accent : Theme.text) + "'>" + t + "</font>" }
    function quiet(t) { return "<font color='" + Theme.text3 + "'>" + t + "</font>" }
    head: Txt {
        width: parent.width; textFormat: Text.StyledText; wrapMode: Text.WordWrap; elide: Text.ElideNone
        font.pixelSize: 17; font.weight: Font.Medium; lh: 1.45
        text: page.quiet("To") + " " + page.part(page.toWord, page.step === 0) + page.quiet(", as") + " " + page.part(page.kindWord.toLowerCase(), page.step === 1) + page.quiet(",") + " " + page.part(page.whenWord, page.step === 2)
    }

    NfSec { visible: page.step === 0; first: true; title: "Who is it for?"
        NfPick { title: "Everyone"; desc: "Every person and every Admin."; on: page.audience === "all_users"; onPicked: page.audience = "all_users" }
        NfPick { title: "A department"; desc: "Everyone in the one you pick."; on: page.audience === "department"; onPicked: page.audience = "department" }
        NfPick { title: "All Admins"; desc: "Only the IT Admins, in their consoles."; on: page.audience === "admin_only"; onPicked: page.audience = "admin_only" }
        NfPick { title: "Chosen people"; desc: "Only the people you name."; on: page.audience === "specific_users"; onPicked: page.audience = "specific_users" } }
    NfSec { visible: page.step === 0 && page.audience === "department"; title: "Which department?"
        Select { width: parent.width; search: true; placeholder: "Pick a department"; value: page.dept; options: Fleet.depts.map(function (d) { return { value: d.id, label: d.name } }); onPicked: function (v) { page.dept = v } } }
    NfSec { visible: page.step === 0 && page.audience === "specific_users"; title: "Who?"
        Select { width: parent.width; multiple: true; search: true; placeholder: "Pick people"; values: page.some; options: page.people; onPicked: function (v) { page.some = v } } }

    NfSec { visible: page.step === 1; first: true; title: "What kind is it?"
        Repeater { model: page.kinds
            NfPick { required property var modelData; title: modelData[1]; desc: modelData[2]; on: page.kind === modelData[0]; onPicked: page.kind = modelData[0] } } }
    NfSec { visible: page.step === 1; title: "A title"; optional: "optional"
        Field { objectName: "annTitle"; width: parent.width; text: page.title; placeholderText: "For example Office closed on Monday"; maximumLength: 120; onTextEdited: page.title = text } }
    NfSec { visible: page.step === 1; title: "What do they need to know?"
        TextArea2 { objectName: "annBody"; width: parent.width; minRows: 5; maxRows: 10; maxLength: 1500; text: page.message; onEdited: function (t) { page.message = t } } }

    NfSec { visible: page.step === 2; first: true; title: "When does it go?"
        NfPick { title: "Now"; desc: "It goes the moment you confirm."; on: !page.later; onPicked: page.later = false }
        NfPick { title: "At a time"; desc: "It waits, and you can withdraw it until then."; on: page.later; onPicked: page.later = true } }
    NfSec { visible: page.step === 2 && page.later
        DateTimeField { width: 240; value: page.at; placeholder: "Pick when"; onChanged: function (v) { page.at = v } } }
    NfSec { visible: page.step === 2
        FactRows { rows: [["To", page.toWord], ["Kind", page.kindWord], ["Title", page.title.trim() || "none"], ["Goes", page.whenWord]] } }
    Decide { visible: page.step === 2 && page.kind === "emergency"; c: Theme.crit; text: "It covers the screen on every machine it reaches until the person has read it." }
}
