import QtQuick
import "."

// DEPARTMENTS, AT THE SUPER USER'S LEVEL: the departments, who looks after each (its Admins) and its machines, and the one thing to make: a new department. A view, not a workbench: what
// happens inside a department is its Admin's work, and the Super User gets there by entering the Admin's console. Theirs to do here is the structure: make a department, give it an Admin,
// go into an Admin's console. (The tab beside this one holds what the Engine keeps for the Super User alone.)
Page {
    id: page
    objectName: "departmentsView"

    property var sel: Nav.sub !== null && Nav.sub !== undefined && !isNaN(Number(Nav.sub)) ? Number(Nav.sub) : null
    function rank(d) {
        var iss = Fleet.issues.filter(function (i) { return i.dept === d.id })
        return !d.admins.length ? 0 : iss.some(function (i) { return i.sev === "critical" }) ? 1 : iss.some(function (i) { return i.sev === "high" }) ? 3 : 4
    }
    readonly property var all: Fleet.depts.map(function (d) {
        var iss = Fleet.issues.filter(function (i) { return i.dept === d.id })
        return Object.assign({ iss: iss, online: d.machines.filter(function (m) { return m.online }).length,
                               crit: iss.filter(function (i) { return i.sev === "critical" }).length, high: iss.filter(function (i) { return i.sev === "high" }).length,
                               ok: d.machines.filter(function (m) { return !m.behind }).length, rank: page.rank(d) }, d)
    }).sort(function (a, b) { return a.rank - b.rank })
    readonly property var rows: all.filter(function (d) { return (d.name + " " + d.admins.map(function (a) { return a.name }).join(" ")).toLowerCase().indexOf(list.query.toLowerCase()) >= 0 })
    readonly property var d: { for (var i = 0; i < all.length; i++) if (all[i].id === sel) return all[i]; return rows.length ? rows[0] : null }
    readonly property int admins: Fleet.depts.reduce(function (a, x) { return a + x.admins.length }, 0)
    readonly property int off: Fleet.machines.filter(function (m) { return !m.online }).length

    PageTabs { options: [{ value: "departments", label: "Departments" }, { value: "registry", label: "Refused connections" }]; current: "departments" }

    Strip {
        width: parent.width
        items: [
            { label: "Departments", value: Theme.fmt(Fleet.depts.length), delta: Theme.fmt(page.admins) + " Admins between them" },
            { label: "Without an Admin", value: Theme.fmt(page.all.filter(function (x) { return !x.admins.length }).length),
              delta: page.all.some(function (x) { return !x.admins.length }) ? "their reports come to you" : "every seat filled", dc: page.all.some(function (x) { return !x.admins.length }) ? Theme.crit : undefined },
            { label: "Machines", value: Theme.fmt(Fleet.machines.length), delta: Theme.fmt(Fleet.machines.length - page.off) + " online" + (page.off ? " · " + page.off + " offline" : ""), dc: page.off ? Theme.crit : undefined },
            { label: "Open issues", value: Theme.fmt(Fleet.issues.length), delta: Fleet.issues.filter(function (i) { return i.sev === "critical" }).length + " critical",
              dc: Fleet.issues.some(function (i) { return i.sev === "critical" }) ? Theme.crit : undefined }
        ]
    }

    Row {
        width: parent.width
        spacing: 14
        ListPanel {
            id: list
            width: (parent.width - 14) * 8 / 12
            title: "Departments"
            sub: "what needs you first · click one to see its Admins and machines"
            placeholder: "Filter by department or Admin"
            actionLabel: "New department"
            onAction: newDept.open()
            rows: page.rows
            pick: page.d ? page.d.id : null
            onPicked: function (k) { page.sel = k }
            icon: "apartment"
            nameTitle: "Department"
            nameText: function (r) { return r.name }
            nameLine: function (r) { return Theme.many(r.machines.length, "machine") }
            cols: [{ title: "Admins", width: 200, text: function (r) { return r.admins.length ? Theme.listNames(r.admins.map(function (a) { return a.name })) : "None" } },
                   { title: "Machines online", width: 150, bar: function (r) { return { v: r.online, max: Math.max(1, r.machines.length), text: r.online + "/" + r.machines.length } } }]
            now: function (r) { return !r.admins.length ? ["No Admin", "bad"] : r.crit ? [r.crit + " critical", "bad"] : r.high ? [r.high + " high", "bad"] : r.online < r.machines.length ? [(r.machines.length - r.online) + " offline", "wait"] : ["All well", "good"] }
            showEmpty: Fleet.loaded && Fleet.depts.length === 0
            emptyIcon: "apartment"
            emptyTitle: "No departments yet"
            emptyText: "Create a department, then give it an Admin and its machines."
            emptyAct: "New department"
            onEmptyAction: newDept.open()
        }
        SidePanel {
            width: (parent.width - 14) * 4 / 12
            showEmpty: page.d === null
            emptyIcon: "apartment"
            emptyText: "Pick a department in the list."
            title: page.d ? page.d.name : ""
            sub: page.d && page.sel === page.d.id ? "the one you picked" : "needs you most · click another"
            facts: page.d ? [["Machines", page.d.online + " of " + page.d.machines.length + " online"],
                             ["Open issues", page.d.iss.length ? page.d.iss.length + (page.d.crit ? " · " + page.d.crit + " critical" : "") : "None"],
                             ["On " + (Fleet.version || "current"), page.d.ok + " of " + page.d.machines.length]] : []
            actions: [
                Btn { visible: page.d !== null && !page.d.admins.length; kind: "primary"; iconName: "useradd"; text: "Assign an Admin"; onClicked: { assign.who = null; assign.open() } },
                Btn { visible: page.d !== null && page.d.admins.length === 1; kind: "primary"; iconName: "login"; text: page.d && page.d.admins.length ? "Enter " + page.d.admins[0].name + "'s console →" : ""
                      onClicked: Nav.enter(page.d.admins[0], null) },
                Btn { visible: page.d !== null && page.d.admins.length > 1; kind: "primary"; iconName: "login"; text: "Enter a console…"; onClicked: admins.openFor(page.d, null) }
            ]
            Column {
                width: parent.width
                spacing: 4
                Txt { text: "ADMINS"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Txt { visible: page.d !== null && page.d.admins.length === 0; text: "None · its reports come to you"; color: Theme.crit; font.pixelSize: 12 }
                Repeater {
                    model: page.d ? page.d.admins : []
                    Row {
                        required property var modelData
                        spacing: 8
                        Rectangle { width: 8; height: 8; radius: 4; anchors.verticalCenter: parent.verticalCenter
                                    color: modelData.session && modelData.session.occupied_via === "traversal" ? Theme.ser3 : modelData.online ? Theme.ok : Theme.text4 }
                        Txt { text: modelData.name; elide: Text.ElideNone }
                        Txt { text: modelData.session && modelData.session.occupied_via === "traversal" ? "inside a machine" : modelData.online ? "at their desk" : "not signed in"; color: Theme.text3; font.pixelSize: 12; elide: Text.ElideNone }
                    }
                }
            }
            Column {
                width: parent.width
                spacing: 6
                Txt { text: "MACHINES"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                Txt { visible: page.d !== null && page.d.machines.length === 0; text: "None yet"; color: Theme.text3; font.pixelSize: 12 }
                Flow {
                    width: parent.width
                    spacing: 6
                    Repeater { model: page.d ? page.d.machines.slice(0, 40) : []
                               Row { required property var modelData; spacing: 5
                                     HealthMark { k: Fleet.mark(modelData.status); size: 12; anchors.verticalCenter: parent.verticalCenter }
                                     Txt { text: modelData.host; mono: true; font.pixelSize: 12; elide: Text.ElideNone } } }
                    Txt { visible: page.d !== null && page.d.machines.length > 40; text: "+" + (page.d ? page.d.machines.length - 40 : 0); mono: true; color: Theme.text3; font.pixelSize: 11 }
                }
            }
        }
    }

    // --- the Admins of a department: whose console ---------------------------------------------------
    Drawer {
        id: admins
        page: page
        width: 440
        property var dd: null
        property var to: null
        title: dd ? (to ? "Whose console · " + dd.name : "Admins · " + dd.name) : ""
        function openFor(x, landing) { dd = x; to = landing; open() }
        Txt { width: parent.width; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
              text: admins.dd ? Theme.many(admins.dd.admins.length, "Admin") + "." + (admins.to ? " The issue opens in the console you enter." : "") + " Entering one's console asks first to block or end their session." : "" }
        Column {
            width: parent.width
            Repeater {
                model: admins.dd ? admins.dd.admins : []
                PersonRow { required property var modelData; width: parent.width; name: modelData.name
                            sub: (modelData.session && modelData.session.occupied_via === "traversal" ? "inside a machine" : modelData.online ? "at their desk" : "not signed in") + (modelData.hostname ? " · " + modelData.hostname : "")
                            dot: modelData.session && modelData.session.occupied_via === "traversal" ? Theme.ser3 : modelData.online ? Theme.ok : Theme.text4
                            act: "Enter →"
                            onActed: { var t = admins.to; admins.close(); Nav.enter(modelData, t) } }
            }
        }
    }
    KeyDrawer { id: keys; page: page; onDone: Fleet.refresh() }
    Drawer {
        id: assign
        page: page
        width: 420
        title: page.d ? "Assign an Admin · " + page.d.name : ""
        property var who: null
        footer: [ Btn { text: "Cancel"; onClicked: assign.close() },
                  Btn { kind: "primary"; text: "Assign"; enabled: assign.who !== null
                        onClicked: { var m = page.d.machines.filter(function (x) { return x.account === assign.who })[0]; assign.close()
                                     keys.ask({ mode: "promote", account_id: assign.who, subject: m ? m.user : "They" }) } } ]
        Column {
            width: parent.width; spacing: 6
            Txt { text: "WHO"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
            Select { width: parent.width; search: true; placeholder: "Pick someone"; value: assign.who; onPicked: function (v) { assign.who = v }
                     options: page.d ? page.d.machines.filter(function (m) { return m.user }).map(function (m) { return { value: m.account, label: m.user + " · works on " + m.host + ", promote to Admin" } }) : [] }
        }
        Rectangle {
            width: parent.width; height: an.height + 20; radius: 6; color: Theme.surface2
            Txt { id: an; x: 12; y: 10; width: parent.width - 24; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.text3; font.pixelSize: 12
                  text: "Until " + (page.d ? page.d.name : "it") + " has an Admin, everything from it comes to you: its reports, stuck updates and help requests. Promoting one of its workers gives them a console and a key, shown once; an Admin belongs to one department." }
        }
    }
    Drawer {
        id: newDept
        page: page
        width: 420
        title: "New department"
        property string name: ""
        note: name.trim() === "" ? "Name it." : ""
        footer: [ Btn { text: "Cancel"; onClicked: newDept.close() },
                  Btn { kind: "primary"; text: "Create"; enabled: newDept.name.trim() !== ""
                        onClicked: falcon.call("hierarchy.department_create", { name: newDept.name.trim() }, function (ok, r) {
                            if (!ok) { Msg.failed(r && r.message ? r.message : "Not created"); return }
                            Msg.ok(newDept.name.trim() + " created · give it an Admin next"); newDept.name = ""; newDept.close(); Fleet.refresh() }) } ]
        Column { width: parent.width; spacing: 6
                 Txt { text: "NAME"; color: Theme.text3; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.66 }
                 Field { width: parent.width; text: newDept.name; placeholderText: "Procurement"; onTextEdited: newDept.name = text } }
    }
}
