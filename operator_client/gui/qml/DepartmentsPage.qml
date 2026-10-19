import QtQuick
import "."

// DEPARTMENTS, AT THE SUPER USER'S LEVEL: the organisation as a card a department, each with who looks after it and how its machines and issues stand. A view, not a workbench: what
// happens inside a department is its Admin's work, and the Super User gets there by entering the Admin's console. What is theirs to do here is the structure: make a department,
// give it an Admin, and go into an Admin's console. (The tab beside this one holds what the Engine keeps for the Super User alone.)
Page {
    id: page
    objectName: "departmentsView"

    property var d: null                         // the department an Assign an Admin is for
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
    readonly property int admins: Fleet.depts.reduce(function (a, x) { return a + x.admins.length }, 0)
    readonly property int off: Fleet.machines.filter(function (m) { return !m.online }).length
    readonly property var markTone: ({ quiet: Theme.ok, watch: Theme.med, high: Theme.crit, crit: Theme.crit, offline: Theme.text4 })
    function segsOf(d) {
        var c = { quiet: 0, watch: 0, high: 0, crit: 0, offline: 0 }
        d.machines.forEach(function (m) { c[Fleet.mark(m.status)] += 1 })
        return [{ n: c.quiet, c: Theme.ok }, { n: c.watch, c: Theme.med }, { n: c.high + c.crit, c: Theme.crit }, { n: c.offline, c: Theme.text4 }]
    }

    // --- the head: one line, and the one thing to make -----------------------------------------------------------------------------------------------------------
    Item {
        width: parent.width
        height: 34
        Row {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 18
            Txt { text: Theme.many(Fleet.depts.length, "department"); font.weight: Font.DemiBold; elide: Text.ElideNone }
            Txt { text: Theme.many(page.admins, "Admin"); color: Theme.text2; elide: Text.ElideNone }
            Txt { text: Theme.fmt(Fleet.machines.length - page.off) + " of " + Theme.fmt(Fleet.machines.length) + " machines online"; color: page.off ? Theme.crit : Theme.text2; elide: Text.ElideNone }
        }
        Btn { objectName: "newDepartment"; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; kind: "primary"; iconName: "plus"; text: "New department"; onClicked: newDept.open() }
    }

    PageTabs { options: [{ value: "departments", label: "Departments" }, { value: "registry", label: "Refused connections" }]; current: "departments" }

    // --- a card a department -------------------------------------------------------------------------------------------------------------------------------------
    Grid {
        objectName: "deptCards"
        width: parent.width
        columns: 2
        columnSpacing: 14
        rowSpacing: 14
        Repeater {
            model: page.all
            DeptCard {
                required property var modelData
                width: (page.w - 14) / 2
                title: modelData.name
                sub: modelData.admins.length ? Theme.listNames(modelData.admins.map(function (a) { return a.name })) : ""
                noAdmin: modelData.admins.length === 0
                segs: page.segsOf(modelData)
                total: Theme.many(modelData.machines.length, "machine")
                Column {
                    width: parent.width
                    DeptLine { dot: modelData.online < modelData.machines.length ? Theme.crit : Theme.ok; text: "Machines online"; aside: modelData.online + " of " + modelData.machines.length; asideTone: modelData.online < modelData.machines.length ? Theme.crit : Theme.text3 }
                    DeptLine { dot: modelData.crit ? Theme.crit : modelData.high ? Theme.med : Theme.ok; text: "Open issues"; aside: modelData.iss.length ? modelData.iss.length + (modelData.crit ? " · " + modelData.crit + " critical" : "") : "none"
                               asideTone: modelData.crit ? Theme.crit : Theme.text3 }
                    DeptLine { dot: modelData.ok < modelData.machines.length ? Theme.med : Theme.ok; text: "On the current version"; aside: modelData.ok + " of " + modelData.machines.length }
                    Item { width: 1; height: 8 }
                    Row {
                        spacing: 8
                        Btn { visible: modelData.admins.length === 0; kind: "primary"; iconName: "useradd"; text: "Assign an Admin"; onClicked: { page.d = modelData; assign.who = null; assign.open() } }
                        Btn { visible: modelData.admins.length === 1; kind: "primary"; iconName: "login"; text: "Enter " + (modelData.admins.length ? modelData.admins[0].name : "") + "'s console →"; onClicked: Nav.enter(modelData.admins[0], null) }
                        Btn { visible: modelData.admins.length > 1; kind: "primary"; iconName: "login"; text: "Enter a console…"; onClicked: admins.openFor(modelData, null) }
                    }
                }
            }
        }
    }
    Empty { visible: Fleet.loaded && Fleet.depts.length === 0; width: parent.width; h: 200; icon: "apartment"; title: "No departments yet"; text: "Create a department, then give it an Admin and its machines."; act: "New department"; onActed: newDept.open() }

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
