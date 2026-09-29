import QtQuick
import QtQuick.Controls.Basic
import "."

// ONE ACCOUNT, ONE PC. Adding a person provisions the machine at the same time, and hands back a key
// the Engine will never print again -- so this form has the same second half as registering a machine
// (rule 13): it turns into the answer instead of closing.
Modal {
    id: root
    width: 520
    title: root.done ? "Added" : "Add a person"
    subtitle: root.done ? "" : "Their machine is provisioned with them. One account, one PC."
    closePolicy: root.busy ? Popup.NoAutoClose : Popup.CloseOnEscape

    property var departments: []
    signal made()

    property string role: "worker"
    property var departmentId: null
    property string hostname: ""
    property bool tried: false
    property bool busy: false
    property string problem: ""
    property var done: null

    readonly property bool boss: falcon.role === "super_user"
    readonly property bool needsDepartment: role !== "super_user"
    readonly property var roleOptions: boss
        ? [{ value: "admin", label: "Admin · governs a department" },
           { value: "worker", label: "Worker · one machine in a department" },
           { value: "super_user", label: "Super User · sees everything" }]
        : [{ value: "worker", label: "Worker · one machine in your department" }]
    readonly property var deptOptions: departments.map(function (d) {
        return { value: d.department_id, label: d.name }
    })

    readonly property string hostProblem:
        hostname.trim() === "" ? "Their machine needs a hostname."
        : hostname.indexOf(" ") >= 0 ? "A hostname has no spaces in it." : ""
    readonly property string deptProblem:
        needsDepartment && departmentId === null ? "Pick the department they belong to." : ""
    readonly property bool valid: hostProblem === "" && deptProblem === ""

    function reset() {
        role = boss ? "admin" : "worker"
        rolePick.value = role
        departmentId = null
        deptPick.value = null
        host.text = ""
        hostname = ""
        tried = false
        busy = false
        problem = ""
        done = null
    }
    onAboutToShow: reset()

    function submit() {
        tried = true
        if (!valid || busy) return
        busy = true
        problem = ""
        var payload = { role: role, hostname: hostname.trim() }
        if (needsDepartment) payload.department_id = departmentId
        falcon.call("hierarchy.account_create", payload, function (ok, r) {
            root.busy = false
            if (!ok) { root.problem = r && r.message ? r.message : "They were not added."; return }
            root.done = r
            Msg.ok("Added")
            root.made()
        })
    }
    function copyKey() {
        if (!done) return
        clip.text = String(done.client_key)
        clip.selectAll()
        clip.copy()
        Msg.ok("Key copied")
    }
    TextEdit { id: clip; visible: false }

    FormRow {
        width: parent.width
        visible: !root.done
        label: "Role"
        required: true
        Select {
            id: rolePick
            objectName: "personRole"
            width: parent.width
            options: root.roleOptions
            value: root.role
            onPicked: function (v) { root.role = v }
        }
    }
    FormRow {
        width: parent.width
        visible: !root.done && root.needsDepartment
        label: "Department"
        required: true
        problem: root.tried ? root.deptProblem : ""
        Select {
            id: deptPick
            objectName: "personDepartment"
            width: parent.width
            options: root.deptOptions
            placeholder: "Which department"
            invalid: root.tried && root.deptProblem !== ""
            onPicked: function (v) { root.departmentId = v }
        }
    }
    FormRow {
        width: parent.width
        visible: !root.done
        label: "Their machine"
        required: true
        hint: "The hostname it reports at connect. The account and the PC are made together."
        problem: root.tried ? root.hostProblem : ""
        Field {
            id: host
            objectName: "personHostname"
            width: parent.width
            placeholderText: "OPS-09"
            onTextChanged: root.hostname = text
            onAccepted: root.submit()
        }
    }
    Alert {
        width: parent.width
        visible: !root.done && root.problem !== ""
        kind: "danger"
        text: root.problem
    }

    // --- what came back ----------------------------------------------------------------------------
    Alert {
        width: parent.width
        visible: root.done !== null
        kind: "warn"
        text: "This key is shown once. Put it in their installer before you close this."
    }
    Descriptions {
        width: parent.width
        visible: root.done !== null
        items: root.done ? [
            { label: "Machine", value: root.hostname, mono: true },
            { label: "Role", value: root.done.role },
            { label: "Client id", value: String(root.done.client_id), mono: true }
        ] : []
    }
    FormRow {
        width: parent.width
        visible: root.done !== null
        label: "Key"
        hint: "Select it here if you would rather copy it by hand."
        Rectangle {
            width: parent.width
            height: Math.max(Theme.control, keyText.contentHeight + 2 * Theme.s2)
            radius: Theme.radius
            color: Theme.fill
            border.width: 1
            border.color: Theme.split
            TextEdit {
                id: keyText
                objectName: "personKey"
                anchors.fill: parent
                anchors.margins: Theme.s2
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.WrapAnywhere
                font.family: Theme.mono
                font.pixelSize: Theme.fSmall
                color: Theme.ink
                text: root.done ? String(root.done.client_key) : ""
            }
        }
    }

    footer: [
        Btn {
            text: root.done ? "Done" : "Cancel"
            visible: !root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: go.left
            anchors.rightMargin: Theme.s2
            onClicked: root.close()
        },
        Btn {
            id: go
            objectName: "personSubmit"
            kind: "primary"
            text: root.done ? "Copy key" : "Add"
            loading: root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: Theme.s5
            onClicked: root.done ? root.copyKey() : root.submit()
        }
    ]
}
