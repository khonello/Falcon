import QtQuick
import "."

// MAKE A RULE (and Edit), the concept's RuleNew: the rule written out on top the whole way, changing as it is filled in, the part being set in the accent. When it starts
// is picked from lists, a reading on a capped slider, or a time with day toggles or a date; the machines are a checklist; actions come from a list, each with a capped time
// limit; then it is checked and switched on. Nothing runs until then.
Editor {
    id: page
    objectName: "newRule"
    readonly property int editId: Nav.sub && String(Nav.sub).indexOf("edit-") === 0 ? Number(String(Nav.sub).slice(5)) : 0
    drawerTitle: editId ? "Edit " + (original ? Auto.nameOf(original) : "") : "Make a rule"
    drawerNote: "nothing runs until you confirm"
    names: ["When it starts", "Which machines", "What it does", "Check and switch on"]
    nameNow: name
    confirmText: editId ? "Save changes" : "Switch it on"

    property string name: ""
    property string kind: "Event"               // Event | Threshold | Schedule
    property string ev: "usb"
    property string prog: ""
    property string rd: "cpu"
    property var lv: null
    property int mins: 5
    property string at: "09:00"
    property string rep: "days"                 // days | date
    property var days: [0, 1, 2, 3, 4]
    property var date: null
    property bool all: true
    property var hosts: []                      // pc ids
    property var acts: []                       // [{ id, name, limit }], in order
    property bool addOpen: false
    property string aq: ""
    property var lib: []
    property var original: null
    property var taken: []

    readonly property var evs: [["usb", "a USB storage device is inserted", "usb", "the machine reports it the moment the drive goes in", "usb.inserted"], ["printer", "a shared printer stops responding", "printer", "checked from the machines that print to it", "printer.offline"],
        ["prog", "a program you name starts", "appstore", "you name the program on the next line", "program.launched"], ["night", "someone signs in outside working hours", "moon", "working hours are 07:00 to 19:00, Monday to Friday", "user.login"],
        ["restricted", "a restricted file turns up where it is not allowed", "fileprotect", "from the one file index, the moment it is seen", "resource.violation"]]
    // id, word, unit, least, most, usual, step, verb, type
    readonly property var reads: [["cpu", "CPU", "%", 50, 100, 90, 5, "stays above", "threshold.cpu"], ["mem", "memory", "%", 50, 100, 90, 5, "stays above", "threshold.memory"],
        ["disk", "the disk", "% full", 50, 100, 90, 5, "is more than", "threshold.disk"], ["signin", "failed sign-ins", "", 2, 20, 5, 1, "reach", "threshold.signin"]]
    readonly property var r0: reads.filter(function (x) { return x[0] === page.rd })[0]
    readonly property int level: lv === null ? r0[5] : Math.min(r0[4], Math.max(r0[3], lv))
    readonly property var dayWords: Auto.dayNames
    readonly property string dayText: days.length === 7 ? "any day" : days.length === 5 && days.indexOf(5) < 0 && days.indexOf(6) < 0 ? "a weekday"
                                      : days.length ? Theme.listNames(days.slice().sort().map(function (d) { return page.dayWords[d] })) : "no day yet"
    readonly property string whenTxt: kind === "Event" ? (ev === "prog" ? (prog.trim() || "a program you name") + " starts" : evs.filter(function (e) { return e[0] === page.ev })[0][1])
        : kind === "Threshold" ? (rd === "signin" ? level + " sign-ins fail within " + mins + " minutes" : r0[1] + " " + r0[7] + " " + level + r0[2] + " for " + mins + " minutes")
        : rep === "date" ? "it is " + at + " on " + (date ? Time.day(date) + " " + Time.d(date).getFullYear() : "a date you pick") : "it is " + at + " on " + dayText
    readonly property var picked: Fleet.machines.filter(function (m) { return page.hosts.indexOf(m.pc_id) >= 0 })
    readonly property string onTxt: all ? "every one of your " + Fleet.machines.length + " machines" : picked.length ? Theme.listNames(picked.map(function (m) { return m.host }), 4) : "the machines you pick"
    readonly property string sug: kind === "Event" ? (ev === "prog" ? (prog.trim() || "A program") + " starts" : ({ usb: "USB device inserted", printer: "Printer stops responding", night: "Sign-in outside working hours", restricted: "Restricted file turns up" })[ev])
        : kind === "Threshold" ? (rd === "signin" ? "Several failed sign-ins" : rd === "disk" ? "Disk nearly full" : "High " + r0[1] + " for " + mins + " min")
        : rep === "date" ? "One-off at " + at + (date ? " on " + Time.day(date) : "") : (days.length === 7 ? "Daily" : dayText === "a weekday" ? "Weekdays" : days.map(function (d) { return page.dayWords[d] }).join(", ") || "Days") + " at " + at
    function free(b) { var n = b, k = 2; while (taken.indexOf(n.toLowerCase()) >= 0) n = b + " (" + (k++) + ")"; return n }
    readonly property bool dup: taken.indexOf(name.trim().toLowerCase()) >= 0
    prob: step === 0 && !name.trim() ? "Give the rule a name." : step === 0 && dup ? "Another rule already has that name." : step === 0 && kind === "Event" && ev === "prog" && !prog.trim() ? "Name the program."
          : step === 0 && kind === "Schedule" && rep === "days" && !days.length ? "Pick at least one day." : step === 0 && kind === "Schedule" && rep === "date" && !date ? "Pick the date."
          : step === 1 && !all && !hosts.length ? "Pick at least one machine." : step === 2 && !acts.length ? "Add at least one action." : ""

    readonly property string type: kind === "Event" ? evs.filter(function (e) { return e[0] === page.ev })[0][4] : kind === "Threshold" ? r0[8] : rep === "date" ? "time.scheduled" : "time.recurring"
    readonly property var match: kind === "Threshold" ? (rd === "signin" ? { count: level, window_s: mins * 60 } : { percent: level, duration_s: mins * 60 })
        : kind === "Schedule" ? (rep === "date" ? { at: atOn() } : { at: at, days: days })
        : ev === "prog" ? { process: prog.trim() } : ev === "night" ? { outside_hours: true } : {}
    function atOn() { var d = Time.d(date); if (!d) return null; var p = at.split(":"); d = new Date(d.getTime()); d.setHours(Number(p[0]), Number(p[1]), 0, 0); return d.toISOString() }

    Component.onCompleted: {
        falcon.call("control.action_list", {}, function (ok, r) {
            var a = ok ? (r.actions || {}) : {}, out = []
            ;["control", "monitoring", "custom"].forEach(function (k) { (a[k] || []).forEach(function (x) { out.push(Object.assign({ cat: k }, x)) }) })
            page.lib = out
            if (!page.editId && !page.acts.length) { var s = out.filter(function (x) { return x.name === "Take a screenshot" })[0]; if (s) page.acts = [{ id: s.id, name: s.name, limit: s.timeout_seconds || 30 }] }
        })
        falcon.call("control.event_list", {}, function (ok, r) {
            var es = ok ? (r.events || []) : []
            page.taken = es.filter(function (e) { return e.id !== page.editId }).map(function (e) { return Auto.nameOf(e).toLowerCase() })
            var e = es.filter(function (x) { return x.id === page.editId })[0]
            if (e) page.load(e)
        })
    }
    // fill it from the rule being edited
    function load(e) {
        var s = e.condition_spec || {}, m = s.match || {}
        original = e
        name = e.name || ""
        kind = Auto.kind(s.type)
        if (kind === "Event") { var hit = evs.filter(function (x) { return x[4] === s.type })[0]; if (hit) ev = hit[0]; if (m.process) prog = m.process }
        if (kind === "Threshold") { var q = reads.filter(function (x) { return x[8] === s.type })[0]; if (q) rd = q[0]; lv = m.percent || m.count || null; mins = Math.round((m.duration_s || m.window_s || 300) / 60) }
        if (s.type === "time.recurring") { at = m.at || "09:00"; days = m.days && m.days.length ? m.days : [0, 1, 2, 3, 4, 5, 6]; rep = "days" }
        if (s.type === "time.scheduled") { rep = "date"; date = m.at; at = Time.hhmm(m.at) }
        all = !(s.pc_ids && s.pc_ids.length)
        hosts = s.pc_ids || []
        acts = (e.actions || []).map(function (a) { return { id: a.id, name: a.name, limit: a.timeout_seconds || 30 } })
    }
    function move(i, d) { var xs = acts.slice(), j = i + d; if (j < 0 || j >= xs.length) return; var t = xs[i]; xs[i] = xs[j]; xs[j] = t; acts = xs }
    onConfirmed: {
        var pcs = all ? null : hosts, limits = {}, n = name.trim()
        acts.forEach(function (a) { limits[a.id] = a.limit })
        var done = function (ok, r) {
            if (!ok) { Msg.failed(r && r.message ? r.message : "Not saved"); return }
            Msg.ok(page.editId ? n + " saved" : n + " is switched on"); Nav.go("automation")
        }
        var ids = acts.map(function (a) { return a.id })
        if (editId) falcon.call("control.event_update", { event_id: editId, match: match, pc_ids: pcs, action_ids: ids, action_limits: limits, name: n }, done)
        else falcon.call("control.event_create", { type: type, match: match, pc_ids: pcs, action_ids: ids, action_limits: limits, enabled: true, name: n }, done)
    }

    function part(t, on) { return "<font color='" + (on ? Theme.accent : Theme.text) + "'>" + t + "</font>" }
    function quiet(t) { return "<font color='" + Theme.text3 + "'>" + t + "</font>" }
    head: Txt {
        objectName: "ruleSentence"
        width: parent.width
        textFormat: Text.StyledText
        wrapMode: Text.WordWrap; elide: Text.ElideNone
        font.pixelSize: 17; font.weight: Font.Medium; lh: 1.45
        text: page.quiet("When") + " " + page.part(page.whenTxt, page.step === 0) + " " + page.quiet("on") + " " + page.part(page.onTxt, page.step === 1) + page.quiet(", do") + " "
              + page.part(page.acts.length ? page.acts.map(function (x) { return x.name }).join(", ") : "…", page.step === 2)
    }

    // --- when it starts --------------------------------------------------------------------------------------------------------------
    NfSec { visible: page.step === 0; first: true; title: "What do you call it?"; note: "The name you give it is how it shows in Your rules, in Recent runs today and in Coming up."
        Field { width: parent.width; text: page.name; placeholderText: "For example Midday backup"; maximumLength: 60; onTextEdited: page.name = text }
        Link { visible: !page.name.trim(); text: "Suggest one from what I set"; font.pixelSize: 13; onClicked: page.name = page.free(page.sug) } }
    NfSec { visible: page.step === 0; title: "How does it start?"
        NfPick { title: "When something happens"; desc: "A machine reports it the moment it happens."; on: page.kind === "Event"; onPicked: page.kind = "Event" }
        NfPick { title: "When a reading crosses a line"; desc: "Checked on each machine every 30 seconds."; on: page.kind === "Threshold"; onPicked: page.kind = "Threshold" }
        NfPick { title: "At a time"; desc: "The Engine starts it on time, on every machine you pick."; on: page.kind === "Schedule"; onPicked: page.kind = "Schedule" } }
    NfSec { visible: page.step === 0 && page.kind === "Event"; title: "What happens?"
        Column { width: parent.width; spacing: 4
            Repeater { model: page.evs
                RnRow { required property var modelData; title: modelData[1]; desc: modelData[3]; icon: modelData[2]; on: page.ev === modelData[0]; onPicked: page.ev = modelData[0] } } }
        Column { visible: page.ev === "prog"; width: parent.width; spacing: 5
            Txt { text: "The program"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
            Field { width: parent.width; text: page.prog; placeholderText: "For example torrent.exe"; onTextEdited: page.prog = text } } }
    NfSec { visible: page.step === 0 && page.kind === "Threshold"; title: "Which reading?"
        Column { width: parent.width; spacing: 4
            Repeater { model: page.reads
                RnRow { required property var modelData; title: modelData[1].charAt(0).toUpperCase() + modelData[1].slice(1); icon: modelData[0] === "signin" ? "lock" : modelData[0] === "disk" ? "hdd" : "dashboard"
                        on: page.rd === modelData[0]; onPicked: { page.rd = modelData[0]; page.lv = null } } } }
        Rectangle {
            width: parent.width; height: rc.height + 30; radius: 8; color: Theme.surface2
            Column { id: rc; x: 16; y: 14; width: parent.width - 32; spacing: 12
                Column { width: parent.width; spacing: 5
                    Txt { text: page.rd === "signin" ? "How many failed sign-ins" : "The line, between " + page.r0[3] + page.r0[2] + " and " + page.r0[4] + page.r0[2]; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                    Item { width: parent.width; height: 40
                        AntSlider { width: parent.width - 72; from: page.r0[3]; to: page.r0[4]; stepSize: page.r0[6]; value: page.level; marks: [page.r0[3] + page.r0[2], page.r0[4] + page.r0[2]]; onMoved: function (v) { page.lv = v } }
                        Txt { anchors.right: parent.right; y: 2; text: page.level + page.r0[2]; font.pixelSize: 15; font.weight: Font.DemiBold; elide: Text.ElideNone } } }
                Column { width: parent.width; spacing: 5
                    Txt { text: page.rd === "signin" ? "Within" : "For at least"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                    Segmented { small: false; options: [1, 5, 10, 30].map(function (v) { return { value: v, label: v + " min" } }); value: page.mins; onPicked: function (v) { page.mins = v } } } } } }
    NfSec { visible: page.step === 0 && page.kind === "Schedule"; title: "When?"
        Rectangle {
            width: parent.width; height: sc.height + 30; radius: 8; color: Theme.surface2
            Column { id: sc; x: 16; y: 14; width: parent.width - 32; spacing: 12
                component Chip: Rectangle { id: ch; property bool on: false; property string text: ""; property bool mono: false; property int least: 0; signal hit()
                    width: Math.max(least, cw.implicitWidth + 26); height: 30; radius: 6; color: on ? Theme.accentSoft : "transparent"; border.width: 1; border.color: on ? Theme.accent : Theme.borderStrong
                    Txt { id: cw; anchors.centerIn: parent; text: ch.text; mono: ch.mono; font.pixelSize: 13; color: ch.on ? Theme.accent : Theme.text2; elide: Text.ElideNone }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: ch.hit() } }
                Column { width: parent.width; spacing: 5
                    Txt { text: "At"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                    Row { spacing: 6
                        Repeater { model: ["07:00", "09:00", "12:00", "17:00", "20:00"]
                            Chip { required property var modelData; text: modelData; mono: true; on: page.at === modelData; onHit: page.at = modelData } }
                        Select { small: true; search: true; width: 100; anchors.verticalCenter: parent.verticalCenter; value: page.at; onPicked: function (v) { page.at = v }
                                 options: { var o = []; for (var i = 0; i < 48; i++) o.push(Time.pad(Math.floor(i / 2)) + ":" + (i % 2 ? "30" : "00")); return o } } } }
                Column { width: parent.width; spacing: 5
                    Txt { text: "Repeats"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                    Segmented { small: false; options: [{ value: "days", label: "On days of the week" }, { value: "date", label: "Once, on a date" }]; value: page.rep; onPicked: function (v) { page.rep = v } } }
                Item { visible: page.rep === "days"; width: parent.width; height: 30
                    Row { spacing: 6
                        Repeater { model: page.dayWords
                            Chip { required property var modelData; required property int index; text: modelData; least: 50; on: page.days.indexOf(index) >= 0
                                   onHit: page.days = on ? page.days.filter(function (d) { return d !== index }) : page.days.concat([index]).sort() } } }
                    Row { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 16
                        Link { text: "Weekdays"; font.pixelSize: 13; onClicked: page.days = [0, 1, 2, 3, 4] }
                        Link { text: "Every day"; font.pixelSize: 13; onClicked: page.days = [0, 1, 2, 3, 4, 5, 6] } } }
                DateTimeField { visible: page.rep === "date"; width: 240; value: page.date; placeholder: "Pick the date"; onChanged: function (iso) { page.date = iso } } } } }

    // --- which machines ---------------------------------------------------------------------------------------------------------------
    NfSec { visible: page.step === 1; first: true; title: "On which machines?"
        NfPick { title: "Every machine (" + Fleet.machines.length + ")"; desc: "Machines added later are included."; on: page.all; onPicked: page.all = true }
        NfPick { title: "The ones you pick"; desc: "Only these; a machine added later is not."; on: !page.all; onPicked: page.all = false } }
    NfSec { visible: page.step === 1 && !page.all
        Item { width: parent.width; height: 20
            Txt { text: page.hosts.length ? page.hosts.length + " picked" : "Pick machines"; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideNone }
            Link { anchors.right: parent.right; font.pixelSize: 13; text: page.hosts.length === Fleet.machines.length ? "Clear" : "All of them"
                   onClicked: page.hosts = page.hosts.length === Fleet.machines.length ? [] : Fleet.machines.map(function (m) { return m.pc_id }) } }
        Column { width: parent.width; spacing: 4
            Repeater { model: Fleet.machines
                RnRow { required property var modelData; check: true; mono: true; title: modelData.host; desc: (modelData.user || "nobody signed in") + (modelData.online ? "" : " · offline")
                        on: page.hosts.indexOf(modelData.pc_id) >= 0
                        onPicked: page.hosts = on ? page.hosts.filter(function (h) { return h !== modelData.pc_id }) : page.hosts.concat([modelData.pc_id]) } } } }

    // --- what it does -------------------------------------------------------------------------------------------------------------------
    NfSec { visible: page.step === 2; first: true; title: "What runs, in this order"; note: "Each action runs on its own; one that runs out of time is stopped and reported."
        Repeater { model: page.acts
            delegate: Rectangle {
                id: st
                required property var modelData
                required property int index
                readonly property var lb: page.lib.filter(function (y) { return y.id === modelData.id })[0] || null
                readonly property int cap: Math.max(60, (lb ? lb.timeout_seconds || 30 : 30) * 4)
                width: parent.width; height: sb.height + 24; radius: 8; color: Theme.surface2
                Rectangle { x: 14; y: 13; width: 24; height: 24; radius: 12; color: Theme.accentSoft
                            Txt { anchors.centerIn: parent; text: st.index + 1; font.pixelSize: 12; font.weight: Font.DemiBold; color: Theme.accent; elide: Text.ElideNone } }
                Column { id: sb; x: 52; y: 12; width: parent.width - 66; spacing: 6
                    Item { width: parent.width; height: Math.max(tt.height, 24)
                        Column { id: tt; width: parent.width - 90; spacing: 1
                            Txt { width: parent.width; text: st.modelData.name; font.pixelSize: 13; font.weight: Font.DemiBold }
                            Txt { visible: !!st.lb; width: parent.width; text: st.lb ? st.lb.description || "" : ""; color: Theme.text3; font.pixelSize: 13 } }
                        Row { anchors.right: parent.right; spacing: 2
                            Btn { small: true; kind: "text"; iconName: "up"; enabled: st.index > 0; onClicked: page.move(st.index, -1) }
                            Btn { small: true; kind: "text"; iconName: "down"; enabled: st.index < page.acts.length - 1; onClicked: page.move(st.index, 1) }
                            Btn { small: true; kind: "text"; iconName: "close"; onClicked: page.acts = page.acts.filter(function (_, j) { return j !== st.index }) } } }
                    Item { width: parent.width; height: 22
                        Txt { id: gl; anchors.verticalCenter: parent.verticalCenter; text: "Gets up to"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                        AntSlider { x: gl.width + 16; width: parent.width - x - 72; from: 5; to: st.cap; stepSize: 5; value: Math.min(st.cap, st.modelData.limit)
                                    onMoved: function (v) { page.acts = page.acts.map(function (y, j) { return j === st.index ? Object.assign({}, y, { limit: v }) : y }) } }
                        Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: st.modelData.limit + "s"; font.pixelSize: 15; font.weight: Font.DemiBold; elide: Text.ElideNone } } }
            } }
        Rectangle { visible: page.acts.length === 0; width: parent.width; height: 54; radius: 8; color: "transparent"
                    DashBox { radius: 8 }
                    Txt { anchors.centerIn: parent; text: "Nothing yet. Add the first action below."; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone } }
        Btn { readonly property bool shut: page.addOpen || !page.acts.length; iconName: shut ? "up" : "plus"; text: shut ? "Close the list" : "Add an action"; onClicked: page.addOpen = !shut } }
    Column {
        visible: page.step === 2 && (page.addOpen || !page.acts.length)
        width: parent.width
        spacing: 8
        topPadding: 8
        Rectangle { width: parent.width; height: 1; color: Theme.border }
        Item { width: 1; height: 8 }
        Field { width: parent.width; iconName: "search"; text: page.aq; placeholderText: "Search the actions"; onTextEdited: page.aq = text }
        Repeater {
            model: [["control", "Do something on the machine"], ["monitoring", "Look at the machine"], ["custom", "Your own scripts"]]
            delegate: Column {
                id: ag
                required property var modelData
                readonly property var hits: page.lib.filter(function (x) { return x.cat === modelData[0] && (!page.aq.trim() || (x.name + " " + (x.description || "")).toLowerCase().indexOf(page.aq.trim().toLowerCase()) >= 0) })
                visible: hits.length > 0
                width: parent.width
                spacing: 2
                topPadding: 8
                Txt { topPadding: 6; text: ag.modelData[1]; color: Theme.text2; font.pixelSize: 12; font.weight: Font.DemiBold; elide: Text.ElideNone }
                Repeater { model: ag.hits.slice(0, 6)
                    delegate: Item {
                        id: ar
                        required property var modelData
                        readonly property bool has: page.acts.some(function (y) { return y.id === modelData.id })
                        width: ag.width; height: ac2.height + 17
                        Column { id: ac2; y: 8; width: parent.width - 80; spacing: 1; opacity: ar.has ? 0.55 : 1
                            Txt { width: parent.width; text: ar.modelData.name; font.pixelSize: 13; font.weight: Font.DemiBold }
                            Txt { width: parent.width; text: ar.modelData.description || ""; color: Theme.text3; font.pixelSize: 13 } }
                        Txt { visible: ar.has; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "Added"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
                        Btn { visible: !ar.has; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; small: true; text: "Add"
                              onClicked: page.acts = page.acts.concat([{ id: ar.modelData.id, name: ar.modelData.name, limit: ar.modelData.timeout_seconds || 30 }]) }
                        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.grid }
                    } }
                Txt { visible: ag.hits.length > 6; topPadding: 6; text: (ag.hits.length - 6) + " more; search to find them"; color: Theme.text3; font.pixelSize: 13; elide: Text.ElideNone }
            }
        }
    }

    // --- check and switch on ------------------------------------------------------------------------------------------------------------
    NfSec { visible: page.step === 3; first: true
        FactRows { rows: [["Called", page.name.trim()], ["Starts", page.whenTxt], ["On", page.onTxt],
                          ["Does", page.acts.map(function (x, i) { return (i + 1) + ". " + x.name + " (" + x.limit + "s)" }).join("  ")], ["Set by", "you"]] } }
    Decide { visible: page.step === 3; text: "It is switched on when you confirm. Every time it runs shows under Recent runs today." }
}
