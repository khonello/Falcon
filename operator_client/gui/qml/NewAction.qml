import QtQuick
import QtQuick.Controls.Basic
import "."

// WRITING ONE. A built-in takes its parameters from the Engine's own list, so this form cannot offer
// a field the Engine does not want or miss one it requires. A Custom Action is a script, Admins only,
// and it is checked here before it is sent -- the same check the Engine and the worker both run again.
Modal {
    id: root
    width: 560
    title: "New action"
    subtitle: "One thing a machine can be made to do."
    closePolicy: root.busy ? Popup.NoAutoClose : Popup.CloseOnEscape

    property var builtin: ({})               // the Engine's catalogue: type -> {category, params}
    signal made()

    property string kind: "control"
    property var builtinType: null
    property var params: ({})
    property string actionName: ""
    property string language: "python"
    property string script: ""
    property int timeout: 60
    property bool tried: false
    property bool busy: false
    property string problem: ""
    property var scriptProblems: []
    property bool reviewed: false

    readonly property bool custom: kind === "custom"
    readonly property var typeOptions: {
        var out = []
        for (var key in builtin)
            if (builtin[key].category === kind)
                out.push({ value: key, label: Doing.plain(key, Doing.actionNames) })
        out.sort(function (a, b) { return String(a.label).localeCompare(String(b.label)) })
        return out
    }
    readonly property var needed: builtinType && builtin[builtinType] ? builtin[builtinType].params : []
    readonly property string typeProblem: custom || builtinType !== null ? "" : "Pick what it does."
    readonly property string paramProblem: {
        for (var i = 0; i < needed.length; i++)
            if (!params[needed[i]] || String(params[needed[i]]).trim() === "")
                return "Fill in everything it needs to know."
        return ""
    }
    readonly property string nameProblem:
        custom && actionName.trim() === "" ? "A script needs a name people will recognise." : ""
    readonly property string scriptProblem:
        custom && script.trim() === "" ? "There is no script here."
        : scriptProblems.length > 0 ? scriptProblems.join("; ") : ""
    readonly property bool valid: typeProblem === "" && (custom ? nameProblem === "" && scriptProblem === ""
                                                                : paramProblem === "")

    function reset() {
        kind = "control"
        kindPick.value = "control"
        builtinType = null
        typePick.value = null
        params = ({})
        actionName = ""
        nameField.text = ""
        language = "python"
        langPick.value = "python"
        script = ""
        scriptArea.text = ""
        scriptProblems = []
        timeout = 60
        timeoutField.text = "60"
        tried = false
        busy = false
        problem = ""
    }
    onAboutToShow: reset()

    function setParam(key, value) {
        var copy = {}
        for (var k in params) copy[k] = params[k]
        copy[key] = value
        params = copy
    }

    // the same check the Engine runs, and then the worker runs again on arrival: stdlib and
    // Windows-native only. Doing it here means the refusal reads as a review, not a rejection.
    function check() {
        if (!custom || script.trim() === "") { scriptProblems = []; return }
        var r = falcon.validateScript(language, script)
        scriptProblems = r.ok ? [] : r.problems
        reviewed = true
    }

    function submit() {
        tried = true
        check()
        if (!valid || busy) return
        busy = true
        problem = ""
        var payload = { kind: kind, timeout_s: timeout }
        if (custom) {
            payload.name = actionName.trim()
            payload.language = language
            payload.script = script
        } else {
            payload.builtin_type = builtinType
            payload.params = params
            payload.name = Doing.plain(builtinType, Doing.actionNames)
        }
        falcon.call("control.action_create", payload, function (ok, r) {
            root.busy = false
            if (!ok) { root.problem = r && r.message ? r.message : "It was not saved."; return }
            Msg.ok("Action saved")
            root.made()
            root.close()
        })
    }

    FormRow {
        width: parent.width
        label: "Kind"
        required: true
        hint: root.custom && falcon.role !== "admin"
              ? "Only an Admin can author a script. Ask the department's Admin." : ""
        Select {
            id: kindPick
            objectName: "actionKind"
            width: parent.width
            value: "control"
            options: [{ value: "control", label: "Control · does something to the machine" },
                      { value: "monitoring", label: "Monitoring · reports something back" },
                      { value: "custom", label: "Custom · a script of your own" }]
            onPicked: function (v) { root.kind = v; root.builtinType = null; typePick.value = null }
        }
    }

    FormRow {
        width: parent.width
        visible: !root.custom
        label: "What it does"
        required: true
        problem: root.tried ? root.typeProblem : ""
        Select {
            id: typePick
            objectName: "actionType"
            width: parent.width
            options: root.typeOptions
            placeholder: "Pick one"
            invalid: root.tried && root.typeProblem !== ""
            onPicked: function (v) { root.builtinType = v; root.params = ({}) }
        }
    }

    // the Engine says which parameters this built-in needs; the form asks for exactly those
    FormRow {
        width: parent.width
        visible: !root.custom && root.needed.length > 0
        label: "What it needs to know"
        required: true
        problem: root.tried ? root.paramProblem : ""
        Column {
            width: parent.width
            spacing: Theme.s2
            Repeater {
                model: root.needed
                delegate: Field {
                    required property var modelData
                    width: parent.width
                    placeholderText: Doing.paramLabel(modelData)
                    onTextEdited: root.setParam(modelData, text)
                }
            }
        }
    }

    FormRow {
        width: parent.width
        visible: root.custom
        label: "Name"
        required: true
        problem: root.tried ? root.nameProblem : ""
        Field {
            id: nameField
            objectName: "actionName"
            width: parent.width
            placeholderText: "Clear the temp folder"
            onTextChanged: root.actionName = text
        }
    }
    FormRow {
        width: parent.width
        visible: root.custom
        label: "Language"
        required: true
        Select {
            id: langPick
            width: parent.width
            value: "python"
            options: [{ value: "python", label: "Python" }, { value: "powershell", label: "PowerShell" }]
            onPicked: function (v) { root.language = v; root.check() }
        }
    }
    FormRow {
        width: parent.width
        visible: root.custom
        label: "Script"
        required: true
        hint: "The standard library and what Windows already has. Nothing installed, nothing fetched."
        problem: root.tried ? root.scriptProblem : ""
        ScriptPanel {
            id: scriptArea
            objectName: "actionScriptEditor"
            width: parent.width
            language: root.language
            problems: root.scriptProblems
            checked: root.reviewed
            onTextChanged: { root.script = text; root.scriptProblems = []; root.reviewed = false }
            onCheck: root.check()
        }
    }

    FormRow {
        width: parent.width
        label: "Gives up after"
        required: true
        hint: "Every Action has a timeout, and a timeout is reported as its own outcome -- not an error."
        Field {
            id: timeoutField
            objectName: "actionTimeout"
            width: 160
            text: "60"
            onTextEdited: root.timeout = parseInt(text) || 0
        }
    }

    Alert {
        width: parent.width
        visible: root.custom
        kind: "warn"
        text: "It runs unsandboxed, as the machine's own user. Read it the way you would read a script "
              + "somebody emailed you."
    }
    Alert {
        width: parent.width
        visible: root.problem !== ""
        kind: "danger"
        text: root.problem
    }

    footer: [
        Btn {
            id: cancel
            text: "Cancel"
            visible: !root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: go.left
            anchors.rightMargin: Theme.s2
            onClicked: root.close()
        },
        Btn {
            id: go
            objectName: "actionSubmit"
            kind: "primary"
            text: "Save"
            loading: root.busy
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: Theme.s5
            onClicked: root.submit()
        }
    ]
}
