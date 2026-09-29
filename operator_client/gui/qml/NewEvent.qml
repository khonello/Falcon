import QtQuick
import QtQuick.Controls.Basic
import "."

// ONE SENTENCE. When something happens, on these machines, run these Actions in this order. The only
// extra the form asks for is what the Engine genuinely requires: a time event needs a time.
Modal {
    id: root
    width: 580
    title: "New rule"
    subtitle: "When something happens, run something."
    closePolicy: root.busy ? Popup.NoAutoClose : Popup.CloseOnEscape

    property var types: ({})                  // event type -> "native_pushed" | "polled"
    signal made()

    property var eventType: null
    property var targets: []                  // pc ids; empty means every machine in reach
    property var chain: []                    // action ids, in order
    property string timeMode: "at"            // at | every
    property string at: ""
    property int everyMinutes: 15
    property bool tried: false
    property bool busy: false
    property string problem: ""
    property var machines: []
    property var library: []

    readonly property bool timed: eventType === "time.scheduled" || eventType === "time.recurring"
    readonly property bool recurring: eventType === "time.recurring"
    readonly property var typeOptions: {
        var out = []
        for (var key in types) out.push({ value: key, label: Doing.eventName(key) })
        out.sort(function (a, b) { return String(a.label).localeCompare(String(b.label)) })
        return out
    }
    readonly property var machineOptions: machines.map(function (m) {
        return { value: m.pc_id, label: m.hostname + "  ·  " + m.department }
    })
    readonly property var actionOptions: library.map(function (a) {
        return { value: a.id, label: Doing.actionName(a) }
    })

    readonly property string typeProblem: eventType === null ? "Pick what sets it off." : ""
    readonly property string chainProblem: {
        if (chain.length === 0) return "Pick at least one Action, or there is nothing to run."
        for (var i = 0; i < chain.length; i++)
            if (chain[i] === null) return "One of these has no Action picked."
        return ""
    }
    readonly property string timeProblem:
        !timed ? ""
        : recurring && timeMode === "every" ? (everyMinutes > 0 ? "" : "How often, in minutes?")
        : at.trim() === "" ? (recurring ? "A time of day, as HH:MM." : "A date and time, as 2026-10-03T16:00.")
        : ""
    readonly property bool valid: typeProblem === "" && chainProblem === "" && timeProblem === ""

    function reset() {
        eventType = null
        typePick.value = null
        targets = []
        chain = [null]
        timeMode = "at"
        at = ""
        atField.text = ""
        everyMinutes = 15
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
            var pcs = []
            var list = r.departments || []
            for (var i = 0; i < list.length; i++) {
                var people = (list[i].admins || []).concat(list[i].workers || [])
                for (var j = 0; j < people.length; j++)
                    if (people[j].pc_id)
                        pcs.push({ pc_id: people[j].pc_id, hostname: people[j].hostname || "a machine",
                                   department: list[i].name })
            }
            root.machines = pcs
        })
        falcon.call("control.action_list", {}, function (ok, r) {
            if (!ok) return
            var groups = r.actions || {}
            root.library = (groups.control || []).concat(groups.monitoring || [], groups.custom || [])
        })
    }

    function setAt(list, index, value) {
        var copy = list.slice()
        copy[index] = value
        return copy
    }
    function addTarget() { targets = targets.concat([null]) }
    function dropTarget(i) { targets = targets.filter(function (_, n) { return n !== i }) }
    function addStep() { chain = chain.concat([null]) }
    function dropStep(i) {
        var left = chain.filter(function (_, n) { return n !== i })
        chain = left.length > 0 ? left : [null]
    }

    function submit() {
        tried = true
        if (!valid || busy) return
        busy = true
        problem = ""
        var picked = targets.filter(function (t) { return t !== null })
        var payload = { type: eventType, action_ids: chain.filter(function (c) { return c !== null }),
                        enabled: true }
        if (picked.length > 0) payload.pc_ids = picked
        if (timed)
            payload.match = (recurring && timeMode === "every") ? { interval_s: everyMinutes * 60 }
                                                                : { at: at.trim() }
        falcon.call("control.event_create", payload, function (ok, r) {
            root.busy = false
            if (!ok) { root.problem = r && r.message ? r.message : "It was not saved."; return }
            Msg.ok("Rule on")
            root.made()
            root.close()
        })
    }

    FormRow {
        width: parent.width
        label: "When"
        required: true
        problem: root.tried ? root.typeProblem : ""
        Select {
            id: typePick
            objectName: "eventType"
            width: parent.width
            options: root.typeOptions
            placeholder: "What sets it off"
            invalid: root.tried && root.typeProblem !== ""
            onPicked: function (v) { root.eventType = v }
        }
    }

    FormRow {
        width: parent.width
        visible: root.timed
        label: root.recurring ? "How often" : "At"
        required: true
        problem: root.tried ? root.timeProblem : ""
        Column {
            width: parent.width
            spacing: Theme.s2
            Select {
                width: parent.width
                visible: root.recurring
                value: "at"
                options: [{ value: "at", label: "At a time of day" },
                          { value: "every", label: "Every so many minutes" }]
                onPicked: function (v) { root.timeMode = v }
            }
            Field {
                id: atField
                objectName: "eventAt"
                width: parent.width
                visible: !(root.recurring && root.timeMode === "every")
                placeholderText: root.recurring ? "18:30" : "2026-10-03T16:00"
                onTextChanged: root.at = text
            }
            Field {
                width: 160
                visible: root.recurring && root.timeMode === "every"
                text: "15"
                onTextEdited: root.everyMinutes = parseInt(text) || 0
            }
        }
    }

    FormRow {
        width: parent.width
        label: "On"
        hint: "Leave it empty and it watches every machine you can see."
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
                        width: parent.width - 32 - Theme.s2
                        options: root.machineOptions
                        value: root.targets[parent.index]
                        placeholder: "Which machine"
                        onPicked: function (v) { root.targets = root.setAt(root.targets, parent.index, v) }
                    }
                    Btn {
                        kind: "text"
                        iconName: "close"
                        onClicked: root.dropTarget(parent.index)
                    }
                }
            }
            Btn {
                objectName: "addEventMachine"
                kind: "link"
                iconName: "plus"
                text: root.targets.length === 0 ? "One machine" : "Another"
                onClicked: root.addTarget()
            }
        }
    }

    FormRow {
        width: parent.width
        label: "Run"
        required: true
        hint: "In this order, each with its own timeout. Nothing is passed from one to the next."
        problem: root.tried ? root.chainProblem : ""
        Column {
            width: parent.width
            spacing: Theme.s2

            Repeater {
                model: root.chain.length
                delegate: Row {
                    required property int index
                    width: parent.width
                    spacing: Theme.s2
                    Txt {
                        width: 16
                        text: (parent.index + 1) + "."
                        tone: "quiet"
                        font.pixelSize: Theme.fSmall
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Select {
                        width: parent.width - 16 - 32 - 2 * Theme.s2
                        options: root.actionOptions
                        value: root.chain[parent.index]
                        placeholder: "Which Action"
                        invalid: root.tried && root.chain[parent.index] === null
                        onPicked: function (v) { root.chain = root.setAt(root.chain, parent.index, v) }
                    }
                    Btn {
                        kind: "text"
                        iconName: "close"
                        visible: root.chain.length > 1
                        onClicked: root.dropStep(parent.index)
                    }
                }
            }
            Btn {
                objectName: "addEventAction"
                kind: "link"
                iconName: "plus"
                text: "Another"
                onClicked: root.addStep()
            }
        }
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
            objectName: "eventSubmit"
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
