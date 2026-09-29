import QtQuick
import QtQuick.Controls.Basic
import "."

// ONE FORM, END TO END (docs/UI-COMPONENTS.md step 4): Modal + Form + Select + validation + message.
// Registering a machine hands back a key the Engine will never print again, so this form has a second
// half -- the key, and the one chance to take it.
Modal {
    id: root
    title: root.done ? "Registered" : "Register a machine"
    subtitle: root.done ? "" : "The Engine makes the key; the installer on the machine uses it."
    closePolicy: root.busy ? Popup.NoAutoClose : Popup.CloseOnEscape

    property var departments: []
    signal registered()

    // what has been entered
    property string hostname: ""
    property string kind: "client_pc"
    property var departmentId: null
    property bool tried: false
    property bool busy: false
    property string problem: ""              // what the Engine said, if it refused
    property var done: null                  // what it answered, if it did not

    readonly property bool needsDepartment: kind !== "super_user_workstation"
    readonly property string hostnameProblem:
        hostname.trim() === "" ? "A machine needs a hostname."
        : hostname.indexOf(" ") >= 0 ? "A hostname has no spaces in it."
        : hostname.length > 63 ? "A hostname stops at 63 characters." : ""
    readonly property string departmentProblem:
        needsDepartment && departmentId === null ? "Pick the department it answers to." : ""
    readonly property bool valid: hostnameProblem === "" && departmentProblem === ""

    readonly property var kinds: [
        { value: "client_pc", label: "Client PC" },
        { value: "admin_workstation", label: "Admin workstation" },
        { value: "super_user_workstation", label: "Super User workstation" }
    ]
    readonly property var deptOptions: departments.map(function (d) {
        return { value: d.department_id, label: d.name }
    })

    function reset() {
        host.text = ""
        hostname = ""
        kind = "client_pc"
        kindPick.value = "client_pc"
        departmentId = null
        deptPick.value = null
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
        var payload = { hostname: hostname.trim(), pc_type: kind }
        if (needsDepartment) payload.department_id = departmentId
        falcon.call("hierarchy.pc_register", payload, function (ok, r) {
            root.busy = false
            if (!ok) {
                root.problem = r && r.message ? r.message : "The Engine would not register it."
                Msg.failed("Not registered")
                return
            }
            root.done = r
            Msg.ok(payload.hostname + " registered")
            root.registered()
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

    // --- what is entered ---------------------------------------------------------------------------
    FormRow {
        width: parent.width
        visible: !root.done
        label: "Hostname"
        required: true
        hint: "The name the machine reports at connect. A different one is a deviation, not a refusal."
        problem: root.tried ? root.hostnameProblem : ""
        Field {
            id: host
            objectName: "hostnameField"
            width: parent.width
            placeholderText: "OPS-08"
            onTextChanged: root.hostname = text
            onAccepted: root.submit()
        }
    }
    FormRow {
        width: parent.width
        visible: !root.done
        label: "Kind"
        required: true
        Select {
            id: kindPick
            width: parent.width
            options: root.kinds
            value: "client_pc"
            onPicked: function (v) { root.kind = v }
        }
    }
    FormRow {
        width: parent.width
        visible: !root.done && root.needsDepartment
        label: "Department"
        required: true
        problem: root.tried ? root.departmentProblem : ""
        Select {
            id: deptPick
            objectName: "departmentSelect"
            width: parent.width
            options: root.deptOptions
            placeholder: "Which department"
            invalid: root.tried && root.departmentProblem !== ""
            onPicked: function (v) { root.departmentId = v }
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
        text: "This key is shown once. Put it in the machine's installer before you close this."
    }
    Descriptions {
        width: parent.width
        visible: root.done !== null
        items: root.done ? [
            { label: "Machine", value: root.hostname, mono: true },
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
                objectName: "clientKey"
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
            objectName: "registerCancel"
            text: root.done ? "Done" : "Cancel"
            visible: !root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: go.left
            anchors.rightMargin: Theme.s2
            onClicked: root.close()
        },
        Btn {
            id: go
            objectName: "registerSubmit"
            kind: "primary"
            text: root.done ? "Copy key" : "Register"
            loading: root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: Theme.s5
            onClicked: root.done ? root.copyKey() : root.submit()
        }
    ]
}
