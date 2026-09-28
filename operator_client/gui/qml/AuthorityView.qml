import QtQuick
import QtQuick.Layouts
import "."

// THE SUPER USER'S AUTHORITY AREA (board OV03) -- who governs what, and where nobody does.
//
// This replaces the pre-kit "Everything" screen, which was the last surface from before the kit: a
// sidebar, a card strip and a detail card printing account and PC ids. Nothing of it survives.
//
// ITS SIGNATURE IS THREE COLUMNS of unequal width -- neither Must see's quartet nor the department's
// pinwheel -- so you know the page before reading a word: the departments (narrow), the people
// (wide), and a right column of where nobody governs over what you call them.
//
// It is also the only place DISPLAY NAMES are set. A name is private to the namer and never
// propagates across relationship layers (hierarchy-system-design.md), so this page only ever says
// what YOU see and what others see of YOU -- never what one person calls another.
//
// One gesture, as everywhere: single click selects a person and the naming cell follows; double
// click on a department enters it (the crumb grows on the page that opens, not here).
Item {
    id: root

    property var tree: []
    property string clock: ""
    property bool loaded: false
    // the person the naming cell is about; 0 = nobody picked
    property int selectedId: 0
    // what this Super User calls themselves, as last set from here. The Engine has no read for it
    // (only hierarchy.set_self_name), so the page says "your own name" until it is set.
    property string selfName: ""

    readonly property var departments: tree || []
    readonly property var people: {
        var out = []
        for (var i = 0; i < root.departments.length; i++) {
            var d = root.departments[i]
            for (var j = 0; j < (d.admins || []).length; j++) {
                var a = d.admins[j]
                out.push({ account_id: a.account_id, name: a.name, hostname: a.hostname,
                           session: a.session, department_id: d.department_id,
                           department_name: d.name, tint: Theme.series(i) })
            }
        }
        return out
    }
    readonly property var selected: {
        for (var i = 0; i < root.people.length; i++)
            if (root.people[i].account_id === root.selectedId) return root.people[i]
        return null
    }
    readonly property var orphans: root.departments.filter(function (d) { return (d.admins || []).length === 0 })

    readonly property var authoritySays: falcon.narrate("authority", { departments: root.departments })
    readonly property var peopleSays: falcon.narrate("dept_people", {
        admins: root.people, selected: root.selected,
        machines: root.departments.reduce(function (n, d) { return n + (d.workers || []).length }, 0) })
    readonly property var gapSays: falcon.narrate("nobody_governs", { departments: root.departments })
    readonly property var nameSays: falcon.narrate("naming", { selected: root.selected, self_name: root.selfName })

    function refresh() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function (ok, r) {
            root.loaded = true
            if (!ok) { shell.notify(r.message, true); return }
            root.tree = r.departments
        })
    }
    function deptState(d) {
        // the card already says "nobody" and offers the act; a second phrase beside it says nothing twice
        if ((d.admins || []).length === 0) return { word: "", tone: "" }
        for (var i = 0; i < d.admins.length; i++) {
            var s = d.admins[i].session
            if (s && s.occupied_via === "assisted_access")
                return { word: d.admins[i].name + " assisting elsewhere", tone: "accent" }
        }
        return { word: "", tone: "" }
    }
    // a new department is an act with a consequence (it starts with nobody in it), so it asks first
    function newDepartment() {
        shell.ask({ title: "Make a department", lead: "It starts with nobody governing it, and no machines.",
                    body: "Give it an Admin next, or it cannot answer for anything.",
                    field: { label: "What it is called", placeholder: "Logistics" },
                    act: "Make it", actIcon: "plus" }, function (name) {
            falcon.call("hierarchy.department_create", { name: name }, function (ok, r) {
                shell.notify(ok ? r.name + " exists now" : r.message, !ok)
                if (ok) root.refresh()
            })
        })
    }
    function nameThem() {
        if (!root.selected) return
        shell.ask({ title: "What do you call " + root.selected.name + "?",
                    lead: "Only you see this name. It never reaches them, or anyone else.",
                    body: "Clear it to go back to the name they were registered with.",
                    field: { label: "Your name for them", placeholder: root.selected.name },
                    act: "Call them this", actIcon: "check" }, function (label) {
            falcon.call("hierarchy.set_display_name", { account_id: root.selected.account_id, label: label },
                        function (ok, r) {
                            shell.notify(ok ? "You call them " + r.label + " now" : r.message, !ok)
                            if (ok) root.refresh()
                        })
        })
    }
    function nameYourself() {
        shell.ask({ title: "What should people below you see?",
                    lead: "Everyone under you sees this name instead of the one on your account.",
                    field: { label: "Your name to them", placeholder: falcon.roleLabel },
                    act: "Use this name", actIcon: "check" }, function (label) {
            falcon.call("hierarchy.set_self_name", { label: label }, function (ok, r) {
                root.selfName = ok ? (r.label || "") : root.selfName
                shell.notify(ok ? "They see you as " + (r.label || "your own name") : r.message, !ok)
                if (ok) root.refresh()
            })
        })
    }

    Connections {
        target: falcon
        function onConnected() { root.refresh() }
        function onScopeChanged() { if (falcon.isConnected) root.refresh() }
        function onDisconnected() { root.tree = []; root.loaded = false; root.selectedId = 0 }
        function onPushReceived(type, p) {
            if (type.indexOf("session.") === 0 || type.indexOf("assisted_access.") === 0
                    || type === "hierarchy.changed") root.refresh()
        }
    }
    Component.onCompleted: if (falcon.isConnected) refresh()

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 22
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 16

        // --- the head: the rail already says Authority, so this says how it stands, and the time
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 34

            Txt {
                objectName: "authorityPhrase"
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: root.loaded ? root.authoritySays.sentence : ""
                color: root.authoritySays.tone === "danger" ? Theme.danger : Qt.rgba(1, 1, 1, 0.55)
                font.pixelSize: Theme.fBody
            }
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 16
                GBtn {
                    objectName: "newDepartment"
                    text: "New department"
                    iconName: "plus"
                    small: true
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: root.newDepartment()
                }
                Txt {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.clock
                    color: Qt.rgba(1, 1, 1, 0.45)
                    font.pixelSize: Theme.fBody
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 20

            // ============================================================ the departments
            GridCell {
                id: deptCell
                objectName: "authorityDepartments"
                Layout.fillWidth: false
                Layout.preferredWidth: 440
                Layout.fillHeight: true
                topAlign: true
                title: "The departments"
                narration: root.authoritySays
                loading: !root.loaded

                PagedColumn {
                    objectName: "authorityDeptList"
                    width: parent.width
                    height: deptCell.room
                    itemHeight: 58
                    model: root.departments
                    attention: function (d) { return (d.admins || []).length === 0 ? d.name + " has nobody" : "" }
                    delegate: DeptCard {
                        dept: modelData || ({})
                        stamp: Theme.series(index)
                        stateWord: modelData ? root.deptState(modelData).word : ""
                        stateTone: modelData ? root.deptState(modelData).tone : ""
                        onEntered: shell.enterDepartment(modelData.department_id)
                        onAssign: shell.registerMachine(modelData.department_id, modelData.name, "admin")
                    }
                }
            }

            // ============================================================ the people
            GridCell {
                id: peopleCell
                objectName: "authorityPeople"
                Layout.fillWidth: true
                Layout.fillHeight: true
                topAlign: true
                title: "The people"
                narration: root.peopleSays
                loading: !root.loaded

                PagedColumn {
                    objectName: "authorityPeopleList"
                    width: parent.width
                    height: peopleCell.room
                    itemHeight: 58
                    model: root.people
                    attention: function (p) { return p.session ? "" : p.name + " is not signed in" }
                    delegate: InfoCard {
                        property var modelData: null
                        readonly property var p: modelData || ({})
                        width: parent ? parent.width : 0
                        initials: Theme.initials(p.name || "")
                        title: p.name || ""
                        line: (p.department_name || "") + " · "
                              + (p.session ? ((p.session.occupied_via === "assisted_access")
                                              ? "helping another department" : "at their workstation")
                                           : "not signed in")
                        lineTone: p.session && p.session.occupied_via === "assisted_access" ? "accent"
                                  : p.session ? "" : "warn"
                        selected: root.selectedId === p.account_id
                        onClicked: root.selectedId = p.account_id
                        onDoubleClicked: if (p.department_id) shell.enterDepartment(p.department_id)
                    }
                }
            }

            // ============================================================ the right column
            ColumnLayout {
                Layout.fillWidth: false
                Layout.preferredWidth: 400
                Layout.fillHeight: true
                spacing: 20

                // --- where nobody governs: a cell that exists to be empty
                GridCell {
                    id: gapCell
                    objectName: "authorityGap"
                    Layout.fillWidth: true
                    Layout.fillHeight: false
                    Layout.preferredHeight: Math.max(190, root.height * 0.36)
                    topAlign: true
                    title: "Where nobody governs"
                    narration: root.gapSays
                    loading: !root.loaded

                    PagedColumn {
                        objectName: "authorityGapList"
                        width: parent.width
                        height: gapCell.room
                        itemHeight: 58
                        model: root.orphans
                        attention: function (d) { return d.name }
                        delegate: InfoCard {
                            property var modelData: null
                            readonly property var d: modelData || ({})
                            width: parent ? parent.width : 0
                            iconName: "dept"
                            iconTone: "danger"
                            title: d.name || ""
                            line: ((d.workers || []).length === 0 ? "no machines yet"
                                   : (d.workers || []).length === 1 ? "one machine, unattended"
                                   : (d.workers || []).length + " machines, unattended")
                            lineTone: "danger"
                            stateWord: "Assign an Admin"
                            stateTone: "danger"
                            onClicked: shell.registerMachine(d.department_id, d.name, "admin")
                        }
                    }
                    Txt {
                        visible: root.orphans.length === 0 && root.loaded
                        width: parent.width
                        text: root.gapSays.sentence
                        color: Theme.dim
                        font.pixelSize: Theme.fBody
                        wrapMode: Text.WordWrap
                    }
                }

                // --- the names, which are yours alone
                GridCell {
                    objectName: "authorityNaming"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    topAlign: true
                    title: "What you call them"
                    narration: root.nameSays
                    loading: !root.loaded

                    Column {
                        width: parent.width
                        spacing: 14

                        ReadingBody {
                            objectName: "authorityNameReading"
                            width: parent.width
                            narration: root.nameSays
                            maxFacts: 3
                            onActionTriggered: root.nameThem()
                        }
                        Rectangle { width: parent.width; height: 1; color: Theme.line }
                        Txt {
                            width: parent.width
                            text: root.selfName === "" ? "Everyone below you sees the name on your account."
                                                       : "Everyone below you sees " + root.selfName + "."
                            color: Theme.faint
                            font.pixelSize: Theme.fMeta
                            wrapMode: Text.WordWrap
                        }
                        GBtn {
                            objectName: "setSelfName"
                            text: "What they call you"
                            iconName: "user"
                            small: true
                            onClicked: root.nameYourself()
                        }
                    }
                }
            }
        }
    }
}
