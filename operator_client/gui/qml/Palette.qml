import QtQuick
import QtQuick.Controls.Basic
import "."

// SEARCH, WHICH IS A JUMP (Ctrl K or Ctrl P): pages, machines, issues, tasks, flows, a few things to do, and at the
// Super User's level departments and rules. At most five per group; the rest are counted, and a sharper query finds
// them. Arrows move (and the list follows), Enter opens, Esc closes. Two letters or more ask the Engine (search.find),
// which finds only what this console may see. Start with ">" (Ctrl Shift P) to see only what can be done: the
// commands, the pages, and starting something new.
Popup {
    id: root
    objectName: "palette"
    parent: Overlay.overlay
    x: (parent.width - width) / 2
    y: parent.height * 0.12
    width: Math.min(640, parent.width - 32)
    height: input.height + Math.min(360, list.contentHeight + 12) + 2
    padding: 0
    clip: true
    modal: true
    dim: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    Overlay.modal: Rectangle { color: Theme.scrimLight }

    property var machines: []
    property var depts: []
    property var found: []             // search.find for the query
    property int at: 0
    onAtChanged: if (list.count > 0) list.positionViewAtIndex(Math.min(at, list.count - 1), ListView.Contain)
    // open with something already typed: ">" for the commands
    property string pending: ""
    function openWith(prefix) { pending = prefix || ""; open() }
    readonly property bool commands: input.text.charAt(0) === ">"
    Timer { id: ask; interval: 150; onTriggered: {
        var q = input.text.trim()
        if (q.length < 2) { root.found = []; return }
        falcon.call("search.find", { q: q, kinds: Nav.boss ? ["machine", "issue", "department", "task", "flow", "rule"] : ["machine", "issue", "task", "flow"], limit: 25 }, function (ok, r) { if (ok && r.q === q) root.found = r.results || [] })
    } }

    onOpened: {
        input.text = pending; pending = ""; at = 0; input.forceActiveFocus(); input.cursorPosition = input.text.length
        falcon.call("hierarchy.tree", {}, function (ok, r) {
            if (!ok) { if (root.machines.length === 0) root.machines = Fleet.cachedMachines(); return }
            var ms = [], ds = r.departments || []
            for (var i = 0; i < ds.length; i++)
                for (var k = 0; k < (ds[i].workers || []).length; k++) {
                    var w = ds[i].workers[k]
                    ms.push({ host: w.hostname, sub: (w.name || "no user") + " · " + ds[i].name + (w.online === false ? " · offline" : "") })
                }
            root.machines = ms
            root.depts = ds.map(function (d) { return { id: d.department_id, name: d.name, admins: (d.admins || []).map(function (a) { return a.name }) } })
        })
    }

    readonly property var items: {
        var cmd = commands, q = (cmd ? input.text.slice(1) : input.text).trim().toLowerCase(), out = [], extra = {}, seen = {}
        var all = [], asked = !cmd && input.text.trim().length >= 2
        for (var g = 0; g < Nav.menu.length; g++)
            for (var i = 0; i < Nav.menu[g][1].length; i++) {
                var m = Nav.menu[g][1][i]
                all.push({ g: "Go to", l: m[1], icon: m[2], page: m[0], sub: null })
            }
        if (asked) {
            // what the Engine found, in the concept's groups; each opens where the Engine says, at this level
            found.forEach(function (x) {
                if (x.kind === "machine") { var fm = Fleet.byHost[x.title]
                    all.push({ g: "Machines", l: x.title, s: (fm ? (fm.user || "no user") + " · " + Fleet.words[fm.status] : x.sub), icon: "desktop", mono: true, page: Nav.boss ? "registry" : "machines", sub: x.title }) }
                else if (x.kind === "issue") all.push({ g: "Issues", l: x.title, s: x.sub, icon: "alert", page: Nav.boss ? "departments" : "issues", sub: Nav.boss ? x.department_id : x.id })
                else if (x.kind === "task") all.push({ g: "Tasks", l: x.title, s: x.sub, icon: "checkcircle", page: "tasks", sub: null })
                else if (x.kind === "flow") all.push({ g: "Flows", l: x.title, s: x.sub, icon: "branches", mono: true, page: "flows", sub: String(x.id) })
                else if (x.kind === "rule" && Nav.boss) all.push({ g: "Rules", l: x.title, s: x.sub, icon: "bolt", page: "rules", sub: x.sub })
                else if (x.kind === "department" && Nav.boss) all.push({ g: "Departments", l: x.title, s: x.sub, icon: "apartment", page: "departments", sub: x.id })
            })
        } else if (!cmd) {
            for (var k = 0; k < machines.length; k++)
                all.push({ g: "Machines", l: machines[k].host, s: machines[k].sub, icon: "desktop", mono: true, page: Nav.boss ? "registry" : "machines", sub: machines[k].host })
            if (Nav.boss)
                for (var d = 0; d < depts.length; d++)
                    all.push({ g: "Departments", l: depts[d].name, s: depts[d].admins.length ? Theme.listNames(depts[d].admins) : "no Admin",
                               icon: "apartment", page: "departments", sub: depts[d].id })
        }
        // a few things to do: leave the session you hold; at an Admin's level, run an action once
        var held = falcon.traversing && falcon.session ? Fleet.byPc[falcon.session.pc_id] : null
        if (held) all.push({ g: "Actions", l: "Leave your session on " + held.host, s: held.user ? held.user + " gets the machine back" : "nobody is waiting for it", icon: "logout", leave: true })
        all.push({ g: "Commands", l: "New task", s: "describe the work; @ marks a person, file, folder, program or deadline", icon: "plus", page: "tasks", sub: "new" })
        if (!Nav.boss) {
            all.push({ g: "Commands", l: "New flow", s: "a one-way sync from a folder to others", icon: "plus", page: "flows", sub: "new" })
            all.push({ g: "Commands", l: "New rule", s: "an event, a condition, an action", icon: "plus", page: "automation", sub: "new" })
        }
        if (!Nav.boss) all.push({ g: "Actions", l: "Run an action once…", s: "pick it on Actions, then Run once", icon: "playcircle", page: "actions", sub: null })
        for (var j = 0; j < all.length; j++) {
            var x = all[j]
            if (!(asked && (x.g === "Machines" || x.g === "Issues" || x.g === "Departments" || x.g === "Tasks" || x.g === "Flows" || x.g === "Rules")) && (x.l + " " + (x.s || "") + " " + x.g).toLowerCase().indexOf(q) < 0) continue
            seen[x.g] = (seen[x.g] || 0) + 1
            if (seen[x.g] <= 5 || x.g === "Go to") out.push(x); else extra[x.g] = (extra[x.g] || 0) + 1
        }
        for (var gg in extra)
            out.push({ g: gg, l: "+" + extra[gg] + " more " + gg.toLowerCase(), s: "type more to narrow, or open the full list",
                       icon: "ellipsis", page: gg === "Machines" ? (Nav.boss ? "registry" : "machines") : gg === "Issues" ? (Nav.boss ? "departments" : "issues") : gg === "Tasks" ? "tasks" : gg === "Flows" ? "flows" : gg === "Rules" ? "rules" : "departments", sub: null })
        if (cmd) {           // in command mode what can be done comes first, then the pages
            var rank = { "Commands": 0, "Actions": 1 }
            out = out.map(function (x, i) { return { x: x, i: i } }).sort(function (a, b) {
                var ra = rank[a.x.g] === undefined ? 2 : rank[a.x.g], rb = rank[b.x.g] === undefined ? 2 : rank[b.x.g]
                return ra - rb || a.i - b.i }).map(function (e) { return e.x })
        }
        return out
    }
    function pick(x) {
        if (!x) return
        if (x.leave) { var h = Fleet.byPc[falcon.session.pc_id]
                       falcon.call("hierarchy.end_session", { session_id: falcon.session.session_id }, function (ok, r) { if (ok) Msg.ok("Left " + (h ? h.host : "the machine")); else Msg.failed(r.message || "Could not leave") })
                       close(); return }
        Nav.go(x.page, x.sub); close()
    }

    background: Rectangle {
        radius: Theme.radiusLg
        color: Theme.surface
        border.width: 1
        border.color: Theme.borderStrong
    }

    TextField {
        id: input
        width: parent.width
        height: 50
        leftPadding: 16
        font.family: Theme.sans
        font.pixelSize: Theme.fLead
        color: Theme.text
        placeholderText: root.commands ? "Type a command, or a page to go to" : (Nav.boss ? "Jump to a page, machine, issue, task or flow. Type > for commands" : "Jump to a page, machine, issue, task or flow. Type > for commands")
        placeholderTextColor: Theme.text4
        background: Rectangle { color: "transparent"; Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border } }
        onTextChanged: { root.at = 0; ask.restart() }
        Keys.onDownPressed: root.at = Math.min(root.items.length - 1, root.at + 1)
        Keys.onUpPressed: root.at = Math.max(0, root.at - 1)
        Keys.onReturnPressed: root.pick(root.items[root.at])
        Keys.onEnterPressed: root.pick(root.items[root.at])
    }
    ListView {
        id: list
        anchors.top: input.bottom
        anchors.topMargin: 6
        x: 6
        width: parent.width - 12
        height: Math.min(360, contentHeight)
        clip: true
        model: root.items
        delegate: Column {
            required property var modelData
            required property int index
            width: list.width
            Txt {
                visible: index === 0 || root.items[index - 1].g !== modelData.g
                text: modelData.g.toUpperCase()
                color: Theme.text4
                font.pixelSize: 11
                font.weight: Font.DemiBold
                font.letterSpacing: 0.6
                leftPadding: 10
                topPadding: 8
                bottomPadding: 2
                height: visible ? implicitHeight : 0
            }
            Rectangle {
                width: parent.width
                height: 32
                radius: 5
                color: index === root.at ? Theme.accentSoft : "transparent"
                Row {
                    x: 10
                    spacing: 10
                    anchors.verticalCenter: parent.verticalCenter
                    Icon { name: modelData.icon; size: 14; color: Theme.text3; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: modelData.l; mono: !!modelData.mono; elide: Text.ElideNone; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: modelData.s || ""; color: Theme.text3; font.pixelSize: Theme.fSmall; anchors.verticalCenter: parent.verticalCenter; width: 320 }
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: root.at = index
                    onClicked: root.pick(modelData)
                }
            }
        }
        Txt { visible: root.items.length === 0; text: "No matches."; color: Theme.text3; x: 12; y: 8 }
        footer: Txt { objectName: "paletteAsOf"; visible: Fleet.asOf !== ""; width: list.width; text: visible ? Fleet.asOf : ""; color: Theme.text4; font.pixelSize: 11
                      leftPadding: 10; topPadding: 6; bottomPadding: 4; height: visible ? implicitHeight : 0 }
    }
}
