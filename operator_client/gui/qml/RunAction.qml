import QtQuick
import QtQuick.Controls.Basic
import "."

// RUNNING ONE NOW. It is a detached process on somebody's machine, it starts the moment this closes,
// and a department run is one independent execution per PC. Rule 4: the cost is on the page, in the
// numbers of this particular run, before the verb.
Modal {
    id: root
    width: 480
    title: "Run it now"
    subtitle: root.action ? root.action.name : ""
    closePolicy: root.busy ? Popup.NoAutoClose : Popup.CloseOnEscape

    property var action: null
    property var pcId: null
    property var departmentId: null
    property bool wide: false                 // a whole department rather than one machine
    property bool tried: false
    property bool busy: false
    property string problem: ""
    property var machines: []
    property var departments: []

    signal ran()

    readonly property var machineOptions: machines.map(function (m) {
        return { value: m.pc_id, label: m.hostname + "  ·  " + m.department }
    })
    readonly property var departmentOptions: departments.map(function (d) {
        return { value: d.department_id, label: d.name + "  ·  " + d.count + " machines" }
    })
    readonly property int reach: {
        if (!wide) return pcId === null ? 0 : 1
        for (var i = 0; i < departments.length; i++)
            if (departments[i].department_id === departmentId) return departments[i].count
        return 0
    }
    readonly property string targetProblem:
        wide ? (departmentId === null ? "Pick the department." : "")
             : (pcId === null ? "Pick the machine." : "")

    function reset() {
        pcId = null
        departmentId = null
        wide = false
        where.value = false
        pick.value = null
        deptPick.value = null
        tried = false
        busy = false
        problem = ""
        load()
    }
    onAboutToShow: reset()

    function load() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function (ok, r) {
            if (!ok) return
            var pcs = [], depts = []
            var list = r.departments || []
            for (var i = 0; i < list.length; i++) {
                var people = (list[i].admins || []).concat(list[i].workers || [])
                var n = 0
                for (var j = 0; j < people.length; j++)
                    if (people[j].pc_id) {
                        pcs.push({ pc_id: people[j].pc_id, hostname: people[j].hostname || "a machine",
                                   department: list[i].name })
                        n += 1
                    }
                depts.push({ department_id: list[i].department_id, name: list[i].name, count: n })
            }
            root.machines = pcs
            root.departments = depts
        })
    }

    function run() {
        tried = true
        if (targetProblem !== "" || busy || !action) return
        busy = true
        problem = ""
        var payload = { action_id: action.action_id }
        if (wide) payload.department_id = departmentId
        else payload.pc_id = pcId
        falcon.call("control.action_run", payload, function (ok, r) {
            root.busy = false
            if (!ok) { root.problem = r && r.message ? r.message : "It did not start."; return }
            var n = (r.executions || []).length
            Msg.ok(n > 1 ? "Started on " + n + " machines" : "Started")
            root.ran()
            root.close()
        })
    }

    FormRow {
        width: parent.width
        label: "Where"
        required: true
        Select {
            id: where
            objectName: "runScope"
            width: parent.width
            value: false
            options: [{ value: false, label: "One machine" },
                      { value: true, label: "Every machine in a department" }]
            onPicked: function (v) { root.wide = v }
        }
    }
    FormRow {
        width: parent.width
        visible: !root.wide
        required: true
        label: "Machine"
        problem: root.tried ? root.targetProblem : ""
        Select {
            id: pick
            objectName: "runMachine"
            width: parent.width
            options: root.machineOptions
            placeholder: "Which machine"
            invalid: root.tried && root.pcId === null
            onPicked: function (v) { root.pcId = v }
        }
    }
    FormRow {
        width: parent.width
        visible: root.wide
        required: true
        label: "Department"
        problem: root.tried ? root.targetProblem : ""
        Select {
            id: deptPick
            objectName: "runDepartment"
            width: parent.width
            options: root.departmentOptions
            placeholder: "Which department"
            invalid: root.tried && root.departmentId === null
            onPicked: function (v) { root.departmentId = v }
        }
    }

    Alert {
        width: parent.width
        kind: root.wide ? "warn" : "note"
        text: root.action
              ? ("It starts the moment you press Run, on " + (root.reach === 1 ? "that machine"
                 : root.reach + " machines") + ", and gives up after " + root.action.timeout + ".")
              : ""
    }
    Alert {
        width: parent.width
        visible: root.problem !== ""
        kind: "danger"
        text: root.problem
    }

    footer: [
        Btn {
            text: "Cancel"
            visible: !root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: go.left
            anchors.rightMargin: Theme.s2
            onClicked: root.close()
        },
        Btn {
            id: go
            objectName: "runSubmit"
            kind: "primary"
            danger: root.wide
            text: "Run"
            loading: root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: Theme.s5
            onClicked: root.run()
        }
    ]
}
