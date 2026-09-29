import QtQuick
import QtQuick.Controls.Basic
import "."

// ONE DIRECTION, SAID ONCE. A source folder, and the folders it lands in. The Engine runs the consent,
// collision and cycle checks before it stores anything -- this form does not second-guess them, it
// asks, and when the Engine says a destination already has content in it, it names that cost and asks
// again with the confirm.
Modal {
    id: root
    width: 580
    title: "New flow"
    subtitle: "What changes in the source folder lands in the others. It never goes back the other way."
    closePolicy: root.busy ? Popup.NoAutoClose : Popup.CloseOnEscape

    signal made()

    property var sourcePcId: null
    property string sourcePath: ""
    property var targets: [{ pc_id: null, path: "" }]
    property bool tried: false
    property bool busy: false
    property string problem: ""
    property var machines: []

    readonly property var machineOptions: machines.map(function (m) {
        return { value: m.pc_id, label: m.hostname + "  \u00b7  " + m.department }
    })
    readonly property string sourceProblem:
        sourcePcId === null ? "Pick the machine the files come from."
        : sourcePath.trim() === "" ? "Say which folder on it." : ""
    readonly property string targetProblem: {
        for (var i = 0; i < targets.length; i++)
            if (targets[i].pc_id === null || String(targets[i].path).trim() === "")
                return "Every destination needs a machine and a folder."
        return ""
    }
    readonly property bool valid: sourceProblem === "" && targetProblem === ""

    function reset() {
        sourcePcId = null
        srcPick.value = null
        srcPath.text = ""
        sourcePath = ""
        targets = [{ pc_id: null, path: "" }]
        tried = false
        busy = false
        problem = ""
        loadMachines()
    }
    onAboutToShow: reset()

    function loadMachines() {
        if (!falcon.isConnected) return
        falcon.call("hierarchy.tree", {}, function (ok, r) {
            if (!ok) return
            var out = []
            var depts = r.departments || []
            for (var i = 0; i < depts.length; i++) {
                var people = (depts[i].admins || []).concat(depts[i].workers || [])
                for (var j = 0; j < people.length; j++)
                    if (people[j].pc_id)
                        out.push({ pc_id: people[j].pc_id, hostname: people[j].hostname || "a machine",
                                   department: depts[i].name })
            }
            root.machines = out
        })
    }

    function setTarget(index, key, value) {
        var copy = []
        for (var i = 0; i < targets.length; i++)
            copy.push({ pc_id: targets[i].pc_id, path: targets[i].path })
        copy[index][key] = value
        targets = copy
    }
    function addTarget() {
        var copy = []
        for (var i = 0; i < targets.length; i++)
            copy.push({ pc_id: targets[i].pc_id, path: targets[i].path })
        copy.push({ pc_id: null, path: "" })
        targets = copy
    }
    function dropTarget(index) {
        var copy = []
        for (var i = 0; i < targets.length; i++)
            if (i !== index) copy.push({ pc_id: targets[i].pc_id, path: targets[i].path })
        targets = copy.length > 0 ? copy : [{ pc_id: null, path: "" }]
    }

    // two names, no arguments: the button asks, the confirm answers
    function create() { send(false) }
    function createAnyway() { send(true) }

    function send(confirmCollisions) {
        tried = true
        if (!valid || busy) return
        busy = true
        problem = ""
        var dests = targets.map(function (t) {
            return { destination_pc_id: t.pc_id, destination_path: String(t.path).trim() }
        })
        var payload = { source_pc_id: sourcePcId, source_path: sourcePath.trim(), destinations: dests }
        if (confirmCollisions) payload.confirm_collisions = true
        falcon.call("flow.create", payload, function (ok, r) {
            root.busy = false
            if (!ok) {
                // the one refusal a person can answer: content already sitting in a destination
                if (r && r.code === "conflict" && String(r.message).indexOf("collides") >= 0) {
                    overwrite.cost = "There are already files in that folder. The flow will copy over "
                                   + "them as the source changes, and what is there now is not backed up "
                                   + "anywhere by this.\n\n" + r.message.split(" -- ")[0]
                    overwrite.open()
                    return
                }
                root.problem = r && r.message ? r.message : "It was not created."
                return
            }
            Msg.ok(r.consent_pending ? "Waiting on consent" : "Flow running")
            root.made()
            root.close()
        })
    }

    Confirm {
        id: overwrite
        objectName: "collisionConfirm"
        title: "That folder is not empty"
        verb: "Use it"
        destructive: true
        onAccepted: root.createAnyway()
    }

    FormRow {
        width: parent.width
        label: "From"
        required: true
        problem: root.tried ? root.sourceProblem : ""
        Column {
            width: parent.width
            spacing: Theme.s2
            Select {
                id: srcPick
                objectName: "sourceSelect"
                width: parent.width
                options: root.machineOptions
                placeholder: "Which machine"
                invalid: root.tried && root.sourcePcId === null
                onPicked: function (v) { root.sourcePcId = v }
            }
            Field {
                id: srcPath
                objectName: "sourcePathField"
                width: parent.width
                placeholderText: "C:\\work\\payroll"
                onTextChanged: root.sourcePath = text
            }
        }
    }

    FormRow {
        width: parent.width
        label: "To"
        required: true
        hint: "One way only. A destination inside its own source is a cycle and the Engine refuses it."
        problem: root.tried ? root.targetProblem : ""
        Column {
            width: parent.width
            spacing: Theme.s2

            Repeater {
                model: root.targets.length
                delegate: Row {
                    required property int index
                    width: parent.width
                    spacing: Theme.s2

                    Select {
                        width: 200
                        options: root.machineOptions
                        value: root.targets[parent.index].pc_id
                        placeholder: "Which machine"
                        invalid: root.tried && root.targets[parent.index].pc_id === null
                        onPicked: function (v) { root.setTarget(parent.index, "pc_id", v) }
                    }
                    Field {
                        width: parent.width - 200 - 32 - 2 * Theme.s2
                        text: root.targets[parent.index].path
                        placeholderText: "C:\\shared\\payroll"
                        onTextEdited: root.setTarget(parent.index, "path", text)
                    }
                    Btn {
                        kind: "text"
                        iconName: "close"
                        visible: root.targets.length > 1
                        onClicked: root.dropTarget(parent.index)
                    }
                }
            }
            Btn {
                objectName: "addDestination"
                kind: "link"
                iconName: "plus"
                text: "Another"
                onClicked: root.addTarget()
            }
        }
    }

    Alert {
        width: parent.width
        kind: "note"
        text: "Nothing is transformed on the way. Branch, transform and categorize come later."
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
            objectName: "flowSubmit"
            kind: "primary"
            text: "Create"
            loading: root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: Theme.s5
            onClicked: root.create()
        }
    ]
}
